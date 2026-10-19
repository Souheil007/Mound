"""Service functions for blueprint lifecycle and persistence."""

import re
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.agent import Agent
from app.models.blueprint import Blueprint, BlueprintStatus, BlueprintVersion
from app.schemas.blueprint_api import (
    BlueprintCreateRequest,
    BlueprintDetailResponse,
    BlueprintSummaryResponse,
    BlueprintVersionResponse,
)
from app.services.embedding_engine import EmbeddingEngine


def generate_slug(text: str) -> str:
    """Generates a URL-friendly slug from a text string with unique suffix.

    Args:
        text: Input string (e.g., one_line_pitch).

    Returns:
        A sanitized, hyphen-separated slug string.
    """
    clean_text = re.sub(r"[^\w\s-]", "", text.lower()).strip()
    words = re.sub(r"[-\s]+", "-", clean_text).split("-")[:6]
    base_slug = "-".join(words)
    unique_suffix = uuid.uuid4().hex[:6]
    return f"{base_slug}-{unique_suffix}"


class BlueprintService:
    """Manages creation, retrieval, and versioning of project blueprints."""

    @classmethod
    async def create_blueprint(
        cls,
        session: AsyncSession,
        request: BlueprintCreateRequest,
    ) -> BlueprintDetailResponse:
        """Creates a new blueprint and its v1 snapshot with vector embedding.

        Args:
            session: Active SQLAlchemy async session.
            request: The validated blueprint proposal request.

        Returns:
            A BlueprintDetailResponse containing the created blueprint and spec.

        Raises:
            ValueError: If the submitting agent does not exist.
        """
        agent_stmt = select(Agent).where(Agent.id == request.agent_id)
        agent_result = await session.execute(agent_stmt)
        agent = agent_result.scalar_one_or_none()
        if not agent:
            raise ValueError(f"Agent with ID '{request.agent_id}' does not exist.")

        spec_data = request.spec.model_dump(mode="json")
        embed_input = f"{request.spec.one_line_pitch}\n{request.spec.problem_statement}"
        search_vector = EmbeddingEngine.embed_text(embed_input)

        slug = generate_slug(request.spec.one_line_pitch)
        blueprint = Blueprint(
            slug=slug,
            creator_agent_id=request.agent_id,
            status=BlueprintStatus.OPEN,
            current_version_num=1,
            search_vector=search_vector,
        )
        session.add(blueprint)
        await session.flush()

        v1 = BlueprintVersion(
            blueprint_id=blueprint.id,
            version_num=1,
            spec_payload=spec_data,
            changelog_summary="Initial v1.0 specification proposal.",
            author_agent_id=request.agent_id,
        )
        session.add(v1)
        await session.commit()
        await session.refresh(blueprint)

        return BlueprintDetailResponse(
            id=blueprint.id,
            slug=blueprint.slug,
            creator_agent_id=blueprint.creator_agent_id,
            status=blueprint.status,
            current_version_num=blueprint.current_version_num,
            upvotes_count=blueprint.upvotes_count,
            comments_count=blueprint.comments_count,
            co_author_agent_ids=blueprint.co_author_agent_ids,
            spec=spec_data,
            created_at=blueprint.created_at,
            updated_at=blueprint.updated_at,
        )

    @classmethod
    async def get_blueprint_by_id(
        cls,
        session: AsyncSession,
        blueprint_id: uuid.UUID,
    ) -> BlueprintDetailResponse | None:
        """Retrieves a blueprint by its UUID along with its latest specification.

        Args:
            session: Active SQLAlchemy async session.
            blueprint_id: UUID of the target blueprint.

        Returns:
            A BlueprintDetailResponse or None if not found.
        """
        stmt = select(Blueprint).options(selectinload(Blueprint.versions)).where(Blueprint.id == blueprint_id)
        result = await session.execute(stmt)
        blueprint = result.scalar_one_or_none()
        if not blueprint:
            return None

        latest_version = max(blueprint.versions, key=lambda v: v.version_num)
        return BlueprintDetailResponse(
            id=blueprint.id,
            slug=blueprint.slug,
            creator_agent_id=blueprint.creator_agent_id,
            status=blueprint.status,
            current_version_num=blueprint.current_version_num,
            upvotes_count=blueprint.upvotes_count,
            comments_count=blueprint.comments_count,
            co_author_agent_ids=blueprint.co_author_agent_ids,
            spec=latest_version.spec_payload,
            created_at=blueprint.created_at,
            updated_at=blueprint.updated_at,
        )

    @classmethod
    async def list_blueprints(
        cls,
        session: AsyncSession,
        limit: int = 20,
        offset: int = 0,
    ) -> list[BlueprintSummaryResponse]:
        """Lists recent blueprints for the Layer-1 feed card.

        Args:
            session: Active SQLAlchemy async session.
            limit: Maximum number of blueprints to return.
            offset: Query offset for pagination.

        Returns:
            A list of BlueprintSummaryResponse items.
        """
        stmt = (
            select(Blueprint)
            .options(selectinload(Blueprint.versions))
            .order_by(Blueprint.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await session.execute(stmt)
        blueprints = result.scalars().all()

        summaries = []
        for bp in blueprints:
            latest_version = max(bp.versions, key=lambda v: v.version_num)
            spec = latest_version.spec_payload
            summaries.append(
                BlueprintSummaryResponse(
                    id=bp.id,
                    slug=bp.slug,
                    one_line_pitch=spec.get("one_line_pitch", ""),
                    domain_tags=spec.get("domain_tags", []),
                    status=bp.status,
                    current_version_num=bp.current_version_num,
                    upvotes_count=bp.upvotes_count,
                    comments_count=bp.comments_count,
                    created_at=bp.created_at,
                )
            )
        return summaries

    @classmethod
    async def list_versions(
        cls,
        session: AsyncSession,
        blueprint_id: uuid.UUID,
    ) -> list[BlueprintVersionResponse]:
        """Retrieves full version history for a blueprint.

        Args:
            session: Active SQLAlchemy async session.
            blueprint_id: UUID of the target blueprint.

        Returns:
            A list of BlueprintVersionResponse items ordered by version number.
        """
        stmt = (
            select(BlueprintVersion)
            .where(BlueprintVersion.blueprint_id == blueprint_id)
            .order_by(BlueprintVersion.version_num.asc())
        )
        result = await session.execute(stmt)
        versions = result.scalars().all()
        return [
            BlueprintVersionResponse(
                id=v.id,
                version_num=v.version_num,
                spec_payload=v.spec_payload,
                changelog_summary=v.changelog_summary,
                author_agent_id=v.author_agent_id,
                created_at=v.created_at,
            )
            for v in versions
        ]
