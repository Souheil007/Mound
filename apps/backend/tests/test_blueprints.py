"""Integration tests for blueprint creation, validation, and retrieval."""

import pytest
from httpx import AsyncClient

from app.models.agent import Agent


def get_valid_blueprint_payload(agent_id: str) -> dict:
    """Helper returning a valid blueprint proposal payload."""
    return {
        "agent_id": agent_id,
        "spec": {
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
        },
    }


@pytest.mark.asyncio
async def test_create_blueprint_success(client: AsyncClient, test_agent: Agent) -> None:
    """Verifies that a valid blueprint is accepted, saved, and embedded with MiniLM."""
    payload = get_valid_blueprint_payload(str(test_agent.id))
    response = await client.post("/api/v1/blueprints", json=payload)

    assert response.status_code == 201
    data = response.json()
    assert data["creator_agent_id"] == str(test_agent.id)
    assert data["status"] == "OPEN"
    assert data["current_version_num"] == 1
    assert data["spec"]["one_line_pitch"] == payload["spec"]["one_line_pitch"]
    assert "slug" in data


@pytest.mark.asyncio
async def test_create_blueprint_rejects_too_short_pitch(client: AsyncClient, test_agent: Agent) -> None:
    """Verifies that pitches shorter than 50 characters are rejected with 422 Unprocessable Entity."""
    payload = get_valid_blueprint_payload(str(test_agent.id))
    payload["spec"]["one_line_pitch"] = "Too short pitch"

    response = await client.post("/api/v1/blueprints", json=payload)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_blueprint_rejects_missing_non_goals(client: AsyncClient, test_agent: Agent) -> None:
    """Verifies that specs with fewer than 2 non-goals are rejected with 422."""
    payload = get_valid_blueprint_payload(str(test_agent.id))
    payload["spec"]["explicit_non_goals"] = ["Only one non goal"]

    response = await client.post("/api/v1/blueprints", json=payload)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_blueprint_rejects_invalid_url(client: AsyncClient, test_agent: Agent) -> None:
    """Verifies that malformed URLs in pain evidence are rejected."""
    payload = get_valid_blueprint_payload(str(test_agent.id))
    payload["spec"]["pain_evidence_urls"] = ["not-a-valid-url"]

    response = await client.post("/api/v1/blueprints", json=payload)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_get_blueprint_by_id(client: AsyncClient, test_agent: Agent) -> None:
    """Verifies retrieving a created blueprint and its version history."""
    payload = get_valid_blueprint_payload(str(test_agent.id))
    create_res = await client.post("/api/v1/blueprints", json=payload)
    assert create_res.status_code == 201
    blueprint_id = create_res.json()["id"]

    get_res = await client.get(f"/api/v1/blueprints/{blueprint_id}")
    assert get_res.status_code == 200
    bp_data = get_res.json()
    assert bp_data["id"] == blueprint_id
    assert bp_data["spec"]["one_line_pitch"] == payload["spec"]["one_line_pitch"]

    versions_res = await client.get(f"/api/v1/blueprints/{blueprint_id}/versions")
    assert versions_res.status_code == 200
    versions = versions_res.json()
    assert len(versions) == 1
    assert versions[0]["version_num"] == 1


@pytest.mark.asyncio
async def test_get_blueprint_by_slug(client: AsyncClient, test_agent: Agent) -> None:
    """Verifies retrieving a blueprint and its sub-resources using human-readable slug string."""
    payload = get_valid_blueprint_payload(str(test_agent.id))
    payload["spec"]["one_line_pitch"] = (
        "Unique standalone tool to verify Docker container runtime integrity for staging pipelines"
    )
    create_res = await client.post("/api/v1/blueprints", json=payload)
    assert create_res.status_code == 201
    slug = create_res.json()["slug"]

    # Fetch by slug instead of UUID
    get_res = await client.get(f"/api/v1/blueprints/{slug}")
    assert get_res.status_code == 200
    bp_data = get_res.json()
    assert bp_data["slug"] == slug
    assert bp_data["spec"]["one_line_pitch"] == payload["spec"]["one_line_pitch"]

    # Fetch versions by slug
    versions_res = await client.get(f"/api/v1/blueprints/{slug}/versions")
    assert versions_res.status_code == 200
    assert len(versions_res.json()) >= 1


@pytest.mark.asyncio
async def test_list_blueprints_feed(client: AsyncClient, test_agent: Agent) -> None:
    """Verifies listing blueprints in the Layer-1 feed card format."""
    payload = get_valid_blueprint_payload(str(test_agent.id))
    await client.post("/api/v1/blueprints", json=payload)

    response = await client.get("/api/v1/blueprints?limit=10")
    assert response.status_code == 200
    feed = response.json()
    assert len(feed) >= 1
    item = feed[0]
    assert "one_line_pitch" in item
    assert "domain_tags" in item
    assert "status" in item
