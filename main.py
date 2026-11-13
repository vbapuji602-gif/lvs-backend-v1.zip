from typing import Dict, Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import BackendConfig
from .call_screening.main import router as call_screening_router
from .routers.auth import router as auth_router
from .routers.ai import router as ai_router
from .routers.voice import router as voice_router
from .routers.tools import router as tools_router
from .routers.devices import router as devices_router


def create_app() -> FastAPI:
    app = FastAPI(
        title=BackendConfig.APP_NAME,
        version=BackendConfig.VERSION,
        description="LVS Assistant secure backend gateway: auth, multi-provider AI routing, voice, tools, devices, call screening.",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=BackendConfig.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(auth_router)
    app.include_router(ai_router)
    app.include_router(voice_router)
    app.include_router(tools_router)
    app.include_router(devices_router)
    app.include_router(call_screening_router)

    @app.get("/health")
    def health_check() -> Dict[str, Any]:
        return {
            "status": "healthy",
            "service": BackendConfig.APP_NAME,
            "version": BackendConfig.VERSION,
            "providers_configured": {
                "gemini": bool(BackendConfig.GEMINI_API_KEY),
                "groq": bool(BackendConfig.GROQ_API_KEY),
                "openrouter": bool(BackendConfig.OPENROUTER_API_KEY),
                "elevenlabs": bool(BackendConfig.ELEVENLABS_API_KEY),
                "weatherapi": bool(BackendConfig.WEATHERAPI_KEY),
                "coingecko": bool(BackendConfig.COINGECKO_API_KEY),
            },
        }

    return app


app = create_app()

# Keep the old class-based entrypoint importable (used by existing tests)
# as a thin wrapper around the new app for backward compatibility.
class LvsBackendApp:
    def __init__(self):
        self.config = BackendConfig()

    def health_check(self) -> Dict[str, Any]:
        return {
            "status": "healthy",
            "service": self.config.APP_NAME,
            "version": self.config.VERSION,
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
