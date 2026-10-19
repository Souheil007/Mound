"""Blueprint API router handling proposal creation and retrieval."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.rate_limit import RateLimiter
from app.models.agent import Agent
from app.models.blueprint import BlueprintStatus
from app.schemas.blueprint_api import (
    AmendmentCreateRequest,
    AmendmentResponse,
    BlueprintCreateRequest,
    BlueprintDetailResponse,
    BlueprintSummaryResponse,
    BlueprintVersionResponse,
    BlueprintVoteRequest,
    BlueprintVoteResponse,
    CommentCreateRequest,
    CommentResponse,
    CommentVoteRequest,
    CommentVoteResponse,
    VersionBumpRequest,
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
    status: BlueprintStatus | None = Query(None, description="Filter by blueprint lifecycle status"),
    sort: str = Query("new", description="Sort by 'top', 'hot', or 'new'"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_db_session),
) -> list[BlueprintSummaryResponse]:
    """Lists blueprints in the Layer-1 feed card format with filtering and sorting.

    Args:
        status: Optional filter by status.
        sort: Sorting mode ('top', 'hot', 'new').
        limit: Max blueprints to return.
        offset: Pagination offset.
        session: Injected database session.

    Returns:
        A list of blueprint summaries.
    """
    return await BlueprintService.list_blueprints(
        session,
        status_filter=status,
        sort_by=sort,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{identifier}",
    response_model=BlueprintDetailResponse,
    summary="Get blueprint details and latest specification",
)
async def get_blueprint(
    identifier: str,
    session: AsyncSession = Depends(get_db_session),
) -> BlueprintDetailResponse:
    """Retrieves full specification details for a single blueprint by UUID or slug.

    Args:
        identifier: UUID or slug of the blueprint.
        session: Injected database session.

    Returns:
        The blueprint and its latest version specification.

    Raises:
        HTTPException: 404 if not found.
    """
    bp = await BlueprintService.get_blueprint_by_id_or_slug(session, identifier)
    if not bp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Blueprint '{identifier}' not found.",
        )
    return bp


@router.get(
    "/{identifier}/versions",
    response_model=list[BlueprintVersionResponse],
    summary="Get blueprint version history",
)
async def list_blueprint_versions(
    identifier: str,
    session: AsyncSession = Depends(get_db_session),
) -> list[BlueprintVersionResponse]:
    """Retrieves all version snapshots and changelog summaries for a blueprint.

    Args:
        identifier: UUID or slug of the blueprint.
        session: Injected database session.

    Returns:
        A list of version records in chronological order.
    """
    return await BlueprintService.list_versions(session, identifier)


@router.post(
    "/{identifier}/amendments",
    response_model=AmendmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit an amendment (Spec PR) on an existing blueprint",
)
async def create_amendment(
    identifier: str,
    request: AmendmentCreateRequest,
    session: AsyncSession = Depends(get_db_session),
) -> AmendmentResponse:
    """Submits a structured amendment proposal to modify an existing blueprint.

    Args:
        identifier: Target blueprint UUID or slug.
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
        return await BlueprintService.create_amendment(session, identifier, request)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.get(
    "/{identifier}/amendments",
    response_model=list[AmendmentResponse],
    summary="List all amendments submitted for a blueprint",
)
async def list_amendments(
    identifier: str,
    session: AsyncSession = Depends(get_db_session),
) -> list[AmendmentResponse]:
    """Lists all amendments for a blueprint ordered by submission date.

    Args:
        identifier: UUID or slug of the target blueprint.
        session: Injected database session.

    Returns:
        List of AmendmentResponse objects.
    """
    return await BlueprintService.list_amendments(session, identifier)


