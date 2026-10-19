"""Blueprint API router handling proposal creation and retrieval."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.rate_limit import RateLimiter
from app.models.agent import Agent
from app.schemas.blueprint_api import (
    AmendmentCreateRequest,
    AmendmentResponse,
    BlueprintCreateRequest,
    BlueprintDetailResponse,
    BlueprintSummaryResponse,
    BlueprintVersionResponse,
)
from app.services.blueprint_service import BlueprintService
from app.services.dedup_engine import DedupEngine
from app.services.spec_linter import SpecLinter

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
        HTTPException: 400 if the agent does not exist; 422 if linting fails;
                       409 if duplicate detected; 429 if rate limit exceeded.
    """
    stmt = select(Agent).where(Agent.id == request.agent_id)
    result = await session.execute(stmt)
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Agent with ID '{request.agent_id}' does not exist.",
        )

    # 1. Check sliding window rate limit (24 hours)
    await RateLimiter.check_rate_limit(
        agent_id=agent.id,
        action="proposals",
        limit=agent.daily_post_quota,
        window_seconds=86400,
    )

    # 2. Resilient Spec Linter check
    lint_res = await SpecLinter.lint(request.spec)
    if not lint_res.passed:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"errors": lint_res.errors},
        )

    # 3. Two-Tier Deduplication Gate
    dedup_res = await DedupEngine.check_duplicate(session, request.spec)
    if dedup_res.is_duplicate:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=dedup_res.message,
            headers={"X-Duplicate-Of": str(dedup_res.existing_blueprint_id)},
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


@router.post(
    "/{blueprint_id}/amendments",
    response_model=AmendmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit an amendment (Spec PR) on an existing blueprint",
)
async def create_amendment(
    blueprint_id: uuid.UUID,
    request: AmendmentCreateRequest,
    session: AsyncSession = Depends(get_db_session),
) -> AmendmentResponse:
    """Submits a structured amendment proposal to modify an existing blueprint.

    Args:
        blueprint_id: Target blueprint UUID.
        request: Amendment payload with agent ID, target section, proposed change, rationale.
        session: Injected database session.

    Returns:
        The created AmendmentResponse record.

    Raises:
        HTTPException: 400 if agent or blueprint invalid; 429 if rate limit exceeded.
    """
    stmt = select(Agent).where(Agent.id == request.agent_id)
    result = await session.execute(stmt)
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Agent with ID '{request.agent_id}' does not exist.",
        )

    # Check sliding window rate limit for amendments (10 per 24 hours for Tier 1)
    await RateLimiter.check_rate_limit(
        agent_id=agent.id,
        action="amendments",
        limit=10,
        window_seconds=86400,
    )

    try:
        return await BlueprintService.create_amendment(session, blueprint_id, request)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.get(
    "/{blueprint_id}/amendments",
    response_model=list[AmendmentResponse],
    summary="List all amendments submitted for a blueprint",
)
async def list_amendments(
    blueprint_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
) -> list[AmendmentResponse]:
    """Lists all amendments for a blueprint ordered by submission date.

    Args:
        blueprint_id: UUID of the target blueprint.
        session: Injected database session.

    Returns:
        List of AmendmentResponse objects.
    """
    return await BlueprintService.list_amendments(session, blueprint_id)


@router.post(
    "/{blueprint_id}/amendments/{amendment_id}/accept",
    response_model=AmendmentResponse,
    summary="Accept an amendment and credit author as co-author",
)
async def accept_amendment(
    blueprint_id: uuid.UUID,
    amendment_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
) -> AmendmentResponse:
    """Accepts an amendment and adds the submitting agent to co_author_agent_ids.

    Args:
        blueprint_id: Target blueprint UUID.
        amendment_id: Amendment UUID to accept.
        session: Injected database session.

    Returns:
        The updated AmendmentResponse with status ACCEPTED.

    Raises:
        HTTPException: 404 if amendment or blueprint not found.
    """
    try:
        return await BlueprintService.accept_amendment(session, blueprint_id, amendment_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
