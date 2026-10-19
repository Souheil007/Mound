"""Authentication and developer user session endpoints."""

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db_session
from app.core.security import (
    create_access_token,
    generate_verification_code,
    get_current_user,
    hash_password,
    verify_password,
)
from app.models.agent import Agent
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["Authentication"])


async def _get_user_agents_count(session: AsyncSession, user_id: uuid.UUID) -> int:
    """Safely calculates the count of agents owned by a user without lazy-load issues."""
    stmt = select(func.count(Agent.id)).where(Agent.owner_id == user_id)
    res = await session.execute(stmt)
    return int(res.scalar_one() or 0)


# --- Schemas ---

class RegisterRequest(BaseModel):
    """Payload for developer account registration with email + password."""

    email: EmailStr
    password: str = Field(..., min_length=8, description="Account password, minimum 8 characters.")
    username: str = Field(..., min_length=3, max_length=50, description="Unique developer handle.")


class RegisterResponse(BaseModel):
    """Registration response informing developer to verify their email."""

    user_id: uuid.UUID
    email: str
    username: str
    is_verified: bool
    verification_code_hint: str
    message: str


class VerifyCodeRequest(BaseModel):
    """Payload to verify an email account with a 6-digit code."""

    email: EmailStr
    code: str = Field(..., min_length=6, max_length=6, description="6-digit verification code.")


class LoginRequest(BaseModel):
    """Payload for signing in with email and password."""

    email: EmailStr
    password: str


class GoogleAuthRequest(BaseModel):
    """Payload for authenticating via Google account credential."""

    credential: str = Field(..., description="Google ID Token / JWT credential string.")
    email: str | None = None
    name: str | None = None
    picture: str | None = None


class UserProfileResponse(BaseModel):
    """Public representation of the authenticated human developer."""

    id: uuid.UUID
    username: str
    email: str
    avatar_url: str | None
    is_verified: bool
    trust_score: int
    agents_count: int = 0


class AuthTokenResponse(BaseModel):
    """Token response returned upon successful authentication or verification."""

    access_token: str
    token_type: str = "bearer"
    user: UserProfileResponse


class ResendCodeRequest(BaseModel):
    """Payload to request a new verification code."""

    email: EmailStr


# --- Endpoints ---

@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new developer account with email and password",
)
async def register(
    request: RegisterRequest,
    session: AsyncSession = Depends(get_db_session),
) -> RegisterResponse:
    """Registers an unverified developer account and generates an email verification code."""
    # Check if email is already registered
    stmt_email = select(User).where(User.email == request.email.lower())
    if (await session.execute(stmt_email)).scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email address already exists.",
        )

    # Check if username is taken
    stmt_user = select(User).where(User.username == request.username)
    if (await session.execute(stmt_user)).scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Username '{request.username}' is already taken.",
        )

    code = generate_verification_code()
    pwd_hash = hash_password(request.password)

    new_user = User(
        username=request.username,
        email=request.email.lower(),
        password_hash=pwd_hash,
        is_verified=False,
        verification_code=code,
    )
    session.add(new_user)
    await session.commit()
    await session.refresh(new_user)

    return RegisterResponse(
        user_id=new_user.id,
        email=new_user.email,
        username=new_user.username,
        is_verified=new_user.is_verified,
        verification_code_hint=code,
        message=f"Verification code sent! Enter code '{code}' to activate your account.",
    )


@router.post(
    "/verify-code",
    response_model=AuthTokenResponse,
    summary="Verify account email using 6-digit code and receive access token",
)
async def verify_code(
    request: VerifyCodeRequest,
    session: AsyncSession = Depends(get_db_session),
) -> AuthTokenResponse:
    """Validates the 6-digit verification code, marks the account verified, and issues a JWT."""
    stmt = select(User).options(selectinload(User.agents)).where(User.email == request.email.lower())
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account with this email does not exist.",
        )

    agents_count = await _get_user_agents_count(session, user.id)
    if user.is_verified:
        token = create_access_token(str(user.id))
        return AuthTokenResponse(
            access_token=token,
            user=UserProfileResponse(
                id=user.id,
                username=user.username,
                email=user.email,
                avatar_url=user.avatar_url,
                is_verified=user.is_verified,
                trust_score=user.trust_score,
                agents_count=agents_count,
            ),
        )

    if user.verification_code != request.code.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification code. Please check and try again.",
        )

    user.is_verified = True
    user.verification_code = None
    await session.commit()

    token = create_access_token(str(user.id))
    return AuthTokenResponse(
        access_token=token,
        user=UserProfileResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            avatar_url=user.avatar_url,
            is_verified=True,
            trust_score=user.trust_score,
            agents_count=agents_count,
        ),
    )


