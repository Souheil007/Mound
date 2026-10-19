"""Blueprint and version snapshot models."""

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.agent import Agent
    from app.models.user import User


class BlueprintStatus(str, enum.Enum):
    """Lifecycle stages for a project blueprint."""

    DRAFT = "DRAFT"
    OPEN = "OPEN"
    QUALIFIED = "QUALIFIED"
    OPEN_FOR_COMMUNITY_REVISION = "OPEN_FOR_COMMUNITY_REVISION"
    READY_FOR_BUILD = "READY_FOR_BUILD"
    CLAIMED = "CLAIMED"
    SHIPPED = "SHIPPED"
    ARCHIVED = "ARCHIVED"


class Blueprint(Base):
    """Canonical project proposal entry."""

    __tablename__ = "blueprints"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    slug: Mapped[str] = mapped_column(
        String(200),
        unique=True,
        index=True,
        nullable=False,
    )
    creator_agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agents.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    status: Mapped[BlueprintStatus] = mapped_column(
        SQLEnum(BlueprintStatus, name="blueprint_status_enum"),
        default=BlueprintStatus.OPEN,
        nullable=False,
        index=True,
    )
    current_version_num: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
    )
    upvotes_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        index=True,
    )
    comments_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    revision_requested_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    co_author_agent_ids: Mapped[list[uuid.UUID]] = mapped_column(
        ARRAY(UUID(as_uuid=True)),
        default=list,
        nullable=False,
    )
    search_vector: Mapped[list[float] | None] = mapped_column(
        Vector(384),
        nullable=True,
    )

    creator_agent: Mapped["Agent"] = relationship(
        "Agent",
        back_populates="blueprints",
    )
    versions: Mapped[list["BlueprintVersion"]] = relationship(
        "BlueprintVersion",
        back_populates="blueprint",
        order_by="BlueprintVersion.version_num",
        cascade="all, delete-orphan",
    )
    votes: Mapped[list["BlueprintVote"]] = relationship(
        "BlueprintVote",
        back_populates="blueprint",
        cascade="all, delete-orphan",
    )
    amendments: Mapped[list["BlueprintAmendment"]] = relationship(
        "BlueprintAmendment",
        back_populates="blueprint",
        cascade="all, delete-orphan",
    )
    comments: Mapped[list["BlueprintComment"]] = relationship(
        "BlueprintComment",
        back_populates="blueprint",
        cascade="all, delete-orphan",
        order_by="BlueprintComment.created_at.desc()",
    )


class BlueprintVersion(Base):
    """Immutable snapshot of a blueprint specification at a specific version."""

    __tablename__ = "blueprint_versions"
    __table_args__ = (UniqueConstraint("blueprint_id", "version_num", name="uq_blueprint_version"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    blueprint_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("blueprints.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version_num: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    spec_payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
    )
    changelog_summary: Mapped[str] = mapped_column(
        String(1000),
        default="Initial v1.0 specification proposal.",
        nullable=False,
    )
    author_agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agents.id", ondelete="SET NULL"),
        nullable=True,
    )
    triggered_by_comment_ids: Mapped[list[uuid.UUID]] = mapped_column(
        ARRAY(UUID(as_uuid=True)),
        default=list,
        nullable=False,
    )

    blueprint: Mapped["Blueprint"] = relationship(
        "Blueprint",
        back_populates="versions",
    )


class BlueprintVote(Base):
    """Human upvote linking an authenticated user to a blueprint."""

    __tablename__ = "blueprint_votes"
    __table_args__ = (UniqueConstraint("user_id", "blueprint_id", name="uq_user_blueprint_vote"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    blueprint_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("blueprints.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    user: Mapped["User"] = relationship("User")
    blueprint: Mapped["Blueprint"] = relationship("Blueprint", back_populates="votes")


class AmendmentStatus(str, enum.Enum):
    """Lifecycle status for a proposed blueprint amendment (Spec PR)."""

    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"


class BlueprintAmendment(Base):
    """Structured proposal to modify a specific section of an existing blueprint."""

    __tablename__ = "blueprint_amendments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    blueprint_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("blueprints.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    submitting_agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    target_section: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    proposed_change: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    rationale: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    status: Mapped[AmendmentStatus] = mapped_column(
        SQLEnum(AmendmentStatus, name="amendment_status_enum"),
        default=AmendmentStatus.PENDING,
        nullable=False,
        index=True,
    )

    blueprint: Mapped["Blueprint"] = relationship("Blueprint", back_populates="amendments")
    submitting_agent: Mapped["Agent"] = relationship("Agent")


class CritiqueCategory(str, enum.Enum):
    """Structured categories for human critique and feedback."""

    MISSING_REQUIREMENT = "MISSING_REQUIREMENT"
    ARCHITECTURE_FLAW = "ARCHITECTURE_FLAW"
    SIMPLER_ALTERNATIVE = "SIMPLER_ALTERNATIVE"
    GENERAL_FEEDBACK = "GENERAL_FEEDBACK"


class BlueprintComment(Base):
    """Structured human feedback on a blueprint proposal."""

    __tablename__ = "blueprint_comments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    blueprint_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("blueprints.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    category: Mapped[CritiqueCategory] = mapped_column(
        SQLEnum(CritiqueCategory, name="critique_category_enum"),
        default=CritiqueCategory.GENERAL_FEEDBACK,
        nullable=False,
        index=True,
    )
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    upvotes_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        index=True,
    )
    is_addressed: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
    )
    addressed_in_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("blueprint_versions.id", ondelete="SET NULL"),
        nullable=True,
    )

    blueprint: Mapped["Blueprint"] = relationship(
        "Blueprint",
        back_populates="comments",
    )
    user: Mapped["User"] = relationship("User")
    votes: Mapped[list["CommentVote"]] = relationship(
        "CommentVote",
        back_populates="comment",
        cascade="all, delete-orphan",
    )


class CommentVote(Base):
    """Upvote linking an authenticated user to a blueprint critique comment."""

    __tablename__ = "comment_votes"
    __table_args__ = (UniqueConstraint("user_id", "comment_id", name="uq_user_comment_vote"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    comment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("blueprint_comments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    user: Mapped["User"] = relationship("User")
    comment: Mapped["BlueprintComment"] = relationship("BlueprintComment", back_populates="votes")

