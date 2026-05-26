import torch
import torch.nn as nn
import numpy as np
import pickle
from typing import List, Tuple, Optional
from pathlib import Path
from sklearn.preprocessing import MultiLabelBinarizer, StandardScaler


class ContentProcessor:
    def __init__(self):
        self.mlb_genres = MultiLabelBinarizer()
        self.mlb_categories = MultiLabelBinarizer()
        self.mlb_tags = MultiLabelBinarizer()
        self.scaler = StandardScaler()
        self.feature_names = []

    def fit_transform(self, game_features_df):
        pass 


class HybridNeuMF(nn.Module):
    def __init__(self, num_users, num_items, content_dim, mf_dim=8, 
                 mlp_dims=[64, 32, 16, 8], content_hidden_dims=[128, 64], 
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
                nn.Dropout(0.2)
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

    def _build_cold_user_embedding(self, owned_game_indices):
        item_indices = torch.LongTensor(owned_game_indices)
        gmf_user_emb = self.gmf_item_embedding(item_indices).mean(dim=0, keepdim=True)
        mlp_user_emb = self.mlp_item_embedding(item_indices).mean(dim=0, keepdim=True)
        return gmf_user_emb, mlp_user_emb

    def forward_cold_start(self, gmf_user_emb, mlp_user_emb, item_ids, item_content):
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

    def forward_collaborative_only(self, gmf_user_emb, mlp_user_emb, item_ids):
        batch_size = item_ids.size(0)

        gmf_user_emb = gmf_user_emb.expand(batch_size, -1)

        gmf_item_emb = self.gmf_item_embedding(item_ids)
        
        user_norm = gmf_user_emb / (gmf_user_emb.norm(dim=1, keepdim=True) + 1e-8)
        item_norm = gmf_item_emb / (gmf_item_emb.norm(dim=1, keepdim=True) + 1e-8)
        
        cosine_sim = (user_norm * item_norm).sum(dim=1)
        
        score = (cosine_sim + 1) / 2
        
        return score

    def predict_single_game_collaborative(self, owned_game_ids, target_game_id, item_to_idx):
        self.eval()

        if target_game_id not in item_to_idx:
            return None

        known_owned_indices = [item_to_idx[gid] for gid in owned_game_ids
                               if gid in item_to_idx]

        if len(known_owned_indices) == 0:
            return None

        gmf_user_emb, mlp_user_emb = self._build_cold_user_embedding(known_owned_indices)

        item_idx = torch.LongTensor([item_to_idx[target_game_id]])

        with torch.no_grad():
            score = self.forward_collaborative_only(gmf_user_emb, mlp_user_emb, item_idx)

        return score.item()

    def get_recommendations_for_games(self, owned_game_ids, item_to_idx, game_to_features,
                                      top_k=10, exclude_owned=True):
        self.eval()

        known_owned_indices = [item_to_idx[gid] for gid in owned_game_ids
                               if gid in item_to_idx and gid in game_to_features]

        if len(known_owned_indices) == 0:
            return []

        gmf_user_emb, mlp_user_emb = self._build_cold_user_embedding(known_owned_indices)

        candidate_games = list(game_to_features.keys())
        if exclude_owned:
            owned_set = set(owned_game_ids)
            candidate_games = [gid for gid in candidate_games if gid not in owned_set]
        candidate_games = [gid for gid in candidate_games if gid in item_to_idx]

        if len(candidate_games) == 0:
            return []

        item_indices = torch.LongTensor([item_to_idx[gid] for gid in candidate_games])
        item_features = torch.FloatTensor(np.array([game_to_features[gid] for gid in candidate_games]))

        with torch.no_grad():
            scores = self.forward_cold_start(gmf_user_emb, mlp_user_emb, item_indices, item_features)

        k = min(top_k, len(scores))
        top_scores, top_indices = torch.topk(scores, k)

        recommendations = []
        for score, idx in zip(top_scores, top_indices):
            recommendations.append((candidate_games[idx], score.item()))

        return recommendations

    def predict_single_game(self, owned_game_ids, target_game_id, item_to_idx, game_to_features):
        self.eval()

        if target_game_id not in item_to_idx or target_game_id not in game_to_features:
            return None

        known_owned_indices = [item_to_idx[gid] for gid in owned_game_ids
                               if gid in item_to_idx and gid in game_to_features]

        if len(known_owned_indices) == 0:
            return None

        gmf_user_emb, mlp_user_emb = self._build_cold_user_embedding(known_owned_indices)

        item_idx = torch.LongTensor([item_to_idx[target_game_id]])
        item_features = torch.FloatTensor([game_to_features[target_game_id]])

        with torch.no_grad():
            score = self.forward_cold_start(gmf_user_emb, mlp_user_emb, item_idx, item_features)

        return score.item()


class RecommendationService:

    def __init__(self, model_path: str = "hybrid_neumf_improved.pkl"):
        self.model = None
        self.item_to_idx = None
        self.game_to_features = None
        self.model_path = model_path
        self._load_model()

    def _load_model(self):
        path = Path(self.model_path)
        if not path.exists():
            raise FileNotFoundError(f"Model file not found: {self.model_path}")

        class CustomUnpickler(pickle.Unpickler):
            def find_class(self, module, name):
                if name == 'ContentProcessor':
                    return ContentProcessor
                if name == 'HybridNeuMF':
                    return HybridNeuMF
                return super().find_class(module, name)

        with open(path, 'rb') as f:
            checkpoint = CustomUnpickler(f).load()

        config = checkpoint['model_config']
        self.model = HybridNeuMF(
            num_users=config['num_users'],
            num_items=config['num_items'],
            content_dim=config['content_dim'],
            mf_dim=config['mf_dim'],
            mlp_dims=config['mlp_dims'],
            content_hidden_dims=config['content_hidden_dims'],
            use_logits=config['use_logits']
        )
        self.model.load_state_dict(checkpoint['model_state_dict'])
        self.model.eval()

        self.item_to_idx = checkpoint['item_to_idx']
        self.game_to_features = checkpoint['game_to_features']

    def get_recommendations(self, owned_game_ids: List[int], top_k: int = 20) -> List[Tuple[int, float]]:
        if self.model is None:
            return []

        return self.model.get_recommendations_for_games(
            owned_game_ids=owned_game_ids,
            item_to_idx=self.item_to_idx,
            game_to_features=self.game_to_features,
            top_k=top_k,
            exclude_owned=True
        )

    def predict_game(self, owned_game_ids: List[int], target_game_id: int) -> Optional[float]:
        if self.model is None:
            return None

        if target_game_id in self.game_to_features:
            return self.model.predict_single_game(
                owned_game_ids=owned_game_ids,
                target_game_id=target_game_id,
                item_to_idx=self.item_to_idx,
                game_to_features=self.game_to_features
            )
        
        if target_game_id in self.item_to_idx:
            return self.model.predict_single_game_collaborative(
                owned_game_ids=owned_game_ids,
                target_game_id=target_game_id,
                item_to_idx=self.item_to_idx
            )
        
        return None

    def is_game_known(self, game_id: int) -> bool:
        return game_id in self.item_to_idx


_recommendation_service: Optional[RecommendationService] = None


def get_recommendation_service() -> RecommendationService:
    global _recommendation_service
    if _recommendation_service is None:
        _recommendation_service = RecommendationService()
    return _recommendation_service