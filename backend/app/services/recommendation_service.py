import pickle
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import torch

from app.core.config import settings
from . import model as model_module
from .model import HybridNeuMF, ProfileNeuMF, TAIL_IDX


class _ModelUnpickler(pickle.Unpickler):

    def find_class(self, module, name):
        if module == "model" and hasattr(model_module, name):
            return getattr(model_module, name)
        return super().find_class(module, name)


class RecommendationService:

    def __init__(self, model_path: Optional[str] = None):
        self.model_path = model_path or settings.model_path
        self.model = None
        self.item_to_idx: Dict[int, int] = {}
        self.game_to_features: Dict[int, np.ndarray] = {}
        self.min_profile_minutes = 0
        self._candidates: List[int] = []
        self._position: Dict[int, int] = {}
        self._cache = None
        self._load_model()


    def _load_model(self):
        path = Path(self.model_path)
        if not path.exists():
            raise FileNotFoundError(f"Model file not found: {self.model_path}")

        with open(path, "rb") as f:
            checkpoint = _ModelUnpickler(f).load()

        cls = ProfileNeuMF if checkpoint.get("model_class") == "ProfileNeuMF" else HybridNeuMF
        self.model = cls(**checkpoint["model_config"])
        self.model.load_state_dict(checkpoint["model_state_dict"])
        self.model.eval()

        self.item_to_idx = {int(k): int(v) for k, v in checkpoint["item_to_idx"].items()}
        self.game_to_features = {int(k): v for k, v in checkpoint["game_to_features"].items()}

        train_cfg = checkpoint.get("train_config") or {}
        self.min_profile_minutes = int(round(float(train_cfg.get("min_playtime", 0.0)) * 60))

        self._candidates = list(self.game_to_features)
        self._position = {g: i for i, g in enumerate(self._candidates)}
        item_ids = torch.tensor([self.item_to_idx.get(g, TAIL_IDX) for g in self._candidates],
                                dtype=torch.long)
        feats = torch.from_numpy(np.asarray([self.game_to_features[g] for g in self._candidates],
                                            dtype=np.float32))
        self._cache = self.model.item_cache(item_ids, feats)

    def is_game_known(self, game_id: int) -> bool:
        idx = self.item_to_idx.get(game_id)
        return idx is not None and idx != TAIL_IDX

    def is_game_scoreable(self, game_id: int) -> bool:
        return game_id in self.game_to_features

    def _profile(self, owned_games: Dict[int, int]) -> List[int]:
        played = [g for g, minutes in owned_games.items()
                  if (minutes or 0) >= self.min_profile_minutes]
        return played or list(owned_games)


    @torch.no_grad()
    def get_recommendations(self, owned_games: Dict[int, int],
                            top_k: int = 20) -> List[Tuple[int, float]]:
        if self.model is None or not self._candidates:
            return []

        gmf, mlp, _ = self.model.cold_user(self._profile(owned_games), self.item_to_idx)
        scores = self.model.score_cached(gmf, mlp, self._cache).clone()

        owned_pos = [self._position[g] for g in owned_games if g in self._position]
        if owned_pos:
            scores[torch.tensor(owned_pos, dtype=torch.long)] = float("-inf")

        k = min(top_k, len(self._candidates) - len(owned_pos))
        if k <= 0:
            return []
        top = torch.topk(scores, k)
        return [(int(self._candidates[i]), float(s))
                for s, i in zip(top.values.tolist(), top.indices.tolist())]

    def predict_game(self, owned_game_ids: List[int],
                     target_game_id: int) -> Optional[float]:
        if self.model is None:
            return None

        if target_game_id in self.game_to_features:
            return self.model.predict_single_game(
                owned_game_ids, target_game_id, self.item_to_idx, self.game_to_features)

        if self.is_game_known(target_game_id):
            return self.model.predict_single_game_collaborative(
                owned_game_ids, target_game_id, self.item_to_idx)

        return None


_recommendation_service: Optional[RecommendationService] = None


def get_recommendation_service() -> RecommendationService:
    global _recommendation_service
    if _recommendation_service is None:
        _recommendation_service = RecommendationService()
    return _recommendation_service
