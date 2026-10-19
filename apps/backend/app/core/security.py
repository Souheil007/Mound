"""Authentication and security utilities for agents and users."""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.database import get_db_session
from app.models.agent import Agent
from app.models.user import User

security_bearer = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    """Hashes a plaintext password using bcrypt."""
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plaintext password against a stored bcrypt hash."""
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))


def generate_verification_code() -> str:
    """Generates a secure 6-digit numeric verification code."""
    return f"{secrets.randbelow(900000) + 100000}"


def create_access_token(subject: str, extra_claims: dict[str, Any] | None = None) -> str:
    """Creates a signed JSON Web Token (JWT) for authenticated human users."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_access_token_expire_minutes)
    payload: dict[str, Any] = {
        "sub": subject,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, Any]:
    """Decodes and validates a JWT access token."""
    try:
        return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session token has expired. Please sign in again.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except jwt.InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token signature.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


async def get_current_user(
    auth: HTTPAuthorizationCredentials | None = Depends(security_bearer),
    session: AsyncSession = Depends(get_db_session),
) -> User:
    """FastAPI dependency resolving the authenticated human developer from a Bearer JWT."""
    if not auth or not auth.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please sign in or pass a Bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = decode_access_token(auth.credentials)
    user_id_str = payload.get("sub")
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Malformed token: missing subject.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        import uuid
        user_uuid = uuid.UUID(user_id_str)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Malformed token: subject is not a valid UUID.",
        ) from exc

    stmt = select(User).options(selectinload(User.agents)).where(User.id == user_uuid)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account no longer exists.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


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

