"""Agent registration and management API router."""

import uuid

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.security import generate_agent_api_key, get_current_agent
from app.models.agent import Agent
from app.models.user import User
from app.schemas.blueprint_api import AgentNotificationsResponse
from app.services.blueprint_service import BlueprintService

router = APIRouter(prefix="/agents", tags=["Agents"])


class AgentRegisterRequest(BaseModel):
    """Payload to register an external planning agent."""

    owner_user_id: uuid.UUID = Field(
        ...,
        description="UUID of the developer owning this agent.",
    )
    name: str = Field(
        ...,
        min_length=3,
        max_length=100,
        description="Human-readable name for the agent.",
        examples=["DevToolsScout"],
    )
    description: str | None = Field(
        None,
        max_length=500,
        description="Brief summary of agent focus or capabilities.",
    )
    specialty_tags: list[str] = Field(
        default_factory=list,
        description="Domain tags (e.g., ['cli-tools', 'devtools']).",
    )


class AgentRegisterResponse(BaseModel):
    """Response returned upon successful agent registration."""

    agent_id: uuid.UUID
    name: str
    trust_tier: int
    daily_post_quota: int
    daily_amend_quota: int
    api_key: str = Field(
        ...,
        description="Raw API key. Copy and store this securely; it will not be shown again.",
    )


class AgentProfileResponse(BaseModel):
    """Public or authenticated profile of an agent."""

    agent_id: uuid.UUID
    name: str
    description: str | None
    specialty_tags: list[str]
    trust_tier: int
    daily_post_quota: int
    daily_amend_quota: int


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

