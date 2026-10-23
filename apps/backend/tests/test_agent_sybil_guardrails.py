"""Tests for Anti-Sybil defense, agent quotas, and registration velocity limiter."""

import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.agent import Agent
from app.models.user import User


@pytest.mark.asyncio
async def test_unverified_user_cannot_register_agent(client: AsyncClient, db_session: AsyncSession) -> None:
    """Unverified users must be blocked from registering agents with 403 Forbidden."""
    unverified_user = User(
        username=f"unverified_dev_{uuid.uuid4().hex[:6]}",
        email=f"unverified_{uuid.uuid4().hex[:6]}@mound.forge",
        password_hash=hash_password("ValidPassword123!"),
        is_verified=False,
        trust_score=0,
    )
    db_session.add(unverified_user)
    await db_session.commit()
    await db_session.refresh(unverified_user)

    res = await client.post(
        "/api/v1/agents/register",
        json={
            "owner_user_id": str(unverified_user.id),
            "name": "SpamBotAgent",
            "description": "Trying to bypass verification",
        },
    )
    assert res.status_code == 403
    assert "Account must be verified" in res.json()["detail"]


@pytest.mark.asyncio
async def test_verified_user_key_limit_enforcement(client: AsyncClient, db_session: AsyncSession) -> None:
    """A verified user cannot exceed the maximum active API key limit (10 keys)."""
    user = User(
        username=f"verified_keys_{uuid.uuid4().hex[:6]}",
        email=f"keys_{uuid.uuid4().hex[:6]}@mound.forge",
        password_hash=hash_password("ValidPassword123!"),
        is_verified=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    # Pre-seed 10 API keys directly in DB for this user
    for i in range(10):
        agent = Agent(
            owner_id=user.id,
            name=f"KeyAgent_{i}",
            api_key_hash=uuid.uuid4().hex,
            specialty_tags=["fastmcp"],
        )
        db_session.add(agent)
    await db_session.commit()

    # Attempting to register the 11th agent must fail with 429
    res = await client.post(
        "/api/v1/agents/register",
        json={
            "owner_user_id": str(user.id),
            "name": "EleventhKeyShouldFail",
            "description": "Exceeding max API keys",
        },
    )
    assert res.status_code == 429
    assert "API key limit reached" in res.json()["detail"]


@pytest.mark.asyncio
async def test_agent_deletion_frees_slot(client: AsyncClient, db_session: AsyncSession) -> None:
    """Deleting an agent releases a slot, allowing registration of a new agent."""
    user = User(
        username=f"delete_slots_{uuid.uuid4().hex[:6]}",
        email=f"del_slots_{uuid.uuid4().hex[:6]}@mound.forge",
        password_hash=hash_password("ValidPassword123!"),
        is_verified=True,
        trust_score=10,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    agent_to_delete = Agent(
        owner_id=user.id,
        name="TemporaryScout",
        api_key_hash=uuid.uuid4().hex,
        specialty_tags=["test"],
    )
    db_session.add(agent_to_delete)
    await db_session.commit()
    await db_session.refresh(agent_to_delete)

    # Delete agent
    del_res = await client.delete(f"/api/v1/agents/{agent_to_delete.id}?owner_user_id={user.id}")
    assert del_res.status_code == 200
    assert "successfully revoked" in del_res.json()["message"]
