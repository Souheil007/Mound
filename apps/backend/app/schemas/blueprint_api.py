"""API request and response schemas for blueprints."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.models.blueprint import AmendmentStatus, BlueprintStatus, CritiqueCategory
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
    triggered_by_comment_ids: list[uuid.UUID] = []
    created_at: datetime


class BlueprintDetailResponse(BaseModel):
    """Comprehensive detail response for a blueprint including its latest spec."""

    id: uuid.UUID
    slug: str
    creator_agent_id: uuid.UUID
    creator_agent_name: str | None = None
    status: BlueprintStatus
    current_version_num: int
    upvotes_count: int
    comments_count: int
    revision_requested_at: datetime | None = None
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
    pain_evidence_urls: list[str] = []
    explicit_non_goals: list[str] = []
    mvp_deliverables: list[str] = []
    created_at: datetime
    creator_agent_name: str | None = None


class AmendmentCreateRequest(BaseModel):
    """Payload to propose an amendment (Spec PR) on an existing blueprint."""

    agent_id: uuid.UUID = Field(
        ...,
        description="UUID of the planning agent authoring the amendment.",
    )
    target_section: str = Field(
        ...,
        max_length=100,
        description="Section targeted for improvement (e.g., 'architecture', 'acceptance_criteria').",
        examples=["acceptance_criteria"],
    )
    proposed_change: str = Field(
        ...,
        min_length=20,
        description="Detailed text of the proposed change.",
        examples=["Add test requirement verifying zero credential leakage in replay logs."],
    )
    rationale: str = Field(
        ...,
        min_length=10,
        description="Justification and trade-off analysis explaining why this amendment improves the spec.",
        examples=["Prevents accidental secret exposure in public test artifacts."],
    )


class AmendmentResponse(BaseModel):
    """Response model for a proposed amendment."""

    id: uuid.UUID
    blueprint_id: uuid.UUID
    submitting_agent_id: uuid.UUID
    target_section: str
    proposed_change: str
    rationale: str
    status: AmendmentStatus
    created_at: datetime


class BlueprintVoteRequest(BaseModel):
    """Payload to vote or un-vote a blueprint."""

    user_id: uuid.UUID = Field(..., description="UUID of the authenticated user.")


class BlueprintVoteResponse(BaseModel):
    """Result of blueprint upvote toggle."""

    blueprint_id: uuid.UUID
    upvotes_count: int
    voted: bool


class CommentCreateRequest(BaseModel):
    """Payload to post structured critique on a blueprint."""

    user_id: uuid.UUID = Field(..., description="UUID of the commenting user.")
    category: CritiqueCategory = Field(
        default=CritiqueCategory.GENERAL_FEEDBACK,
        description="Categorization of the critique for agent consumption.",
    )
    content: str = Field(
        ...,
        min_length=5,
        max_length=4000,
        description="Detailed constructive critique or architectural challenge.",
    )


class CommentResponse(BaseModel):
    """Response representation of a blueprint comment."""

    id: uuid.UUID
    blueprint_id: uuid.UUID
    user_id: uuid.UUID
    category: CritiqueCategory
    content: str
    upvotes_count: int
    is_addressed: bool
    addressed_in_version_id: uuid.UUID | None
    created_at: datetime


class CommentVoteRequest(BaseModel):
    """Payload to upvote a critique comment."""

    user_id: uuid.UUID = Field(..., description="UUID of the authenticated voter.")


class CommentVoteResponse(BaseModel):
    """Result of comment upvote action."""

    comment_id: uuid.UUID
    upvotes_count: int
    voted: bool


class VersionBumpRequest(BaseModel):
    """Payload submitted by an agent (or community contributor) to publish a new spec revision."""

    author_agent_id: uuid.UUID = Field(
        ...,
        description="UUID of the agent publishing the revision.",
    )
    expected_version_num: int = Field(
        ...,
        description="Optimistic locking version number to ensure no concurrent collision.",
    )
    spec: BlueprintSpec = Field(
        ...,
        description="The revised blueprint specification payload.",
    )
    changelog_summary: str = Field(
        ...,
        min_length=10,
        max_length=1000,
        description="Clear summary of what was revised and which critiques were addressed.",
    )
    addressed_comment_ids: list[uuid.UUID] = Field(
        default_factory=list,
        description="List of comment UUIDs addressed and resolved in this revision.",
    )


class AgentNotificationItem(BaseModel):
    """Notification for an agent concerning new critiques on its blueprints."""

    blueprint_id: uuid.UUID
    blueprint_slug: str
    comment_id: uuid.UUID
    category: CritiqueCategory
    content: str
    upvotes_count: int
    created_at: datetime


class AgentNotificationsResponse(BaseModel):
    """Batch of unaddressed critiques requiring attention from the agent."""

    agent_id: uuid.UUID
    unaddressed_critiques: list[AgentNotificationItem]
    total_unaddressed: int

