"""Blueprint and version snapshot models."""

import enum
import uuid
from typing import TYPE_CHECKING, Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
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


class BlueprintVersion(Base):
    """Immutable snapshot of a blueprint specification at a specific version."""

    __tablename__ = "blueprint_versions"
    __table_args__ = (
        UniqueConstraint("blueprint_id", "version_num", name="uq_blueprint_version"),
    )

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
    __table_args__ = (
        UniqueConstraint("user_id", "blueprint_id", name="uq_user_blueprint_vote"),
    )

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
