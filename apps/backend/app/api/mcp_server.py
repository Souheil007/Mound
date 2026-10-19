"""Model Context Protocol (FastMCP) server exposing tools for connected agents."""

import uuid
from typing import Any

from mcp.server.fastmcp import FastMCP
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import async_session_maker
from app.core.security import get_current_agent
from app.models.blueprint import Blueprint
from app.schemas.blueprint_api import (
    AmendmentCreateRequest,
    BlueprintCreateRequest,
    VersionBumpRequest,
)
from app.schemas.blueprint_spec import BlueprintSpec
from app.services.blueprint_service import BlueprintService
from app.services.dedup_engine import DedupEngine
from app.services.embedding_engine import EmbeddingEngine
from app.services.spec_linter import SpecLinter

# Initialize the FastMCP instance
mcp_server = FastMCP(
    name="mound",
    instructions=(
        "Mound MCP server for autonomous planning agents to research, propose, and refine engineering blueprints."
    ),
)


@mcp_server.tool()
async def mound_preflight_check(
    one_line_pitch: str,
    problem_statement: str,
) -> dict[str, Any]:
    """Checks whether a proposed blueprint is unique or similar to existing blueprints.

    Args:
        one_line_pitch: Concise 50-140 character summary of the project.
        problem_statement: 100-600 character explanation of the broken workflow.

    Returns:
        Dict indicating status (NOVEL, DUPLICATE_DETECTED, or INVALID) and preflight similarity.
    """
    if len(one_line_pitch) < 50:
        return {
            "status": "INVALID",
            "message": "one_line_pitch must be at least 50 characters long.",
        }
    if len(one_line_pitch) > 140:
        return {
            "status": "INVALID",
            "message": "one_line_pitch cannot exceed 140 characters.",
        }
    if len(problem_statement) < 100:
        return {
            "status": "INVALID",
            "message": "problem_statement must be at least 100 characters long.",
        }
    if len(problem_statement) > 600:
        return {
            "status": "INVALID",
            "message": "problem_statement cannot exceed 600 characters.",
        }

    async with async_session_maker() as session:
        embed_input = f"{one_line_pitch}\n{problem_statement}"
        query_vector = EmbeddingEngine.embed_text(embed_input)

        stmt = (
            select(
                Blueprint,
                (1.0 - Blueprint.search_vector.cosine_distance(query_vector)).label("similarity"),
            )
            .options(selectinload(Blueprint.versions))
            .where(Blueprint.search_vector.isnot(None))
            .order_by(Blueprint.search_vector.cosine_distance(query_vector))
            .limit(1)
        )
        result = await session.execute(stmt)
        match = result.first()

        if match:
            bp, sim_val = match
            sim = round(float(sim_val), 4)
            if sim >= DedupEngine.SIMILARITY_THRESHOLD_BORDERLINE:
                latest_v = max(bp.versions, key=lambda v: v.version_num) if bp.versions else None
                title = latest_v.spec_payload.get("one_line_pitch", bp.slug) if latest_v else bp.slug
                return {
                    "status": "DUPLICATE_DETECTED",
                    "max_similarity": sim,
                    "existing_blueprint_id": str(bp.id),
                    "existing_blueprint_slug": bp.slug,
                    "existing_title": title,
                    "message": (
                        f"A very similar blueprint already exists with {sim * 100:.1f}% "
                        f"semantic similarity: '{title}'. Consider submitting an amendment via "
                        f"mound_submit_amendment instead."
                    ),
                }

        max_sim = round(float(match[1]), 4) if match else 0.0
        return {
            "status": "NOVEL",
            "max_similarity": max_sim,
            "preflight_token": f"pft_{uuid.uuid4().hex[:12]}",
            "message": "Proposal is novel. Proceed to mound_submit_blueprint.",
        }


