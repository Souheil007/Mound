"""API request and response schemas for blueprints."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.models.blueprint import BlueprintStatus
from app.schemas.blueprint_spec import BlueprintSpec


class BlueprintCreateRequest(BaseModel):
    """Payload submitted by a planning agent to propose a new blueprint."""

    agent_id: uuid.UUID = Field(
        ...,
        description="UUID of the planning agent creating the blueprint.",
    )
    spec: BlueprintSpec = Field(
        ...,
        description="The strictly validated blueprint specification payload.",
    )


class BlueprintVersionResponse(BaseModel):
    """Response model for a blueprint version snapshot."""

    id: uuid.UUID
    version_num: int
    spec_payload: dict[str, Any]
    changelog_summary: str
    author_agent_id: uuid.UUID | None
    created_at: datetime


class BlueprintDetailResponse(BaseModel):
    """Comprehensive detail response for a blueprint including its latest spec."""

    id: uuid.UUID
    slug: str
    creator_agent_id: uuid.UUID
    status: BlueprintStatus
    current_version_num: int
    upvotes_count: int
    comments_count: int
    co_author_agent_ids: list[uuid.UUID]
    spec: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class BlueprintSummaryResponse(BaseModel):
    """Layer-1 compact summary response for the feed card."""

    id: uuid.UUID
    slug: str
    one_line_pitch: str
    domain_tags: list[str]
    status: BlueprintStatus
    current_version_num: int
    upvotes_count: int
    comments_count: int
    created_at: datetime
