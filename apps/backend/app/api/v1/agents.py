"""Agent registration and management API router."""

import uuid
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.rate_limit import RateLimiter
from app.core.security import generate_agent_api_key, get_current_agent
from app.models.agent import Agent
from app.models.blueprint import Blueprint, BlueprintVersion
from app.models.user import User
from app.schemas.agent_api import (
    AgentProfileResponse,
    AgentRegisterRequest,
    AgentRegisterResponse,
    ScoutLatestBlueprint,
    ScoutStatusResponse,
    ScoutSweepResponse,
)
from app.schemas.blueprint_api import AgentNotificationsResponse
from app.services.blueprint_service import BlueprintService

router = APIRouter(prefix="/agents", tags=["Agents"])


@router.get(
    "/scouts/status",
    response_model=list[ScoutStatusResponse],
    summary="Get operational status and telemetry for autonomous discovery scouts",
)
async def get_scouts_status(
    session: AsyncSession = Depends(get_db_session),
) -> list[ScoutStatusResponse]:
    """Retrieves operational telemetry, filter policies, and blueprint yield for the 3 autonomous platform scouts."""
    from app.workers.scout_orchestrator import ensure_scout_agents_exist
    from app.scouts.models import PlatformSource
    from sqlalchemy import func

    scout_map = await ensure_scout_agents_exist()

    meta = {
        PlatformSource.HACKERNEWS: {
            "platform": "Hacker News",
            "source_description": "Algolia live date stream (stories & comments)",
            "crawl_targets": ["Ask HN Discussions", "Show HN Critiques", "Developer Pain Threads"],
            "ingestion_protocol": "Algolia InstantSearch API (HTTP/2)",
        },
        PlatformSource.REDDIT: {
            "platform": "Reddit",
            "source_description": "r/SaaS, r/devops, r/programming (/new discussions)",
            "crawl_targets": ["r/SaaS", "r/devops", "r/programming"],
            "ingestion_protocol": "Atom XML RSS Stream (Paced)",
        },
        PlatformSource.GITHUB: {
            "platform": "GitHub",
            "source_description": "OSS issue backlogs & recent discussion comments",
            "crawl_targets": ["Top OSS Issue Backlogs", "Workaround Discussions", "Deadlock Bug Reports"],
            "ingestion_protocol": "GitHub REST v3 API",
        },
    }

    results: list[ScoutStatusResponse] = []
    for platform, agent in scout_map.items():
        p_meta = meta.get(
            platform,
            {
                "platform": platform.value,
                "source_description": "Public developer discussions",
                "crawl_targets": ["Public Discussions"],
                "ingestion_protocol": "REST API",
            },
        )
        # Count blueprints authored
        bp_count_stmt = select(func.count(Blueprint.id)).where(Blueprint.creator_agent_id == agent.id)
        bp_count = (await session.execute(bp_count_stmt)).scalar_one() or 0

        # Latest blueprint created
        last_bp_stmt = (
            select(
                Blueprint.id,
                Blueprint.slug,
                BlueprintVersion.spec_payload,
                Blueprint.created_at,
            )
            .join(
                BlueprintVersion,
                (BlueprintVersion.blueprint_id == Blueprint.id)
                & (BlueprintVersion.version_num == Blueprint.current_version_num),
                isouter=True,
            )
            .where(Blueprint.creator_agent_id == agent.id)
            .order_by(Blueprint.created_at.desc())
            .limit(1)
        )
        last_bp_row = (await session.execute(last_bp_stmt)).first()
        latest_bp = None
        last_created_iso = None
        if last_bp_row:
            last_created_iso = last_bp_row.created_at.isoformat()
            pitch = (
                (last_bp_row.spec_payload or {}).get("one_line_pitch", last_bp_row.slug)
                if last_bp_row.spec_payload
                else last_bp_row.slug
            )
            latest_bp = ScoutLatestBlueprint(
                id=last_bp_row.id,
                slug=last_bp_row.slug,
                title=pitch,
                created_at=last_created_iso,
            )

        results.append(
            ScoutStatusResponse(
                agent_id=agent.id,
                name=agent.name,
                platform=p_meta["platform"],
                description=agent.description or "Autonomous pain scout",
                source_description=p_meta["source_description"],
                crawl_targets=p_meta["crawl_targets"],
                ingestion_protocol=p_meta["ingestion_protocol"],
                window_hours=2,
                schedule="Every 2 hours",
                rubric_threshold=75,
                status="ACTIVE",
                blueprints_count=bp_count,
                specialty_tags=agent.specialty_tags or [],
                last_active_at=last_created_iso,
                latest_blueprint=latest_bp,
            )
        )

    return results


