"""Autonomous planning agent model."""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.blueprint import Blueprint
    from app.models.user import User


class Agent(Base):
    """Represents a connected autonomous planning agent (BYOA)."""

    __tablename__ = "agents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    description: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )
    api_key_hash: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        index=True,
        nullable=False,
    )
    specialty_tags: Mapped[list[str]] = mapped_column(
        ARRAY(String),
        default=list,
        nullable=False,
    )
    trust_tier: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
    )
    daily_post_quota: Mapped[int] = mapped_column(
        Integer,
        default=2,
        nullable=False,
    )
    daily_amend_quota: Mapped[int] = mapped_column(
        Integer,
        default=10,
        nullable=False,
    )

    owner: Mapped["User"] = relationship(
        "User",
        back_populates="agents",
    )
    blueprints: Mapped[list["Blueprint"]] = relationship(
        "Blueprint",
        back_populates="creator_agent",
        cascade="all, delete-orphan",
    )
