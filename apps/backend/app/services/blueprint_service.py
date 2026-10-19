import re
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.agent import Agent
from app.models.blueprint import (
    AmendmentStatus,
    Blueprint,
    BlueprintAmendment,
    BlueprintComment,
    BlueprintStatus,
    BlueprintVersion,
    BlueprintVote,
    CommentVote,
)
from app.models.user import User
from app.schemas.blueprint_api import (
    AgentNotificationItem,
    AgentNotificationsResponse,
    AmendmentCreateRequest,
    AmendmentResponse,
    BlueprintCreateRequest,
    BlueprintDetailResponse,
    BlueprintSummaryResponse,
    BlueprintVersionResponse,
    BlueprintVoteResponse,
    CommentCreateRequest,
    CommentResponse,
    CommentVoteResponse,
    VersionBumpRequest,
)
from app.services.embedding_engine import EmbeddingEngine
from app.services.spec_linter import SpecLinter


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
            revision_requested_at=blueprint.revision_requested_at,
            co_author_agent_ids=blueprint.co_author_agent_ids,
            spec=spec_data,
            created_at=blueprint.created_at,
            updated_at=blueprint.updated_at,
        )

    @classmethod
    async def resolve_blueprint_id(
        cls,
        session: AsyncSession,
        identifier: str | uuid.UUID,
    ) -> uuid.UUID | None:
        """Resolves a blueprint identifier (UUID, UUID string, or slug) to its database UUID.

        Args:
            session: Active SQLAlchemy async session.
            identifier: Target UUID, UUID string, or blueprint slug.

        Returns:
            The resolved blueprint UUID or None if not found.
        """
        if isinstance(identifier, uuid.UUID):
            return identifier
        id_str = str(identifier).strip()
        try:
            return uuid.UUID(id_str)
        except ValueError:
            stmt = select(Blueprint.id).where(Blueprint.slug == id_str)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    @classmethod
    async def get_blueprint_by_id_or_slug(
        cls,
        session: AsyncSession,
        identifier: str | uuid.UUID,
    ) -> BlueprintDetailResponse | None:
        """Retrieves a blueprint by its UUID or slug along with its latest specification.

        Args:
            session: Active SQLAlchemy async session.
            identifier: Target UUID, UUID string, or blueprint slug.

        Returns:
            A BlueprintDetailResponse or None if not found.
        """
        stmt = select(Blueprint).options(
            selectinload(Blueprint.versions),
            selectinload(Blueprint.creator_agent),
        )
        if isinstance(identifier, uuid.UUID):
            stmt = stmt.where(Blueprint.id == identifier)
        else:
            id_str = str(identifier).strip()
            try:
                parsed_uuid = uuid.UUID(id_str)
                stmt = stmt.where(Blueprint.id == parsed_uuid)
            except ValueError:
                stmt = stmt.where(Blueprint.slug == id_str)

        result = await session.execute(stmt)
        blueprint = result.scalar_one_or_none()
        if not blueprint:
            return None

        latest_version = max(blueprint.versions, key=lambda v: v.version_num)
        return BlueprintDetailResponse(
            id=blueprint.id,
            slug=blueprint.slug,
            creator_agent_id=blueprint.creator_agent_id,
            creator_agent_name=blueprint.creator_agent.name if blueprint.creator_agent else None,
            status=blueprint.status,
            current_version_num=blueprint.current_version_num,
            upvotes_count=blueprint.upvotes_count,
            comments_count=blueprint.comments_count,
            revision_requested_at=blueprint.revision_requested_at,
            co_author_agent_ids=blueprint.co_author_agent_ids,
            spec=latest_version.spec_payload,
            created_at=blueprint.created_at,
            updated_at=blueprint.updated_at,
        )

    @classmethod
    async def get_blueprint_by_id(
        cls,
        session: AsyncSession,
        blueprint_id: uuid.UUID | str,
    ) -> BlueprintDetailResponse | None:
        """Retrieves a blueprint by its UUID or slug along with its latest specification."""
        return await cls.get_blueprint_by_id_or_slug(session, blueprint_id)

    @classmethod
    async def list_blueprints(
        cls,
        session: AsyncSession,
        status_filter: BlueprintStatus | None = None,
        sort_by: str = "new",
        limit: int = 20,
        offset: int = 0,
    ) -> list[BlueprintSummaryResponse]:
        """Lists recent blueprints for the Layer-1 feed card with filtering and sorting.

        Args:
            session: Active SQLAlchemy async session.
            status_filter: Optional filter by BlueprintStatus.
            sort_by: Sorting mode: 'top' (upvotes), 'hot' (activity), or 'new' (chronological).
            limit: Maximum number of blueprints to return.
            offset: Query offset for pagination.

        Returns:
            A list of BlueprintSummaryResponse items.
        """
        stmt = select(Blueprint).options(
            selectinload(Blueprint.versions),
            selectinload(Blueprint.creator_agent),
        )

        if status_filter:
            stmt = stmt.where(Blueprint.status == status_filter)

        if sort_by.lower() == "top":
            stmt = stmt.order_by(Blueprint.upvotes_count.desc(), Blueprint.created_at.desc())
        elif sort_by.lower() == "hot":
            stmt = stmt.order_by(
                (Blueprint.upvotes_count * 2 + Blueprint.comments_count).desc(),
                Blueprint.created_at.desc(),
            )
        else:
            stmt = stmt.order_by(Blueprint.created_at.desc())

        stmt = stmt.limit(limit).offset(offset)
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
                    pain_evidence_urls=spec.get("pain_evidence_urls", []),
                    explicit_non_goals=spec.get("explicit_non_goals", []),
                    mvp_deliverables=spec.get("mvp_deliverables", []),
                    created_at=bp.created_at,
                    creator_agent_name=bp.creator_agent.name if bp.creator_agent else None,
                )
            )
        return summaries

    @classmethod
    async def list_versions(
        cls,
        session: AsyncSession,
        blueprint_id: uuid.UUID | str,
    ) -> list[BlueprintVersionResponse]:
        """Retrieves full version history for a blueprint.

        Args:
            session: Active SQLAlchemy async session.
            blueprint_id: UUID or slug of the target blueprint.

        Returns:
            A list of BlueprintVersionResponse items ordered by version number.
        """
        resolved_id = await cls.resolve_blueprint_id(session, blueprint_id)
        if not resolved_id:
            return []

        stmt = (
            select(BlueprintVersion)
            .where(BlueprintVersion.blueprint_id == resolved_id)
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

    @classmethod
    async def create_amendment(
        cls,
        session: AsyncSession,
        blueprint_id: uuid.UUID | str,
        request: AmendmentCreateRequest,
    ) -> AmendmentResponse:
        """Submits a new amendment (Spec PR) on an existing blueprint.

        Args:
            session: Active SQLAlchemy async session.
            blueprint_id: UUID or slug of the target blueprint.
            request: Amendment proposal payload.

        Returns:
            The created AmendmentResponse.

        Raises:
            ValueError: If blueprint or submitting agent does not exist.
        """
        resolved_id = await cls.resolve_blueprint_id(session, blueprint_id)
        if not resolved_id:
            raise ValueError(f"Blueprint with ID '{blueprint_id}' does not exist.")

        bp_stmt = select(Blueprint).where(Blueprint.id == resolved_id)
        bp_res = await session.execute(bp_stmt)
        blueprint = bp_res.scalar_one_or_none()
        if not blueprint:
            raise ValueError(f"Blueprint with ID '{blueprint_id}' does not exist.")

        agent_stmt = select(Agent).where(Agent.id == request.agent_id)
        agent_res = await session.execute(agent_stmt)
        agent = agent_res.scalar_one_or_none()
        if not agent:
            raise ValueError(f"Agent with ID '{request.agent_id}' does not exist.")

        amendment = BlueprintAmendment(
            blueprint_id=resolved_id,
            submitting_agent_id=request.agent_id,
            target_section=request.target_section,
            proposed_change=request.proposed_change,
            rationale=request.rationale,
            status=AmendmentStatus.PENDING,
        )
        session.add(amendment)
        await session.commit()
        await session.refresh(amendment)

        return AmendmentResponse(
            id=amendment.id,
            blueprint_id=amendment.blueprint_id,
            submitting_agent_id=amendment.submitting_agent_id,
            target_section=amendment.target_section,
            proposed_change=amendment.proposed_change,
            rationale=amendment.rationale,
            status=amendment.status,
            created_at=amendment.created_at,
        )

    @classmethod
    async def list_amendments(
        cls,
        session: AsyncSession,
        blueprint_id: uuid.UUID | str,
    ) -> list[AmendmentResponse]:
        """Lists all amendments submitted for a blueprint.

        Args:
            session: Active SQLAlchemy async session.
            blueprint_id: UUID or slug of the target blueprint.

        Returns:
            List of AmendmentResponse records.
        """
        resolved_id = await cls.resolve_blueprint_id(session, blueprint_id)
        if not resolved_id:
            return []

        stmt = (
            select(BlueprintAmendment)
            .where(BlueprintAmendment.blueprint_id == resolved_id)
            .order_by(BlueprintAmendment.created_at.desc())
        )
        result = await session.execute(stmt)
        amendments = result.scalars().all()
        return [
            AmendmentResponse(
                id=a.id,
                blueprint_id=a.blueprint_id,
                submitting_agent_id=a.submitting_agent_id,
                target_section=a.target_section,
                proposed_change=a.proposed_change,
                rationale=a.rationale,
                status=a.status,
                created_at=a.created_at,
            )
            for a in amendments
        ]

    @classmethod
    async def accept_amendment(
        cls,
        session: AsyncSession,
        blueprint_id: uuid.UUID | str,
        amendment_id: uuid.UUID,
    ) -> AmendmentResponse:
        """Accepts an amendment and credits the author as a co-author on the blueprint.

        Args:
            session: Active SQLAlchemy async session.
            blueprint_id: UUID or slug of the target blueprint.
            amendment_id: UUID of the amendment to accept.

        Returns:
            The updated AmendmentResponse with status ACCEPTED.

        Raises:
            ValueError: If amendment or blueprint not found.
        """
        resolved_id = await cls.resolve_blueprint_id(session, blueprint_id)
        if not resolved_id:
            raise ValueError(f"Blueprint with ID '{blueprint_id}' does not exist.")

        stmt = select(BlueprintAmendment).where(
            BlueprintAmendment.id == amendment_id,
            BlueprintAmendment.blueprint_id == resolved_id,
        )
        result = await session.execute(stmt)
        amendment = result.scalar_one_or_none()
        if not amendment:
            raise ValueError(f"Amendment with ID '{amendment_id}' not found on blueprint '{blueprint_id}'.")

        amendment.status = AmendmentStatus.ACCEPTED

        bp_stmt = select(Blueprint).where(Blueprint.id == resolved_id)
        bp_res = await session.execute(bp_stmt)
        blueprint = bp_res.scalar_one()

        current_co_authors = list(blueprint.co_author_agent_ids or [])
        if amendment.submitting_agent_id not in current_co_authors:
            current_co_authors.append(amendment.submitting_agent_id)
            blueprint.co_author_agent_ids = current_co_authors

        await session.commit()
        await session.refresh(amendment)

        return AmendmentResponse(
            id=amendment.id,
            blueprint_id=amendment.blueprint_id,
            submitting_agent_id=amendment.submitting_agent_id,
            target_section=amendment.target_section,
            proposed_change=amendment.proposed_change,
            rationale=amendment.rationale,
            status=amendment.status,
            created_at=amendment.created_at,
        )

    @classmethod
    async def vote_blueprint(
        cls,
        session: AsyncSession,
        blueprint_id: uuid.UUID | str,
        user_id: uuid.UUID,
    ) -> BlueprintVoteResponse:
        """Toggles upvote for a human user on a blueprint proposal.

        Args:
            session: Active SQLAlchemy async session.
            blueprint_id: UUID or slug of the target blueprint.
            user_id: Authenticated user UUID.

        Returns:
            BlueprintVoteResponse indicating current vote state and total upvotes.

        Raises:
            ValueError: If user or blueprint does not exist.
        """
        user_stmt = select(User).where(User.id == user_id)
        user_res = await session.execute(user_stmt)
        if not user_res.scalar_one_or_none():
            raise ValueError(f"User with ID '{user_id}' does not exist.")

        resolved_id = await cls.resolve_blueprint_id(session, blueprint_id)
        if not resolved_id:
            raise ValueError(f"Blueprint with ID '{blueprint_id}' does not exist.")

        bp_stmt = select(Blueprint).where(Blueprint.id == resolved_id)
        bp_res = await session.execute(bp_stmt)
        blueprint = bp_res.scalar_one_or_none()
        if not blueprint:
            raise ValueError(f"Blueprint with ID '{blueprint_id}' does not exist.")

        vote_stmt = select(BlueprintVote).where(
            BlueprintVote.user_id == user_id,
            BlueprintVote.blueprint_id == resolved_id,
        )
        vote_res = await session.execute(vote_stmt)
        existing_vote = vote_res.scalar_one_or_none()

        if existing_vote:
            await session.delete(existing_vote)
            blueprint.upvotes_count = max(0, blueprint.upvotes_count - 1)
            voted = False
        else:
            vote = BlueprintVote(user_id=user_id, blueprint_id=resolved_id)
            session.add(vote)
            blueprint.upvotes_count += 1
            voted = True

        # Graduate to QUALIFIED status when upvotes reach 10
        if blueprint.upvotes_count >= 10 and blueprint.status == BlueprintStatus.OPEN:
            blueprint.status = BlueprintStatus.QUALIFIED

        await session.commit()
        return BlueprintVoteResponse(
            blueprint_id=blueprint.id,
            upvotes_count=blueprint.upvotes_count,
            voted=voted,
        )

    @classmethod
    async def create_comment(
        cls,
        session: AsyncSession,
        blueprint_id: uuid.UUID | str,
        request: CommentCreateRequest,
    ) -> CommentResponse:
        """Posts structured human critique on a blueprint.

        Args:
            session: Active SQLAlchemy async session.
            blueprint_id: UUID or slug of the target blueprint.
            request: Comment payload with category and content.

        Returns:
            The created CommentResponse.

        Raises:
            ValueError: If user or blueprint does not exist.
        """
        user_stmt = select(User).where(User.id == request.user_id)
        user_res = await session.execute(user_stmt)
        if not user_res.scalar_one_or_none():
            raise ValueError(f"User with ID '{request.user_id}' does not exist.")

        resolved_id = await cls.resolve_blueprint_id(session, blueprint_id)
        if not resolved_id:
            raise ValueError(f"Blueprint with ID '{blueprint_id}' does not exist.")

        bp_stmt = select(Blueprint).where(Blueprint.id == resolved_id)
        bp_res = await session.execute(bp_stmt)
        blueprint = bp_res.scalar_one_or_none()
        if not blueprint:
            raise ValueError(f"Blueprint with ID '{blueprint_id}' does not exist.")

        comment = BlueprintComment(
            blueprint_id=resolved_id,
            user_id=request.user_id,
            category=request.category,
            content=request.content,
        )
        session.add(comment)
        blueprint.comments_count += 1

        # Revision Trigger: 3+ human comments triggers REVISION_REQUESTED
        if blueprint.comments_count >= 3 and blueprint.revision_requested_at is None:
            blueprint.revision_requested_at = datetime.now(timezone.utc)

        await session.commit()
        await session.refresh(comment)

        return CommentResponse(
            id=comment.id,
            blueprint_id=comment.blueprint_id,
            user_id=comment.user_id,
            category=comment.category,
            content=comment.content,
            upvotes_count=comment.upvotes_count,
            is_addressed=comment.is_addressed,
            addressed_in_version_id=comment.addressed_in_version_id,
            created_at=comment.created_at,
        )

    @classmethod
    async def list_comments(
        cls,
        session: AsyncSession,
        blueprint_id: uuid.UUID | str,
    ) -> list[CommentResponse]:
        """Lists all comments for a blueprint ordered by upvotes and recency.

        Args:
            session: Active SQLAlchemy async session.
            blueprint_id: UUID or slug of the target blueprint.

        Returns:
            A list of CommentResponse objects.
        """
        resolved_id = await cls.resolve_blueprint_id(session, blueprint_id)
        if not resolved_id:
            return []

        stmt = (
            select(BlueprintComment)
            .where(BlueprintComment.blueprint_id == resolved_id)
            .order_by(BlueprintComment.upvotes_count.desc(), BlueprintComment.created_at.desc())
        )
        result = await session.execute(stmt)
        comments = result.scalars().all()
        return [
            CommentResponse(
                id=c.id,
                blueprint_id=c.blueprint_id,
                user_id=c.user_id,
                category=c.category,
                content=c.content,
                upvotes_count=c.upvotes_count,
                is_addressed=c.is_addressed,
                addressed_in_version_id=c.addressed_in_version_id,
                created_at=c.created_at,
            )
            for c in comments
        ]

    @classmethod
    async def vote_comment(
        cls,
        session: AsyncSession,
        comment_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> CommentVoteResponse:
        """Toggles upvote for a comment.

        Args:
            session: Active SQLAlchemy async session.
            comment_id: Comment UUID.
            user_id: Authenticated voter UUID.

        Returns:
            CommentVoteResponse with updated vote count and state.

        Raises:
            ValueError: If comment or user does not exist.
        """
        user_stmt = select(User).where(User.id == user_id)
        user_res = await session.execute(user_stmt)
        if not user_res.scalar_one_or_none():
            raise ValueError(f"User with ID '{user_id}' does not exist.")

        comm_stmt = select(BlueprintComment).where(BlueprintComment.id == comment_id)
        comm_res = await session.execute(comm_stmt)
        comment = comm_res.scalar_one_or_none()
        if not comment:
            raise ValueError(f"Comment with ID '{comment_id}' does not exist.")

        bp_stmt = select(Blueprint).where(Blueprint.id == comment.blueprint_id)
        bp_res = await session.execute(bp_stmt)
        blueprint = bp_res.scalar_one()

        vote_stmt = select(CommentVote).where(
            CommentVote.user_id == user_id,
            CommentVote.comment_id == comment_id,
        )
        vote_res = await session.execute(vote_stmt)
        existing_vote = vote_res.scalar_one_or_none()

        if existing_vote:
            await session.delete(existing_vote)
            comment.upvotes_count = max(0, comment.upvotes_count - 1)
            voted = False
        else:
            vote = CommentVote(user_id=user_id, comment_id=comment_id)
            session.add(vote)
            comment.upvotes_count += 1
            voted = True

        # Revision Trigger: 1 comment reaching 5+ upvotes queues REVISION_REQUESTED
        if comment.upvotes_count >= 5 and blueprint.revision_requested_at is None:
            blueprint.revision_requested_at = datetime.now(timezone.utc)

        await session.commit()
        return CommentVoteResponse(
            comment_id=comment.id,
            upvotes_count=comment.upvotes_count,
            voted=voted,
        )

    @classmethod
    async def bump_version(
        cls,
        session: AsyncSession,
        blueprint_id: uuid.UUID | str,
        request: VersionBumpRequest,
    ) -> BlueprintDetailResponse:
        """Publishes a new version snapshot of a blueprint specification.

        Args:
            session: Active SQLAlchemy async session.
            blueprint_id: UUID or slug of the target blueprint.
            request: VersionBumpRequest with optimistic lock version and revised spec.

        Returns:
            BlueprintDetailResponse for the updated blueprint.

        Raises:
            ValueError: If version conflict occurs or spec linting fails.
            PermissionError: If unauthorized agent attempts revision within 48h window.
        """
        agent_stmt = select(Agent).where(Agent.id == request.author_agent_id)
        agent_res = await session.execute(agent_stmt)
        if not agent_res.scalar_one_or_none():
            raise ValueError(f"Agent with ID '{request.author_agent_id}' does not exist.")

        resolved_id = await cls.resolve_blueprint_id(session, blueprint_id)
        if not resolved_id:
            raise ValueError(f"Blueprint with ID '{blueprint_id}' does not exist.")

        bp_stmt = (
            select(Blueprint)
            .options(selectinload(Blueprint.versions))
            .where(Blueprint.id == resolved_id)
        )
        bp_res = await session.execute(bp_stmt)
        blueprint = bp_res.scalar_one_or_none()
        if not blueprint:
            raise ValueError(f"Blueprint with ID '{blueprint_id}' does not exist.")

        # 1. Optimistic Locking check
        if blueprint.current_version_num != request.expected_version_num:
            raise ValueError(
                f"Optimistic lock conflict: current version is {blueprint.current_version_num}, "
                f"expected {request.expected_version_num}."
            )

        # 2. Check 48-Hour Fallback and Authorization
        is_creator = blueprint.creator_agent_id == request.author_agent_id
        is_co_author = request.author_agent_id in (blueprint.co_author_agent_ids or [])
        now = datetime.now(timezone.utc)
        is_timed_out = (
            blueprint.revision_requested_at is not None
            and (now - blueprint.revision_requested_at) >= timedelta(hours=48)
        )
        is_community_open = (
            blueprint.status == BlueprintStatus.OPEN_FOR_COMMUNITY_REVISION
            or is_timed_out
        )

        if not (is_creator or is_co_author):
            if not is_community_open:
                raise PermissionError(
                    "Blueprint revision is reserved for the creator agent during the 48-hour response window."
                )
            # Community responder gains co-authorship credit
            co_authors = list(blueprint.co_author_agent_ids or [])
            if request.author_agent_id not in co_authors:
                co_authors.append(request.author_agent_id)
                blueprint.co_author_agent_ids = co_authors

        # 3. Resilient Spec Linter
        lint_res = await SpecLinter.lint(request.spec)
        if not lint_res.passed:
            raise ValueError(f"Spec linting failed: {', '.join(lint_res.errors)}")

        # 4. Re-calculate embedding
        embed_input = f"{request.spec.one_line_pitch}\n{request.spec.problem_statement}"
        blueprint.search_vector = EmbeddingEngine.embed_text(embed_input)

        # 5. Snapshot new version
        next_version_num = blueprint.current_version_num + 1
        spec_data = request.spec.model_dump(mode="json")
        new_version = BlueprintVersion(
            blueprint_id=blueprint.id,
            version_num=next_version_num,
            spec_payload=spec_data,
            changelog_summary=request.changelog_summary,
            author_agent_id=request.author_agent_id,
            triggered_by_comment_ids=request.addressed_comment_ids,
        )
        session.add(new_version)
        await session.flush()

        # 6. Mark addressed comments
        if request.addressed_comment_ids:
            comm_stmt = select(BlueprintComment).where(
                BlueprintComment.id.in_(request.addressed_comment_ids),
                BlueprintComment.blueprint_id == blueprint.id,
            )
            comm_res = await session.execute(comm_stmt)
            for comm in comm_res.scalars().all():
                comm.is_addressed = True
                comm.addressed_in_version_id = new_version.id

        # 7. Update blueprint state
        blueprint.current_version_num = next_version_num
        blueprint.revision_requested_at = None
        if blueprint.status == BlueprintStatus.OPEN_FOR_COMMUNITY_REVISION:
            blueprint.status = (
                BlueprintStatus.QUALIFIED if blueprint.upvotes_count >= 10 else BlueprintStatus.OPEN
            )

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
            revision_requested_at=blueprint.revision_requested_at,
            co_author_agent_ids=blueprint.co_author_agent_ids,
            spec=spec_data,
            created_at=blueprint.created_at,
            updated_at=blueprint.updated_at,
        )

    @classmethod
    async def get_agent_notifications(
        cls,
        session: AsyncSession,
        agent_id: uuid.UUID,
    ) -> AgentNotificationsResponse:
        """Polls unaddressed human critiques and triggers community fallback if timed out.

        Args:
            session: Active SQLAlchemy async session.
            agent_id: Polling agent UUID.

        Returns:
            AgentNotificationsResponse containing unaddressed critiques.
        """
        agent_stmt = select(Agent).where(Agent.id == agent_id)
        agent_res = await session.execute(agent_stmt)
        if not agent_res.scalar_one_or_none():
            raise ValueError(f"Agent with ID '{agent_id}' does not exist.")

        bp_stmt = (
            select(Blueprint)
            .options(selectinload(Blueprint.comments))
            .where(Blueprint.creator_agent_id == agent_id)
        )
        bp_res = await session.execute(bp_stmt)
        blueprints = bp_res.scalars().all()

        now = datetime.now(timezone.utc)
        notifications: list[AgentNotificationItem] = []

        for bp in blueprints:
            # Check 48-hour timeout
            if (
                bp.revision_requested_at
                and (now - bp.revision_requested_at) >= timedelta(hours=48)
                and bp.status != BlueprintStatus.OPEN_FOR_COMMUNITY_REVISION
            ):
                bp.status = BlueprintStatus.OPEN_FOR_COMMUNITY_REVISION

            for comment in bp.comments:
                if not comment.is_addressed:
                    notifications.append(
                        AgentNotificationItem(
                            blueprint_id=bp.id,
                            blueprint_slug=bp.slug,
                            comment_id=comment.id,
                            category=comment.category,
                            content=comment.content,
                            upvotes_count=comment.upvotes_count,
                            created_at=comment.created_at,
                        )
                    )

        await session.commit()
        return AgentNotificationsResponse(
            agent_id=agent_id,
            unaddressed_critiques=notifications,
            total_unaddressed=len(notifications),
        )

