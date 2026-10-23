"""Core data models and schemas for the Scout Swarm and Opportunity Scoring Engine."""

import enum
import uuid
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field, HttpUrl


class PlatformSource(str, enum.Enum):
    """Supported discovery platforms for raw developer complaints and pain signals."""

    REDDIT = "REDDIT"
    HACKERNEWS = "HACKERNEWS"
    GITHUB = "GITHUB"
    TWITTER = "TWITTER"


class RawPainSignal(BaseModel):
    """An ingested raw signal from an online developer or business community."""

    id: str = Field(
        ...,
        description="Unique platform identifier (e.g. reddit post id or HN item id).",
    )
    platform: PlatformSource
    title: str = Field(..., description="Title or headline of the post/complaint.")
    content: str = Field(
        ..., description="Full text body or description of the complaint."
    )
    author: str = Field(..., description="Username or handle of the author.")
    url: str = Field(
        ..., description="Direct permanent URL to the post or discussion thread."
    )
    engagement_count: int = Field(
        default=0,
        description="Upvotes, likes, or comments count indicating public interest.",
    )
    scraped_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = Field(default_factory=dict)


class OpportunityEvaluation(BaseModel):
    """Rubric scoring result assessing whether a pain signal represents a buildable software project opportunity."""

    signal_id: str
    is_structural_problem: bool = Field(
        ...,
        description="True if this is an industry/business-level architectural gap; False if a single repo bug or trivial script.",
    )
    tam_score: int = Field(
        ...,
        ge=0,
        le=25,
        description="Market Magnitude (0-25): Potential addressable market and breadth of impacted developers or teams.",
    )
    urgency_score: int = Field(
        ...,
        ge=0,
        le=25,
        description="Urgency & Pain Severity (0-25): Financial bleeding, data risk, or critical developer hours lost.",
    )
    willingness_to_pay_score: int = Field(
        ...,
        ge=0,
        le=25,
        description="Commercial Viability (0-25): Likelihood that startups, developers, or enterprises will pay recurring fees or adopt.",
    )
    feasibility_score: int = Field(
        ...,
        ge=0,
        le=25,
        description="Technical Feasibility & Buildability (0-25): Can a software engineer or small team build and ship an MVP defensibly in 2-4 weeks?",
    )
    total_score: int = Field(
        ...,
        ge=0,
        le=100,
        description="Cumulative score (sum of all 4 dimensions). Must be >= 70 to qualify for synthesis.",
    )
    proposed_project_name: str | None = Field(
        None,
        description="Short, memorable working project name (e.g. 'KeySentinel', 'QueuePulse').",
    )
    project_type: str | None = Field(
        None,
        description="Form-factor of the potential project (e.g., CLI, Micro-SaaS, Browser/VSCode Extension, API Bridge, Developer Library).",
    )
    mvp_scope: str | None = Field(
        None,
        description="2-3 sentence description of the minimum viable product that can be built in 2-4 weeks.",
    )
    rationale: str = Field(
        ...,
        description="Concise strategic explanation of the score and business opportunity.",
    )
    suggested_pitch: str | None = Field(
        None,
        description="Initial 50-140 character product pitch if qualified.",
    )
    rejection_reason: str | None = Field(
        None,
        description="Detailed reason if rejected (e.g. 'Single localized library bug', 'Trivial CLI wrapper').",
    )
