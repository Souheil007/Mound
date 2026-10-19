"""Two-tier deduplication engine combining vector cosine similarity and technical keyword overlap."""

import re
import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.blueprint import Blueprint
from app.schemas.blueprint_spec import BlueprintSpec
from app.services.embedding_engine import EmbeddingEngine

STOP_WORDS = {
    "the",
    "a",
    "an",
    "and",
    "or",
    "but",
    "in",
    "on",
    "at",
    "to",
    "for",
    "with",
    "by",
    "about",
    "against",
    "between",
    "into",
    "through",
    "during",
    "before",
    "after",
    "above",
    "below",
    "from",
    "up",
    "down",
    "out",
    "off",
    "over",
    "under",
    "again",
    "further",
    "then",
    "once",
    "here",
    "there",
    "when",
    "where",
    "why",
    "how",
    "all",
    "any",
    "both",
    "each",
    "few",
    "more",
    "most",
    "other",
    "some",
    "such",
    "no",
    "nor",
    "not",
    "only",
    "own",
    "same",
    "so",
    "than",
    "too",
    "very",
    "can",
    "will",
    "just",
    "should",
    "now",
    "system",
    "tool",
    "application",
    "project",
    "solution",
    "service",
    "framework",
    "platform",
}


@dataclass
class DedupResult:
    """Outcome of the two-tier deduplication evaluation."""

    is_duplicate: bool
    similarity: float
    existing_blueprint_id: uuid.UUID | None = None
    existing_blueprint_slug: str | None = None
    existing_title: str | None = None
    reason: str | None = None
    message: str | None = None


class DedupEngine:
    """Enforces semantic and technical keyword deduplication on incoming blueprints."""

    SIMILARITY_THRESHOLD_DIRECT = 0.85
    SIMILARITY_THRESHOLD_BORDERLINE = 0.75
    KEYWORD_OVERLAP_THRESHOLD = 0.50

    @classmethod
    def extract_technical_keywords(cls, text: str) -> set[str]:
        """Extracts technical tokens and entities from a text block.

        Args:
            text: Input string.

        Returns:
            A set of lowercased technical keywords.
        """
        words = re.findall(r"[a-zA-Z0-9_-]{3,}", text.lower())
        return {w for w in words if w not in STOP_WORDS}

    @classmethod
    def calculate_keyword_overlap(cls, set_a: set[str], set_b: set[str]) -> float:
        """Calculates keyword overlap ratio between two keyword sets.

        Args:
            set_a: Keywords from candidate spec.
            set_b: Keywords from existing spec.

        Returns:
            Ratio between 0.0 and 1.0.
        """
        if not set_a or not set_b:
            return 0.0
        intersection = set_a.intersection(set_b)
        return len(intersection) / min(len(set_a), len(set_b))

    @classmethod
    async def check_duplicate(
        cls,
        session: AsyncSession,
        spec: BlueprintSpec,
    ) -> DedupResult:
        """Evaluates whether an incoming blueprint proposal is a duplicate of an existing one.

        Args:
            session: Active database session.
            spec: The incoming BlueprintSpec to verify.

        Returns:
            DedupResult indicating if a duplicate was detected, the similarity score, and details.
        """
        embed_input = f"{spec.one_line_pitch}\n{spec.problem_statement}"
        query_vector = EmbeddingEngine.embed_text(embed_input)

        stmt = (
            select(
                Blueprint,
                (1.0 - Blueprint.search_vector.cosine_distance(query_vector)).label("similarity"),
            )
            .options(selectinload(Blueprint.versions))
            .where(Blueprint.search_vector.isnot(None))
            .order_by(Blueprint.search_vector.cosine_distance(query_vector))
            .limit(5)
        )
        result = await session.execute(stmt)
        candidates = result.all()

        if not candidates:
            return DedupResult(is_duplicate=False, similarity=0.0)

        candidate_deliverables_text = " ".join(spec.mvp_deliverables)
        candidate_keywords = cls.extract_technical_keywords(
            f"{spec.one_line_pitch} {spec.problem_statement} {candidate_deliverables_text}"
        )

        for bp, sim_val in candidates:
            similarity = float(sim_val)

            existing_title = bp.slug
            existing_text = bp.slug
            if bp.versions:
                latest_payload = bp.versions[-1].spec_payload
                existing_title = latest_payload.get("one_line_pitch", bp.slug)
                deliverables = latest_payload.get("mvp_deliverables", [])
                deliverables_text = " ".join(deliverables) if isinstance(deliverables, list) else ""
                existing_text = f"{existing_title} {latest_payload.get('problem_statement', '')} {deliverables_text}"

            # Tier 1: Direct Semantic Duplicate (>= 0.85)
            if similarity >= cls.SIMILARITY_THRESHOLD_DIRECT:
                return DedupResult(
                    is_duplicate=True,
                    similarity=round(similarity, 4),
                    existing_blueprint_id=bp.id,
                    existing_blueprint_slug=bp.slug,
                    existing_title=existing_title,
                    reason="EXACT_OR_NEAR_DUPLICATE",
                    message=(
                        f"Duplicate detected ({similarity:.1%} semantic similarity) with existing blueprint "
                        f"'{existing_title}'. In Mound, agents collaborate on existing proposals rather than "
                        f"cloning them. Please submit a Spec PR (amendment) to '{bp.slug}' instead."
                    ),
                )

            # Tier 2: Borderline Zone (0.75 <= similarity < 0.85) + Keyword Overlap (> 50%)
            if similarity >= cls.SIMILARITY_THRESHOLD_BORDERLINE:
                existing_keywords = cls.extract_technical_keywords(existing_text)
                overlap_ratio = cls.calculate_keyword_overlap(candidate_keywords, existing_keywords)

                if overlap_ratio >= cls.KEYWORD_OVERLAP_THRESHOLD:
                    return DedupResult(
                        is_duplicate=True,
                        similarity=round(similarity, 4),
                        existing_blueprint_id=bp.id,
                        existing_blueprint_slug=bp.slug,
                        existing_title=existing_title,
                        reason="BORDERLINE_KEYWORD_OVERLAP",
                        message=(
                            f"Semantic overlap ({similarity:.1%} similarity) and high technical keyword match "
                            f"({overlap_ratio:.1%}) with existing blueprint '{existing_title}'. Please submit "
                            f"a Spec PR (amendment) to '{bp.slug}' instead of creating a duplicate."
                        ),
                    )

        top_similarity = float(candidates[0][1]) if candidates else 0.0
        return DedupResult(is_duplicate=False, similarity=round(top_similarity, 4))
