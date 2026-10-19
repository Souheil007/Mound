"""Integration tests for Developer Authentication (Email/Password + Verification, Google Auth, Me)."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_auth_registration_and_verification_flow(client: AsyncClient) -> None:
    """Verifies that an unverified developer registers, receives a 6-digit code, and verifies."""
    register_payload = {
        "email": "alice_architect@mound.forge",
        "password": "SecurePassword123!",
        "username": "alice_architect",
    }
    # 1. Register unverified account
    reg_res = await client.post("/api/v1/auth/register", json=register_payload)
    assert reg_res.status_code == 201
    reg_data = reg_res.json()
    assert reg_data["is_verified"] is False
    assert len(reg_data["verification_code_hint"]) == 6
    code = reg_data["verification_code_hint"]

    # 2. Login fails before verification
    login_fail_res = await client.post(
        "/api/v1/auth/login",
        json={"email": "alice_architect@mound.forge", "password": "SecurePassword123!"},
    )
    assert login_fail_res.status_code == 403
    assert "not verified" in login_fail_res.json()["detail"].lower()

    # 3. Verify with code
    verify_res = await client.post(
        "/api/v1/auth/verify-code",
        json={"email": "alice_architect@mound.forge", "code": code},
    )
    assert verify_res.status_code == 200
    verify_data = verify_res.json()
    assert "access_token" in verify_data
    assert verify_data["user"]["is_verified"] is True
    assert verify_data["user"]["email"] == "alice_architect@mound.forge"

    # 4. Login succeeds after verification
    login_ok_res = await client.post(
        "/api/v1/auth/login",
        json={"email": "alice_architect@mound.forge", "password": "SecurePassword123!"},
    )
    assert login_ok_res.status_code == 200
    token = login_ok_res.json()["access_token"]

    # 5. Get current profile with Bearer JWT
    me_res = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_res.status_code == 200
    assert me_res.json()["username"] == "alice_architect"


@pytest.mark.asyncio
async def test_auth_google_flow(client: AsyncClient) -> None:
    """Verifies seamless sign-in or auto-registration using Google identity credential."""
    import jwt
    # Simulate a Google JWT credential
    simulated_google_token = jwt.encode(
        {"sub": "google_109283746152", "email": "bob_google@gmail.com", "name": "Bob Google"},
        "simulated_secret",
        algorithm="HS256",
    )

    google_res = await client.post(
        "/api/v1/auth/google",
        json={"credential": simulated_google_token},
    )
    assert google_res.status_code == 200
    data = google_res.json()
    assert "access_token" in data
    assert data["user"]["is_verified"] is True
    assert data["user"]["email"] == "bob_google@gmail.com"

    # Profile check with issued token
    token = data["access_token"]
    me_res = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_res.status_code == 200
    assert me_res.json()["email"] == "bob_google@gmail.com"
