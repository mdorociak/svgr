
import ast

import numpy as np
import torch
import torch.nn as nn
from sklearn.preprocessing import MultiLabelBinarizer, StandardScaler


TAIL_IDX = 0


class ContentProcessor:
    LOG_COLUMNS = ['positive', 'negative', 'total_reviews', 'price']

    def __init__(self):
        self.mlb_genres = MultiLabelBinarizer()
        self.mlb_categories = MultiLabelBinarizer()
        self.mlb_tags = MultiLabelBinarizer()
        self.scaler = StandardScaler()
        self.feature_names = []

    def fit_transform(self, game_features_df):
        df = game_features_df.copy()         
        if 'has_features' in df.columns:
            df = df[df['has_features'].fillna(0).astype(int) == 1]
        df = df.reset_index(drop=True)
        self.feature_names = []        

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

        genres = self.mlb_genres.fit_transform(df['genres'].apply(safe_parse_list))
        self.feature_names.extend(f'genre_{g}' for g in self.mlb_genres.classes_)

        categories = self.mlb_categories.fit_transform(df['categories'].apply(safe_parse_list))
        self.feature_names.extend(f'category_{c}' for c in self.mlb_categories.classes_)

        tags = self.mlb_tags.fit_transform(df['tags'].apply(safe_parse_tags))
        self.feature_names.extend(f'tag_{t}' for t in self.mlb_tags.classes_)

        num = df[['positive', 'negative', 'price', 'required_age']].fillna(0).astype(float)
        num['total_reviews'] = num['positive'] + num['negative']
        num['positive_ratio'] = num['positive'] / (num['total_reviews'] + 1)
        for col in self.LOG_COLUMNS:
            num[col] = np.log1p(num[col].clip(lower=0))
        num_scaled = self.scaler.fit_transform(num)
        self.feature_names.extend(num.columns.tolist())

        has_features = np.ones((len(df), 1))
        self.feature_names.append('has_features')

        all_features = np.hstack([genres, categories, tags,
                                  num_scaled, has_features]).astype(np.float32)

        game_to_features = {game_id: all_features[i]
                            for i, game_id in enumerate(df['appid'])}
        return game_to_features, all_features.shape[1]

