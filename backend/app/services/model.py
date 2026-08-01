import numpy as np
import torch
import torch.nn as nn
from sklearn.preprocessing import MultiLabelBinarizer, StandardScaler
import ast

TAIL_IDX = 0

class ContentProcessor:
    def __init__(self):
        self.mlb_genres = MultiLabelBinarizer()
        self.mlb_categories = MultiLabelBinarizer()
        self.mlb_tags = MultiLabelBinarizer()
        self.scaler = StandardScaler()
        self.feature_names = []

    def fit_transform(self, game_features_df):

        def safe_parse_list(x):
            try:
                return ast.literal_eval(x) if isinstance(x, str) else []
            except Exception:
                return []

        def safe_parse_tags(x):
            try:
                if isinstance(x, str):
                    tags_dict = ast.literal_eval(x)
                    sorted_tags = sorted(tags_dict.items(),
                                         key=lambda kv: kv[1], reverse=True)
                    return [tag for tag, _ in sorted_tags[:20]]
                return []
            except Exception:
                return []

        game_features_df['genres_list'] = game_features_df['genres'].apply(safe_parse_list)
        genres_encoded = self.mlb_genres.fit_transform(game_features_df['genres_list'])
        self.feature_names.extend([f'genre_{g}' for g in self.mlb_genres.classes_])

        game_features_df['categories_list'] = game_features_df['categories'].apply(safe_parse_list)
        categories_encoded = self.mlb_categories.fit_transform(game_features_df['categories_list'])
        self.feature_names.extend([f'category_{c}' for c in self.mlb_categories.classes_])

        game_features_df['tags_list'] = game_features_df['tags'].apply(safe_parse_tags)
        tags_encoded = self.mlb_tags.fit_transform(game_features_df['tags_list'])
        self.feature_names.extend([f'tag_{t}' for t in self.mlb_tags.classes_])

        numerical_features = ['positive', 'negative', 'price', 'required_age']
        numerical_data = game_features_df[numerical_features].fillna(0)
        numerical_data['total_reviews'] = numerical_data['positive'] + numerical_data['negative']
        numerical_data['positive_ratio'] = (numerical_data['positive'] /
                                            (numerical_data['total_reviews'] + 1))
        numerical_scaled = self.scaler.fit_transform(numerical_data)
        self.feature_names.extend(numerical_data.columns.tolist())

        all_features = np.hstack([genres_encoded, categories_encoded,
                                  tags_encoded, numerical_scaled])

        game_to_features = {}
        for idx, game_id in enumerate(game_features_df['appid']):
            game_to_features[game_id] = all_features[idx]

        return game_to_features, all_features.shape[1]