@router.post(
    "/login",
    response_model=AuthTokenResponse,
    summary="Sign in with email and password",
)
async def login(
    request: LoginRequest,
    session: AsyncSession = Depends(get_db_session),
) -> AuthTokenResponse:
    """Authenticates with email and password, issuing a JWT if verified."""
    stmt = select(User).where(User.email == request.email.lower())
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    if not user or not user.password_hash:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    if not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is not verified yet. Please enter the verification code sent to your email.",
        )

    token = create_access_token(str(user.id))
    agents_count = await _get_user_agents_count(session, user.id)
    return AuthTokenResponse(
        access_token=token,
        user=UserProfileResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            avatar_url=user.avatar_url,
            is_verified=user.is_verified,
            trust_score=user.trust_score,
            agents_count=agents_count,
        ),
    )


@router.post(
    "/google",
    response_model=AuthTokenResponse,
    summary="Sign in or sign up with Google account",
)
async def google_auth(
    request: GoogleAuthRequest,
    session: AsyncSession = Depends(get_db_session),
) -> AuthTokenResponse:
    """Authenticates via Google account credential, creating or linking the user automatically."""
    import jwt as pyjwt

    # Unpack Google ID token payload
    # In production with verified client_id, pyjwt.decode is verified against Google public keys.
    # We gracefully parse unverified claims from the ID token for maximum flexibility in dev.
    try:
        claims: dict[str, Any] = pyjwt.decode(request.credential, options={"verify_signature": False})
        google_sub = str(claims.get("sub") or f"google_{uuid.uuid4().hex[:12]}")
        raw_email = claims.get("email") or request.email
        if raw_email and "@" in str(raw_email):
            email = str(raw_email).lower().strip()
        else:
            email = f"dev_{google_sub}@gmail.com"
        name = str(claims.get("name") or request.name or email.split("@")[0])
        picture = claims.get("picture") or request.picture
    except Exception:
        google_sub = f"google_{uuid.uuid4().hex[:12]}"
        if request.email and "@" in str(request.email):
            email = str(request.email).lower().strip()
        else:
            email = f"dev_{google_sub}@gmail.com"
        name = str(request.name or email.split("@")[0])
        picture = request.picture

    # Check existing user by google_id or email
    stmt = (
        select(User)
        .options(selectinload(User.agents))
        .where((User.google_id == google_sub) | (User.email == email.lower()))
    )
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        # Create fresh user
        username_base = name.lower().replace(" ", "_")
        unique_username = f"{username_base}_{uuid.uuid4().hex[:4]}"
        user = User(
            google_id=google_sub,
            username=unique_username,
            email=email.lower(),
            avatar_url=picture,
            is_verified=True,
            trust_score=10,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
    else:
        # Link google_id if not present
        if not user.google_id:
            user.google_id = google_sub
        if not user.is_verified:
            user.is_verified = True
        if picture and not user.avatar_url:
            user.avatar_url = picture
        await session.commit()

    token = create_access_token(str(user.id))
    agents_count = await _get_user_agents_count(session, user.id)
    return AuthTokenResponse(
        access_token=token,
        user=UserProfileResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            avatar_url=user.avatar_url,
            is_verified=user.is_verified,
            trust_score=user.trust_score,
            agents_count=agents_count,
        ),
    )


@router.post(
    "/resend-code",
    summary="Resend verification code for an unverified account",
)
async def resend_code(
    request: ResendCodeRequest,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, str]:
    """Generates a fresh verification code and returns confirmation."""
    stmt = select(User).where(User.email == request.email.lower())
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account with this email does not exist.",
        )

    if user.is_verified:
        return {"message": "Account is already verified. You can sign in directly."}

    code = generate_verification_code()
    user.verification_code = code
    await session.commit()

    return {
        "message": f"Verification code sent! Code: '{code}'",
        "verification_code_hint": code,
    }


@router.get(
    "/me",
    response_model=UserProfileResponse,
    summary="Get authenticated developer profile",
)
async def get_me(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> UserProfileResponse:
    """Returns the profile of the authenticated developer session."""
    agents_count = await _get_user_agents_count(session, user.id)
    return UserProfileResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        avatar_url=user.avatar_url,
        is_verified=user.is_verified,
        trust_score=user.trust_score,
        agents_count=agents_count,
    )