class _NeuMFCore(nn.Module):

    def __init__(self, num_items, content_dim, mf_dim, mlp_dims,
                 content_hidden_dims, use_logits):
        super().__init__()
        mlp_dims = list(mlp_dims)
        content_hidden_dims = list(content_hidden_dims)
        if mlp_dims[0] % 2:
            raise ValueError("mlp_dims[0] must be even (split between user and item)")

        self.use_logits = use_logits
        self.mf_dim = mf_dim
        self.user_dim = mlp_dims[0] // 2

        self.gmf_item_embedding = nn.Embedding(num_items, mf_dim)
        self.mlp_item_embedding = nn.Embedding(num_items, self.user_dim)

        content_layers = []
        in_dim = content_dim
        for hidden in content_hidden_dims:
            content_layers += [nn.Linear(in_dim, hidden), nn.ReLU(),
                               nn.BatchNorm1d(hidden), nn.Dropout(0.2)]
            in_dim = hidden
        content_layers.append(nn.Linear(in_dim, mf_dim))
        self.content_mlp = nn.Sequential(*content_layers)

        mlp_layer_list = []
        in_dim = mlp_dims[0] + mf_dim
        for out_dim in mlp_dims[1:]:
            mlp_layer_list += [nn.Linear(in_dim, out_dim), nn.ReLU(), nn.Dropout(0.2)]
            in_dim = out_dim
        self.mlp_layers = nn.Sequential(*mlp_layer_list)

        self.prediction_layer = nn.Linear(mf_dim * 2 + mlp_dims[-1], 1)

    def _init_core(self):
        nn.init.normal_(self.gmf_item_embedding.weight, std=0.01)
        nn.init.normal_(self.mlp_item_embedding.weight, std=0.01)
        for module in list(self.content_mlp) + list(self.mlp_layers):
            if isinstance(module, nn.Linear):
                nn.init.xavier_uniform_(module.weight)
                nn.init.zeros_(module.bias)
        nn.init.xavier_uniform_(self.prediction_layer.weight)
        nn.init.zeros_(self.prediction_layer.bias)

    def _device(self):
        return next(self.parameters()).device

    def _item_side(self, item_ids, item_content):
        return (self.gmf_item_embedding(item_ids),
                self.mlp_item_embedding(item_ids),
                self.content_mlp(item_content))

    def _combine(self, gmf_user, mlp_user, gmf_item, mlp_item, content):
        n = gmf_item.size(0)
        gmf_user = gmf_user.expand(n, -1)
        mlp_user = mlp_user.expand(n, -1)
        mlp_out = self.mlp_layers(torch.cat([mlp_user, mlp_item, content], dim=1))
        final = torch.cat([gmf_user * gmf_item, gmf_user * content, mlp_out], dim=1)
        return self.prediction_layer(final).squeeze(-1)

    @torch.no_grad()
    def item_cache(self, item_ids, item_content, batch_size=16384):
        parts = [self._item_side(item_ids[s:s + batch_size],
                                 item_content[s:s + batch_size])
                 for s in range(0, len(item_ids), batch_size)]
        return tuple(torch.cat(p, dim=0) for p in zip(*parts))

    def score_cached(self, gmf_user, mlp_user, cache, idx=None):
        if idx is not None:
            idx = torch.as_tensor(idx, dtype=torch.long, device=cache[0].device)
            cache = tuple(t[idx] for t in cache)
        return torch.sigmoid(self._combine(gmf_user, mlp_user, *cache))

    def forward_cold_start(self, gmf_user_emb, mlp_user_emb, item_ids, item_content):
        return torch.sigmoid(self._combine(gmf_user_emb, mlp_user_emb,
                                           *self._item_side(item_ids, item_content)))

    def forward_collaborative_only(self, gmf_user_emb, item_ids):
        gmf_item_emb = self.gmf_item_embedding(item_ids)
        gmf_user_emb = gmf_user_emb.expand(gmf_item_emb.size(0), -1)
        user_norm = gmf_user_emb / (gmf_user_emb.norm(dim=1, keepdim=True) + 1e-8)
        item_norm = gmf_item_emb / (gmf_item_emb.norm(dim=1, keepdim=True) + 1e-8)
        return ((user_norm * item_norm).sum(dim=1) + 1) / 2

    @torch.no_grad()
    def predict_single_game_collaborative(self, owned_game_ids, target_game_id, item_to_idx):
        self.eval()
        target_idx = item_to_idx.get(target_game_id)
        if target_idx is None or target_idx == TAIL_IDX:
            return None
        gmf_user, _, fallback = self.cold_user(owned_game_ids, item_to_idx)
        if fallback:
            return None
        item_idx = torch.tensor([target_idx], dtype=torch.long, device=self._device())
        return self.forward_collaborative_only(gmf_user, item_idx).item()

    @torch.no_grad()
    def get_recommendations_for_games(self, owned_game_ids, item_to_idx, game_to_features,
                                      top_k=10, exclude_owned=True):
        self.eval()
        candidates = list(game_to_features.keys())
        if exclude_owned:
            owned = set(owned_game_ids)
            candidates = [g for g in candidates if g not in owned]
        if not candidates:
            return []

        dev = self._device()
        item_ids = torch.tensor([item_to_idx.get(g, TAIL_IDX) for g in candidates],
                                dtype=torch.long, device=dev)
        feats = torch.from_numpy(np.asarray([game_to_features[g] for g in candidates],
                                            dtype=np.float32)).to(dev)

        gmf, mlp, _ = self.cold_user(owned_game_ids, item_to_idx)
        scores = self.score_cached(gmf, mlp, self.item_cache(item_ids, feats))

        top = torch.topk(scores, min(top_k, scores.numel()))
        return [(candidates[i], s) for s, i in zip(top.values.tolist(), top.indices.tolist())]

    @torch.no_grad()
    def predict_single_game(self, owned_game_ids, target_game_id,
                            item_to_idx, game_to_features):
        self.eval()
        if target_game_id not in game_to_features:
            return None
        dev = self._device()
        item = torch.tensor([item_to_idx.get(target_game_id, TAIL_IDX)],
                            dtype=torch.long, device=dev)
        feat = torch.from_numpy(np.asarray([game_to_features[target_game_id]],
                                           dtype=np.float32)).to(dev)
        gmf, mlp, _ = self.cold_user(owned_game_ids, item_to_idx)
        return self.forward_cold_start(gmf, mlp, item, feat).item()


