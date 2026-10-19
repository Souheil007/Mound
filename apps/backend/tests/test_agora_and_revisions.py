"""Tests for Human Agora interactions and agent revision loops (Plan 4)."""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent import Agent
from app.models.blueprint import Blueprint, BlueprintStatus, CritiqueCategory
from app.models.user import User


def valid_spec_payload(
    pitch: str = "Automated PostgreSQL index tuning daemon for high-traffic multi-tenant clusters",
) -> dict:
    """Helper returning a fully compliant BlueprintSpec payload."""
    return {
        "one_line_pitch": pitch,
        "problem_statement": (
            "Slow queries degrade database throughput in high-velocity multi-tenant environments "
            "because existing index tuning tools require manual intervention and reboot cycles."
        ),
        "pain_evidence_urls": [
            "https://github.com/postgres/postgres/issues/404",
        ],
        "proposed_solution": (
            "An autonomous background worker that continuously samples pg_stat_statements, simulates "
            "hypothetical index benefits via hypopg, and applies non-blocking concurrent indexes."
        ),
        "domain_tags": ["database", "postgresql", "automation"],
        "mvp_deliverables": [
            "Continuous pg_stat_statements telemetry ingestion worker",
            "HypoPG hypothetical index simulator engine",
            "Automated zero-downtime CREATE INDEX CONCURRENTLY scheduler",
        ],
        "acceptance_criteria": [
            "Must achieve 95% test coverage across telemetry ingestion",
            "Simulated index speedups must be accurate within 10% of explain analyze",
            "Zero locking overhead on concurrent active write workloads",
        ],
        "explicit_non_goals": [
            "Support for proprietary non-PostgreSQL databases",
            "Automated table re-indexing on unmanaged replica clusters",
        ],
        "target_persona": "Database administrators and backend engineers managing high-throughput PostgreSQL databases.",
        "suggested_stack": {
            "language": "Python 3.12",
            "core_libraries": ["asyncpg", "sqlalchemy", "hypopg"],
            "storage": "PostgreSQL 16",
        },
    }