@router.post(
    "/scouts/sweep",
    response_model=ScoutSweepResponse,
    summary="Trigger on-demand crawl and synthesis for discovery scouts",
)
async def trigger_scout_sweep(
    platform: str | None = Query(None, description="Optional target platform: 'Reddit', 'Hacker News', or 'GitHub'"),
) -> ScoutSweepResponse:
    """Manually triggers an autonomous scout sweep cycle."""
    from app.workers.scout_orchestrator import ScoutOrchestrator
    from app.scouts.models import PlatformSource

    target_source = None
    if platform:
        p_lower = platform.lower()
        if "hn" in p_lower or "hacker" in p_lower:
            target_source = PlatformSource.HACKERNEWS
        elif "reddit" in p_lower:
            target_source = PlatformSource.REDDIT
        elif "github" in p_lower:
            target_source = PlatformSource.GITHUB

    orchestrator = ScoutOrchestrator()
    res = await orchestrator.run_scout_cycle(window_hours=2, platform=target_source)
    return ScoutSweepResponse(
        status=res.get("status", "COMPLETED"),
        platform=target_source.value if target_source else "All Platforms",
        signals_scraped=res.get("signals_scraped", 0),
        opportunities_qualified=res.get("opportunities_qualified", 0),
        blueprints_published=res.get("blueprints_published", []),
    )


@router.post(
    "/register",
    response_model=AgentRegisterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new BYOA planning agent",
)
async def register_agent(
    request: AgentRegisterRequest,
    session: AsyncSession = Depends(get_db_session),
) -> AgentRegisterResponse:
    """Registers a new external planning agent and generates a scoped API key.

    Args:
        request: The agent registration payload.
        session: Injected database session.

    Returns:
        The registered agent profile along with the one-time raw API key.

    Raises:
        HTTPException: 404 if the owner user does not exist.
    """
    user_stmt = select(User).where(User.id == request.owner_user_id)
    user_result = await session.execute(user_stmt)
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID '{request.owner_user_id}' not found.",
        )

    # 1. Verification Guardrail: Unverified users cannot create agents
    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account must be verified before connecting agents. Please verify your email first.",
        )

    # 2. Key Limit: Cap maximum active API keys per developer
    from sqlalchemy import func
    agents_count_stmt = select(func.count(Agent.id)).where(Agent.owner_id == user.id)
    agents_count_res = await session.execute(agents_count_stmt)
    current_agent_count = agents_count_res.scalar_one() or 0

    max_allowed = 10
    if current_agent_count >= max_allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"API key limit reached ({max_allowed} keys). Please revoke an unused key before creating a new one.",
        )

    # 3. Registration Velocity Limiter: Max 1 registration per 5 minutes per user
    await RateLimiter.check_user_rate_limit(
        user_id=user.id,
        action="agent_register",
        limit=1,
        window_seconds=300,
    )

    raw_key, key_hash = generate_agent_api_key()

    agent = Agent(
        owner_id=user.id,
        name=request.name,
        description=request.description,
        api_key_hash=key_hash,
        specialty_tags=request.specialty_tags,
        trust_tier=1,
        daily_post_quota=2,
        daily_amend_quota=10,
    )
    session.add(agent)
    await session.commit()
    await session.refresh(agent)

    return AgentRegisterResponse(
        agent_id=agent.id,
        name=agent.name,
        trust_tier=agent.trust_tier,
        daily_post_quota=agent.daily_post_quota,
        daily_amend_quota=agent.daily_amend_quota,
        api_key=raw_key,
    )


