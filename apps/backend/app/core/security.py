"""Authentication and security utilities for agents and users."""

import hashlib
import secrets

from fastapi import HTTPException, status
from fastapi.security import HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent import Agent

security_bearer = HTTPBearer(auto_error=False)


def generate_agent_api_key() -> tuple[str, str]:
    """Generates a secure agent API key and its SHA-256 hash.

    Returns:
        A tuple of (raw_api_key, api_key_hash).
        Only api_key_hash should ever be persisted in the database.
    """
    raw_key = f"mound_sk_{secrets.token_hex(24)}"
    key_hash = hash_api_key(raw_key)
    return raw_key, key_hash


def hash_api_key(api_key: str) -> str:
    """Computes the SHA-256 hash of an agent API key.

    Args:
        api_key: Raw API key string.

    Returns:
        A 64-character hexadecimal SHA-256 digest string.
    """
    return hashlib.sha256(api_key.encode("utf-8")).hexdigest()


async def get_current_agent(
    session: AsyncSession,
    api_key: str,
) -> Agent:
    """Retrieves an active agent by raw API key.

    Args:
        session: Active async database session.
        api_key: Raw API key (from Authorization header or query param).

    Returns:
        The matched Agent model.

    Raises:
        HTTPException: 401 Unauthorized if API key is invalid or agent not found.
    """
    if not api_key or not api_key.startswith("mound_sk_"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key format. Expected 'mound_sk_...'",
            headers={"WWW-Authenticate": "Bearer"},
        )

    key_hash = hash_api_key(api_key)
    stmt = select(Agent).where(Agent.api_key_hash == key_hash)
    result = await session.execute(stmt)
    agent = result.scalar_one_or_none()

    if not agent:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or revoked agent API key.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return agent
