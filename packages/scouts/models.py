"""Core data models and schemas for the Scout Swarm and Opportunity Scoring Engine."""

import enum
import uuid
from datetime import datetime
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

    id: str = Field(..., description="Unique platform identifier (e.g. reddit post id or HN item id).")
    platform: PlatformSource
    title: str = Field(..., description="Title or headline of the post/complaint.")
    content: str = Field(..., description="Full text body or description of the complaint.")
    author: str = Field(..., description="Username or handle of the author.")
    url: str = Field(..., description="Direct permanent URL to the post or discussion thread.")
    engagement_count: int = Field(default=0, description="Upvotes, likes, or comments count indicating public interest.")
    scraped_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = Field(default_factory=dict)


class OpportunityEvaluation(BaseModel):
    """Rubric scoring result assessing whether a pain signal represents a venture-scale opportunity."""

    signal_id: str
    is_structural_problem: bool = Field(
        ...,
        description="True if this is an industry/business-level architectural gap; False if a single repo bug or trivial script.",
    )
    tam_score: int = Field(
        ...,
        ge=0,
        le=25,
        description="Market Magnitude (0-25): Potential total addressable market and breadth of impacted teams.",
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
        description="Commercial Viability (0-25): Likelihood that startups or enterprises will pay recurring SaaS fees.",
    )
    feasibility_score: int = Field(
        ...,
        ge=0,
        le=25,
        description="Technical Feasibility & Moat (0-25): Can a software system solve this defensibly without being a trivial 20-line script?",
    )
    total_score: int = Field(
        ...,
        ge=0,
        le=100,
        description="Cumulative score (sum of all 4 dimensions). Must be >= 80 to qualify.",
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