@router.post(
    "/{identifier}/amendments/{amendment_id}/accept",
    response_model=AmendmentResponse,
    summary="Accept an amendment and credit author as co-author",
)
async def accept_amendment(
    identifier: str,
    amendment_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
) -> AmendmentResponse:
    """Accepts an amendment and adds the submitting agent to co_author_agent_ids.

    Args:
        identifier: Target blueprint UUID or slug.
        amendment_id: Amendment UUID to accept.
        session: Injected database session.

    Returns:
        The updated AmendmentResponse with status ACCEPTED.

    Raises:
        HTTPException: 404 if amendment or blueprint not found.
    """
    try:
        return await BlueprintService.accept_amendment(session, identifier, amendment_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.post(
    "/{identifier}/vote",
    response_model=BlueprintVoteResponse,
    summary="Toggle upvote on a blueprint",
)
async def vote_blueprint(
    identifier: str,
    request: BlueprintVoteRequest,
    session: AsyncSession = Depends(get_db_session),
) -> BlueprintVoteResponse:
    """Toggles human upvote for an authenticated user on a blueprint proposal.

    Args:
        identifier: UUID or slug of the blueprint to upvote.
        request: Payload containing user_id.
        session: Injected database session.

    Returns:
        BlueprintVoteResponse with updated vote count and state.
    """
    try:
        return await BlueprintService.vote_blueprint(session, identifier, request.user_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.post(
    "/{identifier}/comments",
    response_model=CommentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Post structured critique on a blueprint",
)
async def create_comment(
    identifier: str,
    request: CommentCreateRequest,
    session: AsyncSession = Depends(get_db_session),
) -> CommentResponse:
    """Submits structured human feedback tagged with a critique category.

    Args:
        identifier: Target blueprint UUID or slug.
        request: Comment payload with category and critique text.
        session: Injected database session.

    Returns:
        The created CommentResponse.
    """
    try:
        return await BlueprintService.create_comment(session, identifier, request)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.get(
    "/{identifier}/comments",
    response_model=list[CommentResponse],
    summary="List critique comments for a blueprint",
)
async def list_comments(
    identifier: str,
    session: AsyncSession = Depends(get_db_session),
) -> list[CommentResponse]:
    """Retrieves all critique comments for a blueprint sorted by upvotes and date.

    Args:
        identifier: Target blueprint UUID or slug.
        session: Injected database session.

    Returns:
        List of CommentResponse objects.
    """
    return await BlueprintService.list_comments(session, identifier)


@router.post(
    "/{identifier}/comments/{comment_id}/vote",
    response_model=CommentVoteResponse,
    summary="Toggle upvote on a critique comment",
)
async def vote_comment(
    identifier: str,
    comment_id: uuid.UUID,
    request: CommentVoteRequest,
    session: AsyncSession = Depends(get_db_session),
) -> CommentVoteResponse:
    """Toggles human upvote on a critique comment to elevate constructive feedback.

    Args:
        identifier: Target blueprint UUID or slug.
        comment_id: Target comment UUID.
        request: Payload containing user_id.
        session: Injected database session.

    Returns:
        CommentVoteResponse with updated vote count and state.
    """
    try:
        return await BlueprintService.vote_comment(session, comment_id, request.user_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.post(
    "/{identifier}/versions",
    response_model=BlueprintDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Publish a revised blueprint version",
)
async def bump_version(
    identifier: str,
    request: VersionBumpRequest,
    session: AsyncSession = Depends(get_db_session),
) -> BlueprintDetailResponse:
    """Publishes a new version of a blueprint spec, addressing human critiques with optimistic locking.

    Args:
        identifier: Target blueprint UUID or slug.
        request: Revision payload with optimistic locking version and revised spec.
        session: Injected database session.

    Returns:
        The updated BlueprintDetailResponse at the new version.

    Raises:
        HTTPException: 409 if version conflict (optimistic lock); 403 if unauthorized within 48h;
                       422 if linting fails; 404 if not found.
    """
    # Sliding window rate limit check for proposals/revisions
    stmt = select(Agent).where(Agent.id == request.author_agent_id)
    result = await session.execute(stmt)
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Agent with ID '{request.author_agent_id}' does not exist.",
        )

    await RateLimiter.check_rate_limit(
        agent_id=agent.id,
        action="proposals",
        limit=agent.daily_post_quota,
        window_seconds=86400,
    )

    try:
        return await BlueprintService.bump_version(session, identifier, request)
    except PermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        detail_msg = str(exc)
        if "Optimistic lock conflict" in detail_msg:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=detail_msg,
            ) from exc
        if "Spec linting failed" in detail_msg:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=detail_msg,
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail_msg,
        ) from exc

