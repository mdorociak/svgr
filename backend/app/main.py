from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import auth, games, recommendations
from app.core.config import settings

app = FastAPI(
    title="Steam Auth API",
    description="API for Steam authentication",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(games.router)
app.include_router(recommendations.router)

@app.get("/")
async def root():
    return {
        "message": "Steam Auth API is running",
        "version": "1.0.0",
        "status": "healthy"
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "steam_api_configured": bool(settings.steam_api_key),
        "callback_url": settings.callback_url
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)