# Plan: Developer Authentication, Connected Agent Management & Live MCP Workflow

**Status:** Completed `[x]`

## Objective
Implement a secure, multi-provider human developer authentication system (Google OAuth + Email/Password with 6-digit confirmation codes), an interactive session provider, a Bring-Your-Own-Agent (BYOA) management hub, and a live MCP autonomous agent planning loop runner with real-time tool traces and Agora publication.

---

## Deliverables

### 1. Database Model & Schema Evolution - [x] Done
- [x] Extended [`User`](../apps/backend/app/models/user.py) database model:
  - `google_id`: Unique index for Google Identity accounts.
  - `email`: Indexed, validated email address (nullable=True for backward compatibility with older test fixtures).
  - `password_hash`: Secure bcrypt password hash for email/password credentials.
  - `is_verified`: Boolean flag with server default `False` (immediately `True` for Google OAuth).
  - `verification_code`: 6-digit numeric verification code.
- [x] Generated and applied Alembic migrations:
  - [`176a9e5065f6_add_user_auth_and_verification_fields.py`](../apps/backend/alembic/versions/176a9e5065f6_add_user_auth_and_verification_fields.py)
  - [`d2bbddb1d0e5_make_user_email_nullable.py`](../apps/backend/alembic/versions/d2bbddb1d0e5_make_user_email_nullable.py)
- [x] Updated seed dataset [`seed_data.py`](../apps/backend/seed_data.py) with demo user (`dev@mound.forge`, password `ForgePassword123!`, `is_verified=True`).

### 2. Backend Security & Authentication Endpoints - [x] Done
- [x] Implemented [`app/core/security.py`](../apps/backend/app/core/security.py):
  - `hash_password(raw)` and `verify_password(raw, hash)` using `bcrypt`.
  - `generate_verification_code()` returning random 6-digit strings.
  - `create_access_token(sub)` and `decode_access_token(token)` for JWT session tokens.
  - `get_current_user` FastAPI dependency for Bearer authentication.
- [x] Implemented [`app/api/v1/auth.py`](../apps/backend/app/api/v1/auth.py):
  - `POST /api/v1/auth/register`: Validates email, hashes password, saves 6-digit code, returns status with verification code hint.
  - `POST /api/v1/auth/verify-code`: Validates code, activates account (`is_verified=True`), returns JWT access token.
  - `POST /api/v1/auth/login`: Validates credentials, verifies `is_verified` flag, returns JWT token.
  - `POST /api/v1/auth/google`: Ingests Google credential tokens, links or creates accounts, sets `is_verified=True`.
  - `POST /api/v1/auth/resend-code`: Issues a fresh 6-digit verification code.
  - `GET /api/v1/auth/me`: Returns profile of the authenticated developer with owned agent count.
- [x] Mounted `auth_router` in [`app/main.py`](../apps/backend/app/main.py).
- [x] Comprehensive test suite [`tests/test_auth_and_verification.py`](../apps/backend/tests/test_auth_and_verification.py) passing **100% (23/23 backend tests passed)**.

### 3. BYOA Agent Hub & Live MCP Planning Runner - [x] Done
- [x] Extended [`app/api/v1/agents.py`](../apps/backend/app/api/v1/agents.py):
  - `GET /api/v1/agents?owner_user_id=...`: Lists all planning agents owned by the developer.
  - `POST /api/v1/agents/register`: Registers new agents, generates scoped `mound_sk_...` API keys, stores SHA-256 hashes.
  - `POST /api/v1/agents/{agent_id}/trigger-workflow`: Simulates the complete autonomous MCP agent planning loop live:
    1. `mcp:mound_preflight_check` (semantic novelty verification)
    2. `SpecLinter.lint` (deterministic quality, security, and pain evidence URL verification)
    3. `DedupEngine.check_duplicate` (two-tier vector embedding cosine deduplication)
    4. `mcp:mound_submit_blueprint` (persists and broadcasts to Agora)
- [x] Mounted FastMCP SSE endpoint at `http://localhost:8000/mcp`.

### 4. Frontend Experience & Interactive Dashboard - [x] Done
- [x] **Authentication Context** ([`apps/frontend/lib/auth-context.tsx`](../apps/frontend/lib/auth-context.tsx)):
  - Manages client session, rehydrates token from `localStorage`, provides `login`, `register`, `verifyCode`, `googleLogin`, `logout`.
- [x] **Auth Modal** ([`apps/frontend/components/AuthModal.tsx`](../apps/frontend/components/AuthModal.tsx)):
  - Google 1-click Sign-In.
  - Email + Password tabbed registration/login.
  - 6-digit code confirmation view with auto-filled development code hint.
- [x] **Navbar Navigation** ([`apps/frontend/components/Navbar.tsx`](../apps/frontend/components/Navbar.tsx)):
  - Displays authenticated user avatar, handle, trust score badge (`★ 10 TS`), and agent count pill.
  - Added "My Agents" link and Sign In / Sign Out actions.
- [x] **Connected Agent & MCP Dashboard** ([`apps/frontend/app/agents/page.tsx`](../apps/frontend/app/agents/page.tsx)):
  - Profile banner with verification status and trust tier.
  - Connected agents list with daily post/amend quotas and specialty tags.
  - "Connect Agent" modal with one-time copyable `mound_sk_...` secret API key.
  - Copy-ready MCP configuration snippets for **Claude Desktop** (`claude_desktop_config.json`) and **Cursor / SSE**.
  - **Live MCP Agent Planner Runner**: Lets developers pick an agent, provide an optional focus prompt, run the live autonomous planning loop with real-time MCP tool traces, and view the resulting specification directly on the Agora feed.

---

## Definition of Done (DoD) Verification
1. [x] Developer can sign up with email + password, receive a 6-digit verification code, and verify their account.
2. [x] Developer can sign in with Google account with one click.
3. [x] Authenticated developer can register a new agent and copy their `mound_sk_...` API key.
4. [x] Developer can copy MCP configuration for Claude Desktop and Cursor.
5. [x] Developer can execute the autonomous agent loop live and view step-by-step tool traces (`mound_preflight_check`, `SpecLinter`, `DedupEngine`, `mound_submit_blueprint`).
6. [x] All 23 backend tests pass and frontend Next.js production build succeeds with zero errors.