class ProfileNeuMF(_NeuMFCore):

    def __init__(self, num_items, content_dim, mf_dim=16, mlp_dims=(64, 32, 16),
                 content_hidden_dims=(128, 64), use_logits=True):
        super().__init__(num_items, content_dim, mf_dim, mlp_dims,
                         content_hidden_dims, use_logits)
        self.config = {
            'num_items': num_items,
            'content_dim': content_dim,
            'mf_dim': mf_dim,
            'mlp_dims': list(mlp_dims),
            'content_hidden_dims': list(content_hidden_dims),
            'use_logits': use_logits,
        }
        self.gmf_ctx = nn.Embedding(num_items, mf_dim)
        self.mlp_ctx = nn.Embedding(num_items, self.user_dim)

        self._init_core()
        nn.init.normal_(self.gmf_ctx.weight, std=0.01)
        nn.init.normal_(self.mlp_ctx.weight, std=0.01)

        self.register_buffer('_pf_flat', torch.zeros(0, dtype=torch.long), persistent=False)
        self.register_buffer('_pf_offs', torch.zeros(0, dtype=torch.long), persistent=False)
        self.register_buffer('_pf_len', torch.zeros(0, dtype=torch.long), persistent=False)

    def set_profile_index(self, flat, offsets, lengths):
        dev = self._device()
        self._pf_flat = torch.as_tensor(flat, dtype=torch.long, device=dev)
        self._pf_offs = torch.as_tensor(offsets, dtype=torch.long, device=dev)
        self._pf_len = torch.as_tensor(lengths, dtype=torch.long, device=dev)

    def _pooled(self, user_ids, drop_items, drop_mask):
        dev = user_ids.device
        uniq, inv = torch.unique(user_ids, return_inverse=True)
        lens = self._pf_len[uniq]
        total = int(lens.sum())

        if total == 0:
            return (torch.zeros(len(user_ids), self.mf_dim, device=dev),
                    torch.zeros(len(user_ids), self.user_dim, device=dev))

        seg = torch.repeat_interleave(torch.arange(len(uniq), device=dev), lens)
        within = (torch.arange(total, device=dev)
                  - torch.repeat_interleave(torch.cumsum(lens, 0) - lens, lens))
        items = self._pf_flat[self._pf_offs[uniq][seg] + within]

        drop = drop_mask.to(torch.float32)
        counts = (lens[inv] - drop).clamp(min=1).unsqueeze(1)

        out = []
        for table, dim in ((self.gmf_ctx, self.mf_dim), (self.mlp_ctx, self.user_dim)):
            summed = torch.zeros(len(uniq), dim, device=dev).index_add_(0, seg, table(items))
            out.append((summed[inv] - drop.unsqueeze(1) * table(drop_items)) / counts)
        return out[0], out[1]

    def forward(self, user_ids, item_ids, item_content, is_positive):
        drop_mask = is_positive & (item_ids != TAIL_IDX)
        gmf_user, mlp_user = self._pooled(user_ids, item_ids, drop_mask)
        logits = self._combine(gmf_user, mlp_user, *self._item_side(item_ids, item_content))
        return logits if self.use_logits else torch.sigmoid(logits)

    def cold_user(self, owned_game_ids, item_to_idx):
        core = [item_to_idx[g] for g in owned_game_ids
                if item_to_idx.get(g, TAIL_IDX) != TAIL_IDX]
        dev = self._device()
        if not core:
            return (torch.zeros(1, self.mf_dim, device=dev),
                    torch.zeros(1, self.user_dim, device=dev), True)
        idx = torch.tensor(core, dtype=torch.long, device=dev)
        return (self.gmf_ctx(idx).mean(dim=0, keepdim=True),
                self.mlp_ctx(idx).mean(dim=0, keepdim=True), False)


class HybridNeuMF(_NeuMFCore):

    def __init__(self, num_users, num_items, content_dim,
                 mf_dim=8, mlp_dims=(64, 32, 16, 8),
                 content_hidden_dims=(128, 64), use_logits=True):
        super().__init__(num_items, content_dim, mf_dim, mlp_dims,
                         content_hidden_dims, use_logits)
        self.config = {
            'num_users': num_users,
            'num_items': num_items,
            'content_dim': content_dim,
            'mf_dim': mf_dim,
            'mlp_dims': list(mlp_dims),
            'content_hidden_dims': list(content_hidden_dims),
            'use_logits': use_logits,
        }
        self.gmf_user_embedding = nn.Embedding(num_users, mf_dim)
        self.mlp_user_embedding = nn.Embedding(num_users, self.user_dim)

        self._init_core()
        nn.init.normal_(self.gmf_user_embedding.weight, std=0.01)
        nn.init.normal_(self.mlp_user_embedding.weight, std=0.01)

    def forward(self, user_ids, item_ids, item_content, is_positive=None):
        logits = self._combine(self.gmf_user_embedding(user_ids),
                               self.mlp_user_embedding(user_ids),
                               *self._item_side(item_ids, item_content))
        return logits if self.use_logits else torch.sigmoid(logits)

    def mean_user(self):
        return (self.gmf_user_embedding.weight.mean(dim=0, keepdim=True),
                self.mlp_user_embedding.weight.mean(dim=0, keepdim=True))

    def cold_user(self, owned_game_ids, item_to_idx):
        core = [item_to_idx[g] for g in owned_game_ids
                if item_to_idx.get(g, TAIL_IDX) != TAIL_IDX]
        if not core:
            gmf, mlp = self.mean_user()
            return gmf, mlp, True
        idx = torch.tensor(core, dtype=torch.long, device=self._device())
        return (self.gmf_item_embedding(idx).mean(dim=0, keepdim=True),
                self.mlp_item_embedding(idx).mean(dim=0, keepdim=True), False)
