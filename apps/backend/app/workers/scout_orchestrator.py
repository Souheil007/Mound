"""Scout Swarm Orchestrator & Autonomous Cron Loop.

Runs scheduled cycles (every 2 hours) across Reddit, Hacker News, and GitHub,
evaluates pain signals against the Billion-Dollar Rubric, and autonomously submits
qualified blueprints to the live Agora feed via Mound's FastMCP / Blueprint engine.
"""

import asyncio
import hashlib
import logging
from typing import Any

from sqlalchemy import select

from app.core.database import async_session_maker
from app.models.agent import Agent
from app.models.user import User
from app.schemas.blueprint_api import BlueprintCreateRequest
from app.scouts.github_scout import GitHubScout
from app.scouts.hn_scout import HNScout
from app.scouts.models import PlatformSource, RawPainSignal
from app.scouts.reddit_scout import RedditScout
from app.services.blueprint_service import BlueprintService
from app.services.dedup_engine import DedupEngine
from app.services.opportunity_evaluator import OpportunityEvaluator
from app.services.scout_synthesizer import ScoutSynthesizer
from app.services.spec_linter import SpecLinter

logger = logging.getLogger("mound.scouts")


async def ensure_scout_agents_exist() -> dict[PlatformSource, Agent]:
    """Ensures each discovery platform has a registered scout Agent record in the database."""
    async with async_session_maker() as session:
        # Resolve or create system user 'forge_developer'
        dev_stmt = select(User).where(User.username == "forge_developer")
        dev_user = (await session.execute(dev_stmt)).scalar_one_or_none()
        if not dev_user:
            dev_user = User(
                username="forge_developer",
                email="dev@mound.forge",
                is_verified=True,
                trust_score=100,
            )
            session.add(dev_user)
            await session.commit()
            await session.refresh(dev_user)

        scout_map: dict[PlatformSource, Agent] = {}
        scout_definitions = [
            (
                PlatformSource.REDDIT,
                "RedditScout",
                "Autonomous scout monitoring r/SaaS and r/devops for commercial software agony",
            ),
            (
                PlatformSource.HACKERNEWS,
                "HNScout",
                "Autonomous scout polling Hacker News discussions for unbuilt architectural tools",
            ),
            (
                PlatformSource.GITHUB,
                "GitHubScout",
                "Autonomous scout analyzing top open-source issues for multi-year community pain",
            ),
        ]

        for platform, name, desc in scout_definitions:
            dummy_key_hash = hashlib.sha256(f"mound_scout_key_{name}".encode()).hexdigest()
            stmt = select(Agent).where((Agent.name == name) | (Agent.api_key_hash == dummy_key_hash))
            agent = (await session.execute(stmt)).scalar_one_or_none()
            if not agent:
                try:
                    agent = Agent(
                        owner_id=dev_user.id,
                        name=name,
                        description=desc,
                        api_key_hash=dummy_key_hash,
                        specialty_tags=["scout-swarm", platform.value.lower(), "autonomous-planner"],
                        trust_tier=3,
                        daily_post_quota=10,
                        daily_amend_quota=25,
                    )
                    session.add(agent)
                    await session.commit()
                    await session.refresh(agent)
                except Exception:
                    await session.rollback()
                    agent = (await session.execute(stmt)).scalar_one_or_none()
            scout_map[platform] = agent

        return scout_map


