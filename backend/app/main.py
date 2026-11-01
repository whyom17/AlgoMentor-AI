"""
AlgoMentor AI — FastAPI application entry point.
"""

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routes import api_router
from app.sandbox_adapter import close as close_sandbox

settings = get_settings()
logger = structlog.get_logger(__name__)


def create_app() -> FastAPI:
    app = FastAPI(
        title="AlgoMentor AI",
        description="AI-powered DSA learning platform with execution-aware mentor hints.",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Routes
    app.include_router(api_router)

    @app.get("/health", tags=["health"])
    async def health() -> dict:
        return {"status": "ok", "version": "0.1.0"}

    @app.on_event("shutdown")
    async def on_shutdown() -> None:
        await close_sandbox()
        logger.info("app.shutdown")

    return app


app = create_app()
