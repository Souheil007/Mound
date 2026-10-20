"""Pydantic schemas for agent management, registration, and scout telemetry."""

import uuid
from typing import Any

from pydantic import BaseModel, Field


class AgentRegisterRequest(BaseModel):
    """Payload to register an external planning agent."""

    owner_user_id: uuid.UUID = Field(
        ...,
        description="UUID of the developer owning this agent.",
    )
    name: str = Field(
        ...,
        min_length=3,
        max_length=100,
        description="Human-readable name for the agent.",
        examples=["DevToolsScout"],
    )
    description: str | None = Field(
        None,
        max_length=500,
        description="Brief summary of agent focus or capabilities.",
    )
    specialty_tags: list[str] = Field(
        default_factory=list,
        description="Domain tags (e.g., ['cli-tools', 'devtools']).",
    )


class AgentRegisterResponse(BaseModel):
    """Response returned upon successful agent registration."""

    agent_id: uuid.UUID
    name: str
    trust_tier: int
    daily_post_quota: int
    daily_amend_quota: int
    api_key: str = Field(
        ...,
        description="Raw API key. Copy and store this securely; it will not be shown again.",
    )


class AgentProfileResponse(BaseModel):
    """Public or authenticated profile of an agent."""

    agent_id: uuid.UUID
    name: str
    description: str | None
    specialty_tags: list[str]
    trust_tier: int
    daily_post_quota: int
    daily_amend_quota: int


class ScoutLatestBlueprint(BaseModel):
    """Preview of the most recent blueprint discovered and published by a scout."""

    id: uuid.UUID
    slug: str
    title: str
    created_at: str


class ScoutStatusResponse(BaseModel):
    """Operational telemetry and yield metrics for an autonomous discovery scout."""

    agent_id: uuid.UUID
    name: str
    platform: str
    description: str
    source_description: str
    crawl_targets: list[str]
    ingestion_protocol: str
    window_hours: int
    schedule: str
    rubric_threshold: int
    status: str
    blueprints_count: int
    specialty_tags: list[str]
    last_active_at: str | None = None
    latest_blueprint: ScoutLatestBlueprint | None = None


class ScoutSweepResponse(BaseModel):
    """Execution summary of an on-demand scout swarm sweep pass."""

    status: str
    platform: str
    signals_scraped: int
    opportunities_qualified: int
    blueprints_published: list[dict[str, Any]]
