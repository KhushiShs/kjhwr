"""FastAPI application entrypoint for WindWise backend."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.data_store import get_data_store
from app.routes import router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("windwise")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Lifespan context manager: preload dataset snapshot into memory at startup."""
    settings = get_settings()
    logger.info("Initializing WindWise data store from %s", settings.data_dir)
    store = get_data_store()
    logger.info(
        "DataStore loaded successfully (%d actual periods, %s to %s)",
        store.total_actual_periods,
        store.min_date,
        store.max_date,
    )
    yield
    logger.info("WindWise backend shutting down")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application instance."""
    settings = get_settings()

    app = FastAPI(
        title="WindWise API",
        description=(
            "UK Day-Ahead Wind Forecast Decision API for energy buyers. "
            "Evaluates Elexon BMRS WINDFOR forecasts against FUELHH actuals at decision cutoff."
        ),
        version="0.1.0",
        lifespan=lifespan,
    )

    origins = settings.cors_origins
    logger.info("Configuring CORS with allowed origins: %s", origins)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins if origins != ["*"] else ["*"],
        allow_credentials=True if origins != ["*"] else False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(router)
    return app


app = create_app()

if __name__ == "__main__":
    cfg = get_settings()
    uvicorn.run("app.main:app", host=cfg.host, port=cfg.port, reload=True)
