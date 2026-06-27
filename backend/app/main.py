"""Chronos AI — FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config.settings import get_settings
from app.database.db import Database
from app.middleware.error_handler import ErrorHandlerMiddleware
from app.routes import auth_router, chat_router, dashboard_router, tasks_router
from app.scheduler import scheduler, setup_scheduler
from app.utils.helpers import setup_logging

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    setup_logging()
    logger.info("Starting %s v%s", settings.app_name, settings.app_version)
    settings.log_startup_status()

    await Database.connect(settings)
    setup_scheduler(settings)
    scheduler.start()
    logger.info("Background scheduler started")

    yield

    scheduler.shutdown(wait=False)
    await Database.disconnect()
    logger.info("Shutdown complete")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=(
            "Chronos AI — Autonomous AI productivity companion that understands tasks, "
            "predicts deadline risks, plans work, monitors progress, and motivates users."
        ),
        lifespan=lifespan,
    )

    app.add_middleware(ErrorHandlerMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(auth_router)
    app.include_router(tasks_router)
    app.include_router(dashboard_router)
    app.include_router(chat_router)

    @app.get("/health")
    async def health_check():
        return {
            "status": "healthy",
            "app": settings.app_name,
            "version": settings.app_version,
        }

    return app


app = create_app()
