"""User database model for authenticated developers and voters."""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.agent import Agent


class User(Base):
    """Represents a human user authenticated via GitHub OAuth."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    github_id: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        index=True,
        nullable=False,
    )
    username: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        index=True,
        nullable=False,
    )
    email: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    avatar_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )
    trust_score: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    agents: Mapped[list["Agent"]] = relationship(
        "Agent",
        back_populates="owner",
        cascade="all, delete-orphan",
    )
