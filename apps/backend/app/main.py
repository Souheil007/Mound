"""Main entrypoint for the Mound FastAPI application."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.blueprints import router as blueprints_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Manages application startup and shutdown lifecycle.

    Args:
        app: The FastAPI application instance.

    Yields:
        None when startup completes.
    """
    yield


app = FastAPI(
    title="Mound Backend API",
    description="The Crowdsourced AI Engineering Forge for autonomous planning agents and developers.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(blueprints_router, prefix="/api/v1")


@app.get("/health", tags=["System"])
async def health_check() -> dict[str, str]:
    """Returns application health status.

    Returns:
        A dict with the current status and version.
    """
    return {"status": "ok", "version": "0.1.0"}
