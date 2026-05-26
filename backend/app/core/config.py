from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    steam_api_key: str
    callback_url: str = "http://localhost:8000/auth/steam/callback"

    steam_openid_url: str = "https://steamcommunity.com/openid/login"
    steam_api_base: str = "https://api.steampowered.com"

    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()