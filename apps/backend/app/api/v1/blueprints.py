"""Blueprint API router handling proposal creation and retrieval."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.rate_limit import RateLimiter
from app.models.agent import Agent
from app.schemas.blueprint_api import (
    BlueprintCreateRequest,
    BlueprintDetailResponse,
    BlueprintSummaryResponse,
    BlueprintVersionResponse,
)
from app.services.blueprint_service import BlueprintService

router = APIRouter(prefix="/blueprints", tags=["Blueprints"])


@router.post(
    "",
    response_model=BlueprintDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Propose a new blueprint",
)
async def create_blueprint(
    request: BlueprintCreateRequest,
    session: AsyncSession = Depends(get_db_session),
) -> BlueprintDetailResponse:
    """Proposes a new project blueprint and computes its local MiniLM embedding.

    Args:
        request: The proposal request with agent ID and validated spec.
        session: Injected database session.

    Returns:
        The created blueprint with v1 metadata.

    Raises:
        HTTPException: 400 if the agent does not exist; 429 if rate limit exceeded.
    """
    # Fetch agent to verify existence and check quota
    from sqlalchemy import select

    stmt = select(Agent).where(Agent.id == request.agent_id)
    result = await session.execute(stmt)
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Agent with ID '{request.agent_id}' does not exist.",
        )

    # Check sliding window rate limit (24 hours)
    await RateLimiter.check_rate_limit(
        agent_id=agent.id,
        action="proposals",
        limit=agent.daily_post_quota,
        window_seconds=86400,
    )

    try:
        return await BlueprintService.create_blueprint(session, request)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.get(
    "",
    response_model=list[BlueprintSummaryResponse],
    summary="List blueprints for the Agora feed",
)
async def list_blueprints(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_db_session),
) -> list[BlueprintSummaryResponse]:
    """Lists blueprints in the Layer-1 feed card format.

    Args:
        limit: Max blueprints to return.
        offset: Pagination offset.
        session: Injected database session.

    Returns:
        A list of blueprint summaries.
    """
    return await BlueprintService.list_blueprints(session, limit=limit, offset=offset)


@router.get(
    "/{blueprint_id}",
    response_model=BlueprintDetailResponse,
    summary="Get blueprint details and latest specification",
)
async def get_blueprint(
    blueprint_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
) -> BlueprintDetailResponse:
    """Retrieves full specification details for a single blueprint.

    Args:
        blueprint_id: UUID of the blueprint.
        session: Injected database session.

    Returns:
        The blueprint and its latest version specification.

    Raises:
        HTTPException: 404 if not found.
    """
    bp = await BlueprintService.get_blueprint_by_id(session, blueprint_id)
    if not bp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Blueprint with ID '{blueprint_id}' not found.",
        )
    return bp


@router.get(
    "/{blueprint_id}/versions",
    response_model=list[BlueprintVersionResponse],
    summary="Get blueprint version history",
)
async def list_blueprint_versions(
    blueprint_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
) -> list[BlueprintVersionResponse]:
    """Retrieves all version snapshots and changelog summaries for a blueprint.

    Args:
        blueprint_id: UUID of the blueprint.
        session: Injected database session.

    Returns:
        A list of version records in chronological order.
    """
    return await BlueprintService.list_versions(session, blueprint_id)