@mcp_server.tool()
async def mound_submit_blueprint(
    api_key: str,
    spec_payload: dict[str, Any],
) -> dict[str, Any]:
    """Submits a strictly validated blueprint specification to Mound.

    Args:
        api_key: The agent's secret API key (starts with mound_sk_).
        spec_payload: Complete dictionary matching the BlueprintSpec schema.

    Returns:
        Dict containing created blueprint ID, slug, and status.
    """
    async with async_session_maker() as session:
        agent = await get_current_agent(session, api_key)
        validated_spec = BlueprintSpec.model_validate(spec_payload)

        # 1. Spec Linter check
        lint_res = await SpecLinter.lint(validated_spec)
        if not lint_res.passed:
            return {
                "status": "REJECTED_LINT",
                "errors": lint_res.errors,
                "message": "Blueprint specification failed quality/security linting.",
            }

        # 2. Two-Tier Dedup check
        dedup_res = await DedupEngine.check_duplicate(session, validated_spec)
        if dedup_res.is_duplicate:
            return {
                "status": "DUPLICATE_DETECTED",
                "similarity": dedup_res.similarity,
                "existing_blueprint_id": str(dedup_res.existing_blueprint_id),
                "existing_title": dedup_res.existing_title,
                "message": dedup_res.message,
            }

        request = BlueprintCreateRequest(agent_id=agent.id, spec=validated_spec)
        result = await BlueprintService.create_blueprint(session, request)
        return {
            "status": "SUCCESS",
            "blueprint_id": str(result.id),
            "slug": result.slug,
            "version": result.current_version_num,
            "message": "Blueprint proposal created successfully.",
        }


@mcp_server.tool()
async def mound_submit_spec_pr(
    api_key: str,
    blueprint_id: str,
    target_section: str,
    proposed_change: str,
    rationale: str,
) -> dict[str, Any]:
    """Submits a Spec PR (amendment) to improve an existing blueprint.

    Args:
        api_key: The agent's secret API key.
        blueprint_id: UUID or slug of the target blueprint to improve.
        target_section: Section targeted (e.g., 'dependencies', 'acceptance_criteria').
        proposed_change: Specific improvement text or diff.
        rationale: Why this change improves the blueprint.

    Returns:
        Dict confirming Spec PR receipt.
    """
    async with async_session_maker() as session:
        agent = await get_current_agent(session, api_key)
        req = AmendmentCreateRequest(
            agent_id=agent.id,
            target_section=target_section,
            proposed_change=proposed_change,
            rationale=rationale,
        )
        try:
            amendment = await BlueprintService.create_amendment(session, blueprint_id, req)
            return {
                "status": "RECEIVED",
                "amendment_id": str(amendment.id),
                "blueprint_id": str(amendment.blueprint_id),
                "submitting_agent_id": str(agent.id),
                "target_section": amendment.target_section,
                "message": "Spec PR / Amendment created and pending review.",
            }
        except ValueError as exc:
            return {
                "status": "ERROR",
                "message": str(exc),
            }


@mcp_server.tool()
async def mound_poll_feedback_notifications(
    api_key: str,
) -> dict[str, Any]:
    """Polls unaddressed human comments and revision requests for the agent's blueprints.

    Args:
        api_key: The agent's secret API key.

    Returns:
        List of unaddressed feedback notifications.
    """
    async with async_session_maker() as session:
        agent = await get_current_agent(session, api_key)
        notifications = await BlueprintService.get_agent_notifications(session, agent.id)
        return notifications.model_dump()


@mcp_server.tool()
async def mound_publish_version(
    api_key: str,
    blueprint_id: str,
    updated_spec_payload: dict[str, Any],
    changelog_summary: str,
    expected_version_num: int = 1,
    addressed_comment_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Publishes an improved version (e.g. v2) of a blueprint addressing human feedback.

    Args:
        api_key: The agent's secret API key.
        blueprint_id: UUID or slug of the blueprint.
        updated_spec_payload: Updated specification matching BlueprintSpec.
        changelog_summary: Concise explanation of changes and human comments addressed.
        expected_version_num: Optimistic locking version number.
        addressed_comment_ids: Optional list of comment UUID strings addressed.

    Returns:
        Confirmation with new version number.
    """
    async with async_session_maker() as session:
        agent = await get_current_agent(session, api_key)
        try:
            validated_spec = BlueprintSpec.model_validate(updated_spec_payload)
            comment_uuids = [uuid.UUID(c) for c in (addressed_comment_ids or [])]
            req = VersionBumpRequest(
                author_agent_id=agent.id,
                expected_version_num=expected_version_num,
                spec=validated_spec,
                changelog_summary=changelog_summary,
                addressed_comment_ids=comment_uuids,
            )
            result = await BlueprintService.bump_version(session, blueprint_id, req)
            return {
                "status": "PUBLISHED",
                "blueprint_id": str(result.id),
                "version": result.current_version_num,
                "slug": result.slug,
                "published_by": str(agent.id),
                "changelog": changelog_summary,
                "message": "New blueprint version registered successfully.",
            }
        except (ValueError, PermissionError) as exc:
            return {
                "status": "ERROR",
                "message": str(exc),
            }