@pytest.mark.asyncio
async def test_blueprint_voting_and_qualification(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """Test human voting toggles and auto-graduation to QUALIFIED status upon 10 upvotes."""
    # 1. Create a user and an agent
    user = User(github_id="gh_voter_1", username="voter1")
    agent = Agent(
        owner=user,
        name="PlannerAlpha",
        api_key_hash="test_hash",
        daily_post_quota=10,
    )
    db_session.add_all([user, agent])
    await db_session.commit()
    await db_session.refresh(user)
    await db_session.refresh(agent)

    # 2. Propose blueprint
    prop_res = await client.post(
        "/api/v1/blueprints",
        json={"agent_id": str(agent.id), "spec": valid_spec_payload()},
    )
    assert prop_res.status_code == 201
    bp_id = prop_res.json()["id"]

    # 3. Vote blueprint
    vote_res = await client.post(
        f"/api/v1/blueprints/{bp_id}/vote",
        json={"user_id": str(user.id)},
    )
    assert vote_res.status_code == 200
    assert vote_res.json()["voted"] is True
    assert vote_res.json()["upvotes_count"] == 1

    # 4. Toggle vote off
    unvote_res = await client.post(
        f"/api/v1/blueprints/{bp_id}/vote",
        json={"user_id": str(user.id)},
    )
    assert unvote_res.status_code == 200
    assert unvote_res.json()["voted"] is False
    assert unvote_res.json()["upvotes_count"] == 0

    # 5. Simulate 10 upvotes to graduate to QUALIFIED
    for i in range(10):
        u = User(github_id=f"gh_voter_{i+2}", username=f"voter_{i+2}")
        db_session.add(u)
        await db_session.commit()
        await db_session.refresh(u)
        await client.post(
            f"/api/v1/blueprints/{bp_id}/vote",
            json={"user_id": str(u.id)},
        )

    # Verify status is now QUALIFIED
    bp_detail = await client.get(f"/api/v1/blueprints/{bp_id}")
    assert bp_detail.status_code == 200
    assert bp_detail.json()["upvotes_count"] == 10
    assert bp_detail.json()["status"] == BlueprintStatus.QUALIFIED.value


@pytest.mark.asyncio
async def test_critiques_revision_trigger_and_notifications(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """Test comments trigger revision requests and appear in agent notifications."""
    # 1. Setup user and agent with real raw api key
    user = User(github_id="gh_architect_1", username="architect1")
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    reg_res = await client.post(
        "/api/v1/agents/register",
        json={"owner_user_id": str(user.id), "name": "IndexerBot"},
    )
    assert reg_res.status_code == 201
    agent_id = reg_res.json()["agent_id"]
    api_key = reg_res.json()["api_key"]

    # 2. Propose blueprint
    prop_res = await client.post(
        "/api/v1/blueprints",
        json={
            "agent_id": agent_id,
            "spec": valid_spec_payload(
                "High-throughput PostgreSQL index tuning agent with automated rollback"
            ),
        },
    )
    assert prop_res.status_code == 201
    bp_id = prop_res.json()["id"]

    # 3. Post 2 comments (below 3 comment threshold)
    c1_res = await client.post(
        f"/api/v1/blueprints/{bp_id}/comments",
        json={
            "user_id": str(user.id),
            "category": CritiqueCategory.ARCHITECTURE_FLAW.value,
            "content": "HypoPG requires superuser or pg_read_all_stats permissions in RDS.",
        },
    )
    assert c1_res.status_code == 201
    c1_id = c1_res.json()["id"]

    c2_res = await client.post(
        f"/api/v1/blueprints/{bp_id}/comments",
        json={
            "user_id": str(user.id),
            "category": CritiqueCategory.MISSING_REQUIREMENT.value,
            "content": "Need rollback mechanism if concurrent index creation exceeds memory limit.",
        },
    )
    assert c2_res.status_code == 201

    # Check blueprint does not have revision_requested_at yet
    bp_res = await client.get(f"/api/v1/blueprints/{bp_id}")
    assert bp_res.json()["revision_requested_at"] is None

    # 4. Third comment triggers revision request
    c3_res = await client.post(
        f"/api/v1/blueprints/{bp_id}/comments",
        json={
            "user_id": str(user.id),
            "category": CritiqueCategory.SIMPLER_ALTERNATIVE.value,
            "content": "Consider using pg_stat_user_indexes instead of brute sampling statements.",
        },
    )
    assert c3_res.status_code == 201

    # Check blueprint now has revision_requested_at set
    bp_res = await client.get(f"/api/v1/blueprints/{bp_id}")
    assert bp_res.json()["revision_requested_at"] is not None

    # 5. Agent polls notifications
    notif_res = await client.get(
        "/api/v1/agents/me/notifications",
        headers={"Authorization": f"Bearer {api_key}"},
    )
    assert notif_res.status_code == 200
    data = notif_res.json()
    assert data["total_unaddressed"] == 3
    assert len(data["unaddressed_critiques"]) == 3

    # 6. Creator agent addresses feedback and publishes v2
    revised_spec = valid_spec_payload(
        "High-throughput PostgreSQL index tuning agent with automated rollback v2"
    )
    revised_spec["mvp_deliverables"].append("Automatic index rollback on memory pressure")

    v2_res = await client.post(
        f"/api/v1/blueprints/{bp_id}/versions",
        json={
            "author_agent_id": agent_id,
            "expected_version_num": 1,
            "spec": revised_spec,
            "changelog_summary": "v1.1: Addressed RDS HypoPG permission requirements and memory limit safeguards.",
            "addressed_comment_ids": [c1_id],
        },
    )
    assert v2_res.status_code == 201
    assert v2_res.json()["current_version_num"] == 2
    assert v2_res.json()["revision_requested_at"] is None

    # Verify c1 is marked addressed
    comments_res = await client.get(f"/api/v1/blueprints/{bp_id}/comments")
    comments = comments_res.json()
    c1_item = next(c for c in comments if c["id"] == c1_id)
    assert c1_item["is_addressed"] is True


@pytest.mark.asyncio
async def test_optimistic_locking_conflict(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """Test that concurrent version publication with mismatched version number returns 409 Conflict."""
    user = User(github_id="gh_lock_user", username="lockuser")
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    reg_res = await client.post(
        "/api/v1/agents/register",
        json={"owner_user_id": str(user.id), "name": "ConcurrencyAgent"},
    )
    agent_id = reg_res.json()["agent_id"]

    prop_res = await client.post(
        "/api/v1/blueprints",
        json={
            "agent_id": agent_id,
            "spec": valid_spec_payload(
                "Concurrency test specification for pessimistic lock mitigation in engines"
            ),
        },
    )
    bp_id = prop_res.json()["id"]

    # Attempt to bump with wrong expected version (e.g. 5 instead of 1)
    conflict_res = await client.post(
        f"/api/v1/blueprints/{bp_id}/versions",
        json={
            "author_agent_id": agent_id,
            "expected_version_num": 5,
            "spec": valid_spec_payload(
                "Concurrency specification bump resolving deadlock conflicts across workers"
            ),
            "changelog_summary": "Out of sync update",
        },
    )
    assert conflict_res.status_code == 409
    assert "Optimistic lock conflict" in conflict_res.json()["detail"]


@pytest.mark.asyncio
async def test_48_hour_community_revision_fallback(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """Test that if creator agent is unresponsive past 48h, community agents can publish revision and gain co-authorship."""
    # 1. Setup creator user & agent
    creator_user = User(github_id="gh_abandon_user", username="creator_dev")
    db_session.add(creator_user)
    await db_session.commit()
    await db_session.refresh(creator_user)

    reg_creator = await client.post(
        "/api/v1/agents/register",
        json={"owner_user_id": str(creator_user.id), "name": "OfflineCreatorAgent"},
    )
    creator_agent_id = reg_creator.json()["agent_id"]

    # Setup community agent
    comm_user = User(github_id="gh_comm_user", username="community_dev")
    db_session.add(comm_user)
    await db_session.commit()
    await db_session.refresh(comm_user)

    reg_comm = await client.post(
        "/api/v1/agents/register",
        json={"owner_user_id": str(comm_user.id), "name": "CommunityFixerAgent"},
    )
    community_agent_id = reg_comm.json()["agent_id"]

    # 2. Creator posts proposal
    prop_res = await client.post(
        "/api/v1/blueprints",
        json={
            "agent_id": creator_agent_id,
            "spec": valid_spec_payload(
                "Stalled architectural proposal needing community intervention and revision"
            ),
        },
    )
    bp_id = prop_res.json()["id"]

    # 3. Simulate an immediate revision request by setting revision_requested_at to 1 hour ago
    stmt = select(Blueprint).where(Blueprint.id == uuid.UUID(bp_id))
    bp = (await db_session.execute(stmt)).scalar_one()
    bp.revision_requested_at = datetime.now(timezone.utc) - timedelta(hours=1)
    await db_session.commit()

    # Community agent attempts revision before 48 hours -> Should be 403 Forbidden!
    early_res = await client.post(
        f"/api/v1/blueprints/{bp_id}/versions",
        json={
            "author_agent_id": community_agent_id,
            "expected_version_num": 1,
            "spec": valid_spec_payload(
                "Premature community revision attempting unauthorized takeovers in windows"
            ),
            "changelog_summary": "Attempting early takeover.",
        },
    )
    assert early_res.status_code == 403
    assert "reserved for the creator agent during the 48-hour response window" in early_res.json()["detail"]

    # 4. Now simulate 49 hours elapsed since revision request
    bp.revision_requested_at = datetime.now(timezone.utc) - timedelta(hours=49)
    await db_session.commit()

    # Community agent now submits revision -> Should succeed!
    success_res = await client.post(
        f"/api/v1/blueprints/{bp_id}/versions",
        json={
            "author_agent_id": community_agent_id,
            "expected_version_num": 1,
            "spec": valid_spec_payload(
                "Community rescued architecture resolving unaddressed critiques in 48h loop"
            ),
            "changelog_summary": "Community v1.1 revision resolving unaddressed critiques after 48h timeout.",
        },
    )
    assert success_res.status_code == 201
    data = success_res.json()
    assert data["current_version_num"] == 2
    # Verify community agent earned co-authorship credit
    assert community_agent_id in [str(ca) for ca in data["co_author_agent_ids"]]
