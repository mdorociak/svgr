import httpx
import asyncio
from typing import Optional, List
from app.core.config import settings
from app.models.schemas import SteamProfile, SteamGame

class SteamService:
    
    def __init__(self):
        self.api_key = settings.steam_api_key
        self.base_url = settings.steam_api_base
    
    async def get_player_summary(self, steam_id: str) -> Optional[SteamProfile]:

        url = f"{self.base_url}/ISteamUser/GetPlayerSummaries/v2/"
        params = {
            'key': self.api_key,
            'steamids': steam_id
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                
                data = response.json()
                players = data.get('response', {}).get('players', [])
                
                if not players:
                    return None
                
                player = players[0]
                return SteamProfile(
                    steam_id=player['steamid'],
                    persona_name=player['personaname'],
                    profile_url=player['profileurl'],
                    avatar=player['avatar'],
                    avatar_medium=player['avatarmedium'],
                    avatar_full=player['avatarfull']
                )
        except httpx.HTTPError:
            return None
    

    async def get_player_games(self, steam_id: str, include_appinfo: bool = True, 
                               include_played_free_games: bool = True) -> Optional[List[SteamGame]]:
        url = f"{self.base_url}/IPlayerService/GetOwnedGames/v1"

        params = {
            'key': self.api_key,
            'steamid': steam_id,
            'include_appinfo': 1 if include_appinfo else 0,
            'include_played_free_games': 1 if include_played_free_games else 0,
            'format': 'json'
        }

        try:
            async with httpx.AsyncClient() as client:
               response = await client.get(url, params=params) 
               response.raise_for_status()

               data = response.json()
               response_obj = data.get('response', {})

               if 'game_count' not in response_obj:
                   return None

               games_list = response_obj.get('games', [])
               
               games = []
               for game in games_list:
                   games.append(SteamGame(
                       appid=game['appid'],
                       name=game.get('name', 'Unknown'),
                       playtime_forever=game.get('playtime_forever', 0),
                       playtime_2weeks=game.get('playtime_2weeks'),
                       img_icon_url=game.get('img_icon_url', ''),
                       img_logo_url=game.get('img_logo_url', ''),
                       has_community_visible_stats=game.get('has_community_visible_stats')
                   ))
            return games

        except httpx.HTTPError:
            return None


    async def validate_steam_id(self, steam_id: str) -> bool:
        profile = await self.get_player_summary(steam_id)
        return profile is not None

    async def get_game_details(self, appid: int) -> Optional[dict]:
        url = "https://store.steampowered.com/api/appdetails"
        params = {'appids': appid}

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params)
                response.raise_for_status()

                data = response.json()
                app_data = data.get(str(appid), {})

                if not app_data.get('success'):
                    return None

                return app_data.get('data')

        except httpx.HTTPError:
            return None

    async def get_game_reviews(self, appid: int) -> Optional[dict]:
        url = f"https://store.steampowered.com/appreviews/{appid}"
        params = {
            'json': 1,
            'language': 'all',
            'purchase_type': 'all',
            'num_per_page': 0
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params)
                response.raise_for_status()

                data = response.json()
                if not data.get('success'):
                    return None

                summary = data.get('query_summary', {})
                return {
                    'total': summary.get('total_reviews', 0),
                    'score': summary.get('review_score', 0),
                    'description': summary.get('review_score_desc', 'No reviews')
                }

        except httpx.HTTPError:
            return None

    async def get_full_game_details(self, appid: int) -> Optional[dict]:
        import asyncio

        details, reviews = await asyncio.gather(
            self.get_game_details(appid),
            self.get_game_reviews(appid)
        )

        if not details:
            return None

        genres = [g['description'] for g in details.get('genres', [])]
        categories = [c['description'] for c in details.get('categories', [])]

        price_overview = details.get('price_overview')
        price_str = None
        if details.get('is_free'):
            price_str = "Free"
        elif price_overview:
            if price_overview.get('discount_percent', 0) > 0:
                price_str = f"{price_overview['final_formatted']} (-{price_overview['discount_percent']}%)"
            else:
                price_str = price_overview.get('final_formatted')

        release_date = details.get('release_date', {})
        release_str = release_date.get('date') if not release_date.get('coming_soon') else "Coming Soon"

        return {
            'appid': appid,
            'name': details.get('name'),
            'header_image': details.get('header_image'),
            'short_description': details.get('short_description'),
            'developers': details.get('developers', []),
            'publishers': details.get('publishers', []),
            'release_date': release_str,
            'price_overview': price_str,
            'is_free': details.get('is_free', False),
            'genres': genres,
            'categories': categories,
            'reviews': reviews
        }
    
    async def search_games(self, term: str, page: int = 1) -> Optional[List[dict]]:
        import re
       
        url = "https://store.steampowered.com/search/results/"
        params = {
            'term': term,
            'json': 1,
            'page': page
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params)
                response.raise_for_status()

                data = response.json()
                items = data.get('items', [])

                if not items:
                    return []
                
                results = []
                for item in items:
                    logo = item.get('logo', '')

                    match = re.search(r'/apps/(\d+)/', logo)
                    if not match:
                        continue

                    appid = int(match.group(1))

                    results.append({
                        'appid': appid,
                        'name': item.get('name', ''),
                        'logo': logo,
                        'price': item.get('price')
                    })

                return results
            
        except httpx.HTTPError:
            return None
        
    async def get_games_basic_info(self, appids: List[int]) -> dict:
        tasks = [self.get_game_details(appid) for appid in appids]
        responses = await asyncio.gather(*tasks, return_exceptions=True)

        results = {}
        for appid, response in zip(appids, responses):
            if isinstance(response, Exception) or response is None:
                results[appid] = {'name': 'Unknown', 'logo': None}
            else:
                results[appid] = {
                    'name': response.get('name', 'Unknown'),
                    'logo': response.get('header_image')
                }
        return results
        
_steam_service: Optional[SteamService] = None

def get_steam_service() -> SteamService:
    global _steam_service
    if _steam_service is None:
        _steam_service = SteamService()
    return _steam_service