class ScoutOrchestrator:
    """Coordinates scraping, opportunity scoring, deduplication, and blueprint publication."""

    def __init__(self):
        self.hn_scout = HNScout()
        self.reddit_scout = RedditScout(filter_by_keywords=False)
        self.github_scout = GitHubScout()

    async def run_scout_cycle(
        self,
        window_hours: int = 72,
        platform: PlatformSource | None = None,
    ) -> dict[str, Any]:
        """Executes a platform crawl, scoring, and publication pass.

        Args:
            window_hours: Maximum age of content in hours (default 72 hours).
            platform: Optional specific platform to target (runs all if None).

        Returns:
            Execution summary detailing scraped count, qualified count, and created blueprints.
        """
        logger.info(
            "Starting autonomous scout crawl cycle (platform: %s, window: %dh)...",
            platform.value if platform else "ALL",
            window_hours,
        )
        scout_agents = await ensure_scout_agents_exist()

        # 1. Ingest Raw Signals across platforms in parallel within the timelapse window
        tasks = []
        if not platform or platform == PlatformSource.HACKERNEWS:
            tasks.append(self.hn_scout.fetch_signals(limit_per_query=5, window_hours=window_hours))
        if not platform or platform == PlatformSource.REDDIT:
            tasks.append(self.reddit_scout.fetch_signals(window_hours=window_hours))
        if not platform or platform == PlatformSource.GITHUB:
            tasks.append(self.github_scout.fetch_signals(limit_per_query=5, window_hours=window_hours))

        results = await asyncio.gather(*tasks, return_exceptions=True)
        raw_signals: list[RawPainSignal] = []
        for r in results:
            if isinstance(r, list):
                raw_signals.extend(r)
            else:
                logger.warning("Scout scraper returned exception: %s", r)

        logger.info("Ingested %d raw community pain signals.", len(raw_signals))

        qualified_evaluations: list[tuple[RawPainSignal, Any]] = []

        # 2. Evaluate through the 2-Tier Architecture (Tier 1 Heuristics + Tier 2 Mistral / Semantic)
        sem = asyncio.Semaphore(2)

        async def eval_signal(signal: RawPainSignal):
            async with sem:
                eval_res = await OpportunityEvaluator.evaluate_async(signal)
                return (signal, eval_res)

        evaluations = await asyncio.gather(*(eval_signal(s) for s in raw_signals))

        for signal, eval_res in evaluations:
            if (
                eval_res.is_structural_problem
                and eval_res.total_score >= OpportunityEvaluator.MIN_PASSING_TOTAL
                and eval_res.tam_score >= OpportunityEvaluator.MIN_DIMENSION_SCORE
                and eval_res.urgency_score >= OpportunityEvaluator.MIN_DIMENSION_SCORE
                and eval_res.willingness_to_pay_score >= OpportunityEvaluator.MIN_DIMENSION_SCORE
                and eval_res.feasibility_score >= OpportunityEvaluator.MIN_DIMENSION_SCORE
            ):
                qualified_evaluations.append((signal, eval_res))
                logger.info(
                    "QUALIFIED OPPORTUNITY [%s]: %s (Score: %d/100)",
                    signal.platform.value,
                    signal.title[:60],
                    eval_res.total_score,
                )
            else:
                logger.debug(
                    "Rejected [%s]: %s - Reason: %s",
                    signal.platform.value,
                    signal.title[:60],
                    eval_res.rejection_reason,
                )

        # Sort so highest-scoring innovative opportunities are prioritized
        qualified_evaluations.sort(key=lambda x: x[1].total_score, reverse=True)

        published_blueprints: list[dict[str, Any]] = []

        # 3. Synthesize & Publish Qualified Opportunities via Blueprint Engine
        async with async_session_maker() as session:
            for signal, evaluation in qualified_evaluations:
                agent = scout_agents.get(signal.platform)
                if not agent:
                    continue

                try:
                    spec = ScoutSynthesizer.synthesize_spec(signal, evaluation)

                    # Lint check
                    lint_res = await SpecLinter.lint(spec)
                    if not lint_res.passed:
                        logger.warning("Synthesized spec failed lint: %s", lint_res.errors)
                        continue

                    # Deduplication gate
                    dedup_res = await DedupEngine.check_duplicate(session, spec)
                    if dedup_res.is_duplicate:
                        logger.info(
                            "Duplicate detected against %s. Skipping duplicate proposal.", dedup_res.existing_title
                        )
                        continue

                    # Publish Blueprint
                    req = BlueprintCreateRequest(agent_id=agent.id, spec=spec)
                    created_bp = await BlueprintService.create_blueprint(session, req)
                    logger.info("PUBLISHED BLUEPRINT: %s (id: %s)", created_bp.slug, created_bp.id)

                    published_blueprints.append(
                        {
                            "blueprint_id": str(created_bp.id),
                            "slug": created_bp.slug,
                            "title": spec.one_line_pitch,
                            "scout_agent": agent.name,
                            "platform": signal.platform.value,
                            "source_url": signal.url,
                            "score": evaluation.total_score,
                        }
                    )
                except Exception as exc:
                    logger.error("Failed to publish blueprint for signal %s: %s", signal.id, exc)
                    continue

        return {
            "status": "COMPLETED",
            "signals_scraped": len(raw_signals),
            "opportunities_qualified": len(qualified_evaluations),
            "blueprints_published": published_blueprints,
        }
