from pydantic import BaseModel
from typing import Optional, List

class SteamLoginResponse(BaseModel):
    login_url: str


class SteamProfile(BaseModel):
    steam_id: str
    persona_name: str
    profile_url: str
    avatar: str
    avatar_medium: str
    avatar_full: str

class SteamGame(BaseModel):
    appid: int
    name: str
    playtime_forever: int
    playtime_2weeks: Optional[int] = None
    img_icon_url: str
    img_logo_url: str
    has_community_visible_stats: Optional[bool] = None

class GamesResponse(BaseModel):
    steam_id: str
    game_count: int
    games: List[SteamGame]

class GameDetails(BaseModel):
    appid: int
    name: str
    header_image: Optional[str] = None
    short_description: Optional[str] = None
    developers: Optional[List[str]] = None
    publishers: Optional[List[str]] = None
    release_date: Optional[str] = None
    price_overview: Optional[str] = None
    is_free: Optional[bool] = None
    genres: Optional[List[str]] = None
    categories: Optional[List[str]] = None
    reviews: Optional["GameReviews"] = None

class GameReviews(BaseModel):
    total: int
    score: int
    description: str

class SearchResult(BaseModel):
    appid: int
    name: str
    logo: Optional[str] = None
    price: Optional[str] = None

class SearchResponse(BaseModel):
    results: List[SearchResult]

class RecommendationRequest(BaseModel):
    owned_game_ids: List[int]
    top_k: int = 20

class RecommendedGame(BaseModel):
    appid: int
    score: float
    name: str
    logo: Optional[str] = None

class RecommendationResponse(BaseModel): 
    recommendations: List[RecommendedGame]

class PredictionRequest(BaseModel):
    owned_game_ids: List[int]
    target_game_id: int

class PredictionResponse(BaseModel):
    appid: int
    score: float

class ErrorResponse(BaseModel):
    detail: str