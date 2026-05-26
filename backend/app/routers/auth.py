from fastapi import APIRouter, HTTPException, status, Request
from fastapi.responses import HTMLResponse
from app.models.schemas import SteamLoginResponse
from app.core.config import settings
from app.services.steam_service import SteamService
from app.utils.openid import SteamOpenID

router = APIRouter(prefix="/auth", tags=["authentication"])

@router.post("/steam/login", response_model=SteamLoginResponse)
async def initiate_steam_login():
    login_url = SteamOpenID.get_login_url(settings.callback_url)
    return SteamLoginResponse(login_url=login_url)

@router.get("/steam/callback")
async def steam_callback(request: Request):
    params = dict(request.query_params)
    
    try:
        steam_id = await SteamOpenID.verify_response(params)
        
        steam_service = SteamService()
        if not await steam_service.validate_steam_id(steam_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid Steam ID or profile not accessible"
            )
        
        redirect_url = f"svgr://auth/callback?steam_id={steam_id}"
        
        html_content = f"""
        <html>
            <head>
                <title>Redirecting...</title>
                <meta http-equiv="refresh" content="0;url={redirect_url}">
            </head>
            <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
                <h2>Authentication Successful</h2>
                <p>Redirecting to the app...</p>
                <script>
                    window.location.href = '{redirect_url}';
                </script>
            </body>
        </html>
        """
        return HTMLResponse(content=html_content)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Steam authentication failed: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Authentication error: {str(e)}"
        )