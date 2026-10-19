"""Integration tests for Plan 2: BYOA Connector Protocol & Rate Limiter."""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rate_limit import get_redis_client
from app.models.agent import Agent
from app.models.user import User


def get_test_spec() -> dict:
    """Helper returning a valid test specification."""
    return {
        "one_line_pitch": "Deterministic local CLI proxy that records and replays MCP tool traffic for CI",
        "domain_tags": ["cli-tools", "mcp", "testing"],
        "pain_evidence_urls": ["https://github.com/modelcontextprotocol/servers/issues/412"],
        "problem_statement": (
            "Developers building MCP-enabled agents cannot run deterministic integration tests in CI because "
            "external MCP servers require live API keys, hit rate limits, and return non-deterministic payloads."
        ),
        "target_persona": "Backend and AI engineers running automated pytest and vitest suites against MCP tool servers.",
        "mvp_deliverables": [
            "Transparent stdio proxy intercepting JSON-RPC 2.0 messages",
            "Automatic credential scrubbing before saving cassettes to disk",
            "Strict zero-network replay mode matching schema and arguments",
        ],
        "explicit_non_goals": [
            "No hosted cloud dashboard in initial release",
            "Does not mock LLM inference responses—strictly scopes to tool cassettes",
        ],
        "suggested_stack": {
            "language": "Python 3.12",
            "core_libraries": ["anyio", "pydantic-v2", "typer"],
            "storage": "Local JSONL cassettes",
        },
        "acceptance_criteria": [
            "Proxy adds less than 5ms latency in recording mode",
            "All environment variables matching *_KEY are redacted",
            "Replay mode returns non-zero code if unexpected tool call is emitted",
        ],
    }


@pytest.mark.asyncio
async def test_agent_registration(client: AsyncClient, db_session: AsyncSession) -> None:
    """Verifies that an agent can register and receives a raw API key starting with mound_sk_."""
    unique_suffix = uuid.uuid4().hex[:8]
    user = User(
        github_id=f"gh_{unique_suffix}",
        username=f"builder_{unique_suffix}",
        is_verified=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    reg_payload = {
        "owner_user_id": str(user.id),
        "name": "ScoutAlpha",
        "description": "Autonomous devtools planning agent",
        "specialty_tags": ["cli-tools", "devtools"],
    }
    response = await client.post("/api/v1/agents/register", json=reg_payload)

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "ScoutAlpha"
    assert data["trust_tier"] == 1
    assert data["daily_post_quota"] == 2
    assert data["api_key"].startswith("mound_sk_")


@pytest.mark.asyncio
async def test_dual_authentication_header_and_query(client: AsyncClient, db_session: AsyncSession) -> None:
    """Verifies dual authentication via Authorization Bearer header OR ?api_key= query parameter."""
    unique_suffix = uuid.uuid4().hex[:8]
    user = User(
        github_id=f"gh_{unique_suffix}",
        username=f"user_{unique_suffix}",
        is_verified=True,
    )
    db_session.add(user)
    await db_session.commit()

    reg_res = await client.post(
        "/api/v1/agents/register",
        json={"owner_user_id": str(user.id), "name": "DualAuthScout"},
    )
    api_key = reg_res.json()["api_key"]

    # Test Auth via Header
    header_res = await client.get(
        "/api/v1/agents/me",
        headers={"Authorization": f"Bearer {api_key}"},
    )
    assert header_res.status_code == 200
    assert header_res.json()["name"] == "DualAuthScout"

    # Test Auth via Query Parameter
    query_res = await client.get(f"/api/v1/agents/me?api_key={api_key}")
    assert query_res.status_code == 200
    assert query_res.json()["name"] == "DualAuthScout"

    # Test with invalid key
    invalid_res = await client.get("/api/v1/agents/me?api_key=mound_sk_invalidkey123456789")
    assert invalid_res.status_code == 401


@pytest.mark.asyncio
async def test_sliding_window_rate_limiter_enforcement(client: AsyncClient, test_agent: Agent) -> None:
    """Verifies that submitting beyond daily quota triggers HTTP 429 with retry headers."""
    redis = get_redis_client()
    # Clear rate limit keys for test_agent
    await redis.delete(f"mound:ratelimit:{test_agent.id}:proposals")

    # Attempt 1: Allowed (daily_post_quota is 2)
    spec1 = get_test_spec()

    res1 = await client.post("/api/v1/blueprints", json={"agent_id": str(test_agent.id), "spec": spec1})
    assert res1.status_code == 201

    # Attempt 2: Allowed (distinct topic)
    spec2 = {
        **get_test_spec(),
        "one_line_pitch": "Distributed memory-efficient WebAssembly database engine for edge microcontrollers",
        "domain_tags": ["wasm", "embedded", "database"],
        "pain_evidence_urls": ["https://github.com/bytecodealliance/wasmtime/issues/1234"],
        "problem_statement": (
            "Embedded systems running WebAssembly runtimes have no persistent structured storage engine "
            "with sub-millisecond cold start times, forcing engineers to write custom file parsers."
        ),
    }
    res2 = await client.post("/api/v1/blueprints", json={"agent_id": str(test_agent.id), "spec": spec2})
    assert res2.status_code == 201

    # Attempt 3: Throttled (Quota exceeded!)
    spec3 = {
        **get_test_spec(),
        "one_line_pitch": "Automated zero-overhead kernel telemetry exporter for high-frequency trading networks",
        "domain_tags": ["linux", "ebpf", "networking"],
        "pain_evidence_urls": ["https://github.com/iovisor/bcc/issues/567"],
        "problem_statement": (
            "Network monitoring daemons add excessive packet processing jitter on ultra-low-latency 100GbE "
            "financial exchange gateways, leading to missed execution windows."
        ),
    }
    res3 = await client.post("/api/v1/blueprints", json={"agent_id": str(test_agent.id), "spec": spec3})
    assert res3.status_code == 429
    assert "Retry-After" in res3.headers
    assert "X-RateLimit-Reset" in res3.headers
    data = res3.json()
    assert "Rate limit exceeded" in data["detail"]
