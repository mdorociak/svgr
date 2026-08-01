
import numpy as np
import torch
import pickle
from typing import List, Tuple, Optional
from pathlib import Path

from .model import HybridNeuMF, ContentProcessor, TAIL_IDX


class RecommendationService:

    def __init__(self, model_path: str = "hybrid_neumf_improved.pkl"):
        self.model = None
        self.item_to_idx = None
        self.game_to_features = None
        self.owner_counts = None
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
        self.model = HybridNeuMF(**config)
        self.model.load_state_dict(checkpoint['model_state_dict'])
        self.model.eval()

        self.item_to_idx = checkpoint['item_to_idx']
        self.game_to_features = checkpoint['game_to_features']
        self.owner_counts = checkpoint.get('owner_counts', None)

    def is_game_known(self, game_id: int) -> bool:
        idx = self.item_to_idx.get(game_id)
        return idx is not None and idx != TAIL_IDX

    def is_game_scoreable(self, game_id: int) -> bool:
        return game_id in self.game_to_features

    def get_recommendations(self, owned_games: dict,
                            top_k: int = 20) -> List[Tuple[int, float]]:
        if self.model is None:
            return []
        return self.model.get_recommendations_for_games(
            owned_games=owned_games,
            item_to_idx=self.item_to_idx,
            game_to_features=self.game_to_features,
            top_k=top_k,
            exclude_owned=True,
            owner_counts=self.owner_counts,
        )

    def predict_game(self, owned_game_ids: List[int],
                     target_game_id: int) -> Optional[float]:
 
        if self.model is None:
            return None

        if target_game_id in self.game_to_features:
            return self.model.predict_single_game(
                owned_game_ids=owned_game_ids,
                target_game_id=target_game_id,
                item_to_idx=self.item_to_idx,
                game_to_features=self.game_to_features
            )

        if self.is_game_known(target_game_id):
            return self.model.predict_single_game_collaborative(
                owned_game_ids=owned_game_ids,
                target_game_id=target_game_id,
                item_to_idx=self.item_to_idx
            )

        return None


_recommendation_service: Optional[RecommendationService] = None


def get_recommendation_service() -> RecommendationService:
    global _recommendation_service
    if _recommendation_service is None:
        _recommendation_service = RecommendationService()
    return _recommendation_service