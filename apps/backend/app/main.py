"""Main entrypoint for the Mound FastAPI application."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Manages application startup and shutdown lifecycle.

    Args:
        app: The FastAPI application instance.

    Yields:
        None when startup completes.
    """
    # Startup actions (e.g. database pool, redis connection)
    yield
    # Shutdown actions (e.g. close connections)


app = FastAPI(
    title="Mound API",
    description="The Idea-to-Blueprint Forge for autonomous planning agents and human builders.",
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


@app.get("/health", tags=["System"])
async def health_check() -> dict[str, str]:
    """Returns application health status.

    Returns:
        A dict with the current status and version.
    """
    return {"status": "ok", "version": "0.1.0"}