class HybridNeuMF(nn.Module):
    def __init__(self, num_users, num_items, content_dim,
                 mf_dim=8, mlp_dims=[64, 32, 16, 8],
                 content_hidden_dims=[128, 64],
                 use_logits=True):
        super(HybridNeuMF, self).__init__()

        self.config = {
            'num_users': num_users,
            'num_items': num_items,
            'content_dim': content_dim,
            'mf_dim': mf_dim,
            'mlp_dims': mlp_dims,
            'content_hidden_dims': content_hidden_dims,
            'use_logits': use_logits
        }
        self.use_logits = use_logits

        self.gmf_user_embedding = nn.Embedding(num_users, mf_dim)
        self.gmf_item_embedding = nn.Embedding(num_items, mf_dim)

        self.mlp_user_embedding = nn.Embedding(num_users, mlp_dims[0] // 2)
        self.mlp_item_embedding = nn.Embedding(num_items, mlp_dims[0] // 2)

        content_layers = []
        input_dim = content_dim
        for hidden_dim in content_hidden_dims:
            content_layers.extend([
                nn.Linear(input_dim, hidden_dim),
                nn.ReLU(),
                nn.BatchNorm1d(hidden_dim),
                nn.Dropout(0.2),
            ])
            input_dim = hidden_dim
        content_layers.append(nn.Linear(input_dim, mf_dim))
        self.content_mlp = nn.Sequential(*content_layers)

        mlp_input_dim = mlp_dims[0] + mf_dim
        mlp_layer_list = []
        for i in range(len(mlp_dims) - 1):
            if i == 0:
                mlp_layer_list.append(nn.Linear(mlp_input_dim, mlp_dims[i + 1]))
            else:
                mlp_layer_list.append(nn.Linear(mlp_dims[i], mlp_dims[i + 1]))
            mlp_layer_list.append(nn.ReLU())
            mlp_layer_list.append(nn.Dropout(0.2))
        self.mlp_layers = nn.Sequential(*mlp_layer_list)

        self.prediction_layer = nn.Linear(mf_dim * 2 + mlp_dims[-1], 1)

        self._init_weights()

    def _init_weights(self):
        nn.init.normal_(self.gmf_user_embedding.weight, std=0.01)
        nn.init.normal_(self.gmf_item_embedding.weight, std=0.01)
        nn.init.normal_(self.mlp_user_embedding.weight, std=0.01)
        nn.init.normal_(self.mlp_item_embedding.weight, std=0.01)
        for module in self.mlp_layers:
            if isinstance(module, nn.Linear):
                nn.init.xavier_uniform_(module.weight)
                nn.init.zeros_(module.bias)
        nn.init.xavier_uniform_(self.prediction_layer.weight)
        nn.init.zeros_(self.prediction_layer.bias)

    def forward(self, user_ids, item_ids, item_content):
        gmf_user_emb = self.gmf_user_embedding(user_ids)
        gmf_item_emb = self.gmf_item_embedding(item_ids)
        gmf_output = gmf_user_emb * gmf_item_emb

        content_emb = self.content_mlp(item_content)
        content_gmf_output = gmf_user_emb * content_emb

        mlp_user_emb = self.mlp_user_embedding(user_ids)
        mlp_item_emb = self.mlp_item_embedding(item_ids)
        mlp_input = torch.cat([mlp_user_emb, mlp_item_emb, content_emb], dim=1)
        mlp_output = self.mlp_layers(mlp_input)

        final_features = torch.cat([gmf_output, content_gmf_output, mlp_output], dim=1)
        logits = self.prediction_layer(final_features).squeeze()

        if self.use_logits:
            return logits
        return torch.sigmoid(logits)

    def _build_cold_user_embedding(self, owned_games, item_to_idx,
                                   owner_counts=None):
        import math

        core = [(g, item_to_idx[g]) for g in owned_games
                if g in item_to_idx and item_to_idx[g] != TAIL_IDX]
        if len(core) == 0:
            return None, None

        indices = torch.LongTensor([idx for _, idx in core])

        weights = []
        for g, _ in core:
            minutes = owned_games.get(g, 0)
            w = math.log1p(minutes) + 0.1
            if owner_counts is not None:
                owners = owner_counts.get(g, 1)
                w *= 1.0 / (math.log1p(owners) + 1e-6)
            weights.append(w)

        w = torch.tensor(weights, dtype=torch.float32).unsqueeze(1) 
        w = w / (w.sum() + 1e-8) 
 
        gmf_embs = self.gmf_item_embedding(indices) 
        mlp_embs = self.mlp_item_embedding(indices)
 
        gmf_user_emb = (gmf_embs * w).sum(dim=0, keepdim=True)
        mlp_user_emb = (mlp_embs * w).sum(dim=0, keepdim=True)
        return gmf_user_emb, mlp_user_emb


    def _content_only_score(self, item_ids, item_content):
        batch_size = item_ids.size(0)
        content_emb = self.content_mlp(item_content)

        gmf_output = torch.zeros(batch_size, content_emb.size(1),
                                 device=content_emb.device)
        content_gmf_output = content_emb
        mlp_user_emb = torch.zeros(batch_size, self.mlp_item_embedding.embedding_dim,
                                   device=content_emb.device)
        mlp_item_emb = self.mlp_item_embedding(item_ids)
        mlp_input = torch.cat([mlp_user_emb, mlp_item_emb, content_emb], dim=1)
        mlp_output = self.mlp_layers(mlp_input)

        final_features = torch.cat([gmf_output, content_gmf_output, mlp_output], dim=1)
        logits = self.prediction_layer(final_features).squeeze()
        return torch.sigmoid(logits)

    def forward_cold_start(self, gmf_user_emb, mlp_user_emb, item_ids, item_content):
        if gmf_user_emb is None:
            return self._content_only_score(item_ids, item_content)

        batch_size = item_ids.size(0)
        gmf_user_emb = gmf_user_emb.expand(batch_size, -1)
        mlp_user_emb = mlp_user_emb.expand(batch_size, -1)

        gmf_item_emb = self.gmf_item_embedding(item_ids)
        gmf_output = gmf_user_emb * gmf_item_emb

        content_emb = self.content_mlp(item_content)
        content_gmf_output = gmf_user_emb * content_emb

        mlp_item_emb = self.mlp_item_embedding(item_ids)
        mlp_input = torch.cat([mlp_user_emb, mlp_item_emb, content_emb], dim=1)
        mlp_output = self.mlp_layers(mlp_input)

        final_features = torch.cat([gmf_output, content_gmf_output, mlp_output], dim=1)
        logits = self.prediction_layer(final_features).squeeze()
        return torch.sigmoid(logits)

    def forward_collaborative_only(self, gmf_user_emb, item_ids):
        batch_size = item_ids.size(0)
        gmf_user_emb = gmf_user_emb.expand(batch_size, -1)
        gmf_item_emb = self.gmf_item_embedding(item_ids)

        user_norm = gmf_user_emb / (gmf_user_emb.norm(dim=1, keepdim=True) + 1e-8)
        item_norm = gmf_item_emb / (gmf_item_emb.norm(dim=1, keepdim=True) + 1e-8)
        cosine_sim = (user_norm * item_norm).sum(dim=1)
        return (cosine_sim + 1) / 2

    def predict_single_game_collaborative(self, owned_game_ids, target_game_id,
                                          item_to_idx):
        self.eval()
        target_idx = item_to_idx.get(target_game_id)
        if target_idx is None or target_idx == TAIL_IDX:
            return None

        gmf_user_emb, mlp_user_emb = self._build_cold_user_embedding(
            {g: 0 for g in owned_game_ids}, item_to_idx)
        if gmf_user_emb is None:
            return None

        item_idx = torch.LongTensor([target_idx])
        with torch.no_grad():
            score = self.forward_collaborative_only(gmf_user_emb, item_idx)
            if score.dim() == 0:
                score = score.unsqueeze(0)
        return score.item()

    def get_recommendations_for_games(self, owned_games, item_to_idx, game_to_features,
                                      top_k=10, exclude_owned=True,
                                      owner_counts=None):
        self.eval()
        gmf_user_emb, mlp_user_emb = self._build_cold_user_embedding(
            owned_games, item_to_idx, owner_counts=owner_counts)
 
        candidate_games = list(game_to_features.keys())
        if exclude_owned:
            owned_set = set(owned_games)
            candidate_games = [g for g in candidate_games if g not in owned_set]
        if len(candidate_games) == 0:
            return []
 
        item_indices = torch.LongTensor([item_to_idx.get(g, TAIL_IDX)
                                         for g in candidate_games])
        item_features = torch.FloatTensor(
            np.array([game_to_features[g] for g in candidate_games], dtype=np.float32))
 
        with torch.no_grad():
            scores = self.forward_cold_start(gmf_user_emb, mlp_user_emb,
                                             item_indices, item_features)
            if scores.dim() == 0:
                scores = scores.unsqueeze(0)
 
        k = min(top_k, len(scores))
        top_scores, top_indices = torch.topk(scores, k)
        return [(candidate_games[i], s.item())
                for s, i in zip(top_scores, top_indices)]


    def predict_single_game(self, owned_game_ids, target_game_id,
                            item_to_idx, game_to_features):
        self.eval()
        if target_game_id not in game_to_features:
            return None

        gmf_user_emb, mlp_user_emb = self._build_cold_user_embedding(
            {g: 0 for g in owned_game_ids}, item_to_idx)

        item_idx = torch.LongTensor([item_to_idx.get(target_game_id, TAIL_IDX)])
        item_features = torch.FloatTensor(
            np.array([game_to_features[target_game_id]], dtype=np.float32))

        with torch.no_grad():
            score = self.forward_cold_start(gmf_user_emb, mlp_user_emb,
                                            item_idx, item_features)
        return score.item()