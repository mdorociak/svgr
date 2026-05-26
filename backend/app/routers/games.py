from fastapi import APIRouter, HTTPException, status, Query
from app.models.schemas import GamesResponse, SteamProfile, GameDetails, SearchResult, SearchResponse
from app.services.steam_service import SteamService

router = APIRouter(prefix="/api", tags=["games"])

@router.get("/games/{steam_id}", response_model=GamesResponse)
async def get_user_games(steam_id: str):
    steam_service= SteamService()

    if not await steam_service.validate_steam_id(steam_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Steam user not found or the profile is private."
        )
    
    games = await steam_service.get_player_games(steam_id)

    if games is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Unable to fetch games. User doesn't own any games or the profile is private"
        )
    
    return GamesResponse(
        steam_id=steam_id,
        game_count=len(games),
        games=games
    )

@router.get("/profile/{steam_id}", response_model=SteamProfile)
async def get_user_profile(steam_id: str):
    steam_service = SteamService()

    profile = await steam_service.get_player_summary(steam_id)

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Steam user not found."
        )
    
    return profile

@router.get("/game/{appid}", response_model=GameDetails)
async def get_game_details(appid: int):
    steam_service = SteamService()

    details = await steam_service.get_full_game_details(appid)

    if not details:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Game not found or unavailable."
        )
    
    return GameDetails(**details)

@router.get("/search", response_model=SearchResponse)
async def search_games(
    term: str = Query(..., min_length=1, description="Search term"),
    page: int = Query(1, ge=1, description="Page number")
):
    steam_service = SteamService()

    results = await steam_service.search_games(term, page)

    if results is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to search games"
        )
    
    return SearchResponse(
        results=[SearchResult(**r) for r in results]
    )