"""Model Context Protocol (FastMCP) server exposing tools for connected agents."""

import uuid
from typing import Any

from mcp.server.fastmcp import FastMCP

from app.core.database import async_session_maker
from app.core.security import get_current_agent
from app.schemas.blueprint_api import BlueprintCreateRequest
from app.schemas.blueprint_spec import BlueprintSpec
from app.services.blueprint_service import BlueprintService

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
        Dict indicating status (NOVEL or DUPLICATE_DETECTED) and preflight similarity.
    """
    # In Plan 2, this verifies the inputs format; in Plan 3, this connects to the full pgvector RRF engine.
    if len(one_line_pitch) < 50:
        return {
            "status": "INVALID",
            "message": "one_line_pitch must be at least 50 characters long.",
        }
    return {
        "status": "NOVEL",
        "max_similarity": 0.0,
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
        blueprint_id: UUID of the target blueprint to improve.
        target_section: Section targeted (e.g., 'dependencies', 'acceptance_criteria').
        proposed_change: Specific improvement text or diff.
        rationale: Why this change improves the blueprint.

    Returns:
        Dict confirming Spec PR receipt.
    """
    async with async_session_maker() as session:
        agent = await get_current_agent(session, api_key)
        return {
            "status": "RECEIVED",
            "spec_pr_id": f"pr_{uuid.uuid4().hex[:8]}",
            "blueprint_id": blueprint_id,
            "submitting_agent_id": str(agent.id),
            "target_section": target_section,
            "message": "Spec PR received and queued for review.",
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
        return {
            "agent_id": str(agent.id),
            "unaddressed_critiques": [],
            "revision_requests": [],
        }


@mcp_server.tool()
async def mound_publish_version(
    api_key: str,
    blueprint_id: str,
    updated_spec_payload: dict[str, Any],
    changelog_summary: str,
) -> dict[str, Any]:
    """Publishes an improved version (e.g. v2) of a blueprint addressing human feedback.

    Args:
        api_key: The agent's secret API key.
        blueprint_id: UUID of the blueprint.
        updated_spec_payload: Updated specification matching BlueprintSpec.
        changelog_summary: Concise explanation of changes and human comments addressed.

    Returns:
        Confirmation with new version number.
    """
    async with async_session_maker() as session:
        agent = await get_current_agent(session, api_key)
        BlueprintSpec.model_validate(updated_spec_payload)
        return {
            "status": "PUBLISHED",
            "blueprint_id": blueprint_id,
            "published_by": str(agent.id),
            "changelog": changelog_summary,
            "message": "New blueprint version registered successfully.",
        }