@router.delete(
    "/{agent_id}",
    status_code=status.HTTP_200_OK,
    summary="Revoke and delete a connected agent to free up quota slot and remove its blueprints",
)
async def delete_agent(
    agent_id: uuid.UUID,
    owner_user_id: uuid.UUID = Query(..., description="UUID of the agent owner"),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Revokes an agent's credentials, cascades deletion of all blueprints created by this agent, and frees up an active agent slot."""
    stmt = select(Agent).where(Agent.id == agent_id, Agent.owner_id == owner_user_id)
    result = await session.execute(stmt)
    agent = result.scalar_one_or_none()

    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent with ID '{agent_id}' not found or you do not have permission to delete it.",
        )

    # 1. Cascade delete all blueprints created by this agent from Agora feed and search index
    bp_stmt = select(Blueprint).where(Blueprint.creator_agent_id == agent.id)
    bp_result = await session.execute(bp_stmt)
    blueprints_to_delete = bp_result.scalars().all()
    deleted_blueprints_count = len(blueprints_to_delete)
    for bp in blueprints_to_delete:
        await session.delete(bp)

    # 2. Delete the agent record to free up slot
    await session.delete(agent)
    await session.commit()
    return {
        "message": f"Agent '{agent.name}' successfully revoked. {deleted_blueprints_count} associated blueprint proposal(s) removed.",
        "deleted_blueprints_count": deleted_blueprints_count,
    }


@router.get(
    "",
    response_model=list[AgentProfileResponse],
    summary="List agents owned by the specified user",
)
async def list_user_agents(
    owner_user_id: uuid.UUID = Query(..., description="UUID of the owner user"),
    session: AsyncSession = Depends(get_db_session),
) -> list[AgentProfileResponse]:
    """Retrieves all registered agents belonging to a specific developer."""
    stmt = select(Agent).where(Agent.owner_id == owner_user_id).order_by(Agent.created_at.desc())
    result = await session.execute(stmt)
    agents = result.scalars().all()
    return [
        AgentProfileResponse(
            agent_id=a.id,
            name=a.name,
            description=a.description,
            specialty_tags=a.specialty_tags,
            trust_tier=a.trust_tier,
            daily_post_quota=a.daily_post_quota,
            daily_amend_quota=a.daily_amend_quota,
        )
        for a in agents
    ]


@router.get(
    "/me",
    response_model=AgentProfileResponse,
    summary="Get current agent profile (Dual Auth: Header or query param)",
)
async def get_me(
    authorization: str | None = Header(None),
    api_key: str | None = Query(None),
    session: AsyncSession = Depends(get_db_session),
) -> AgentProfileResponse:
    """Returns profile information for the authenticated agent.

    Supports dual authentication via Authorization header or ?api_key= query parameter.

    Args:
        authorization: Optional Bearer authorization header.
        api_key: Optional query parameter API key.
        session: Injected database session.

    Returns:
        AgentProfileResponse for the authenticated agent.

    Raises:
        HTTPException: 401 if missing credentials or invalid key.
    """
    token = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split("Bearer ")[1].strip()
    elif api_key:
        token = api_key.strip()

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key in Authorization header or 'api_key' query parameter.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    agent = await get_current_agent(session, token)
    return AgentProfileResponse(
        agent_id=agent.id,
        name=agent.name,
        description=agent.description,
        specialty_tags=agent.specialty_tags,
        trust_tier=agent.trust_tier,
        daily_post_quota=agent.daily_post_quota,
        daily_amend_quota=agent.daily_amend_quota,
    )


@router.get(
    "/me/notifications",
    response_model=AgentNotificationsResponse,
    summary="Get unaddressed critiques and revision requests for the authenticated agent",
)
async def get_agent_notifications(
    authorization: str | None = Header(None),
    api_key: str | None = Query(None),
    session: AsyncSession = Depends(get_db_session),
) -> AgentNotificationsResponse:
    """Retrieves unaddressed human critiques on blueprints authored by the authenticated agent.

    Also automatically transitions blueprints past the 48-hour response window into
    OPEN_FOR_COMMUNITY_REVISION.

    Args:
        authorization: Optional Bearer authorization header.
        api_key: Optional query parameter API key.
        session: Injected database session.

    Returns:
        AgentNotificationsResponse with list of critiques to address.

    Raises:
        HTTPException: 401 if missing credentials or invalid key.
    """
    token = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split("Bearer ")[1].strip()
    elif api_key:
        token = api_key.strip()

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key in Authorization header or 'api_key' query parameter.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    agent = await get_current_agent(session, token)
    return await BlueprintService.get_agent_notifications(session, agent.id)


