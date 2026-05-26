from fastapi import APIRouter, HTTPException, Depends

from app.models.schemas import (
    RecommendationRequest,
    RecommendationResponse,
    RecommendedGame,
    PredictionRequest,
    PredictionResponse
)
from app.services.recommendation_service import get_recommendation_service, RecommendationService
from app.services.steam_service import get_steam_service, SteamService

router = APIRouter(prefix="/api/recommendations", tags=["recommendations"])

@router.post("", response_model=RecommendationResponse)
async def get_recommendations(
    request: RecommendationRequest,
    rec_service: RecommendationService = Depends(get_recommendation_service),
    steam_service: SteamService = Depends(get_steam_service)
):
    
    if not request.owned_game_ids:
        raise HTTPException(status_code=400, detail="owned_game_ids cannot be empty")
    
    if request.top_k < 1 or request.top_k > 100:
        raise HTTPException(status_code=400, detail="top_k must be between 1 and 100")
    
    recommendations = rec_service.get_recommendations(
        owned_game_ids=request.owned_game_ids,
        top_k=request.top_k
    )

    if not recommendations:
        return RecommendationResponse(recommendations=[])
    
    appids = [appid for appid, _ in recommendations]
    game_info = await steam_service.get_games_basic_info(appids)

    result = []
    for appid, score in recommendations:
        info = game_info.get(appid, {'name': 'Unknown', 'logo': None})
        result.append(RecommendedGame(
            appid=appid,
            score=round(score, 4),
            name=info['name'],
            logo=info['logo']
        ))
    
    return RecommendationResponse(recommendations=result)

@router.post("/predict", response_model=PredictionResponse)
async def predict_game(
    request: PredictionRequest,
    rec_service: RecommendationService = Depends(get_recommendation_service)
):
    if not request.owned_game_ids:
        raise HTTPException(status_code=400, detail="owned_game_ids cannot be empty")
    
    if not rec_service.is_game_known(request.target_game_id):
        raise HTTPException(
            status_code=404,
            detail=f"Game {request.target_game_id} not found in model"
        )
    
    score = rec_service.predict_game(
        owned_game_ids=request.owned_game_ids,
        target_game_id=request.target_game_id
    )

    if score is None:
        raise HTTPException(
            status_code=400,
            detail="Could not generate prediction. Ensure owned games are valid"
        )
    
    return PredictionResponse(
        appid=request.target_game_id,
        score=round(score, 4)
    )