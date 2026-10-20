"""Pydantic schemas for authentication and developer account management."""

import uuid

from pydantic import BaseModel, EmailStr, Field


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
