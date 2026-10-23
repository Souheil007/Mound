"""Inspects raw signals specifically from r/SideProject and r/microSaaS, evaluating them
and identifying potentially great ideas that were either qualified or disqualified.
"""

import asyncio
import json
import logging
import sys

from app.scouts.models import PlatformSource, RawPainSignal
from app.scouts.reddit_scout import RedditScout
from app.services.opportunity_evaluator import OpportunityEvaluator

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("sideproject_inspector")


async def main():
    logger.info("Initializing RedditScout targeted specifically at r/SideProject and r/microSaaS...")
    scout = RedditScout(
        target_subreddits=["SideProject", "microSaaS"],
        filter_by_keywords=False,
        two_pass_staggered=False,
    )

    logger.info("Fetching signals from Reddit...")
    # Fetch signals with window_hours=72
    signals = await scout.fetch_signals(window_hours=72)
    logger.info("Fetched %d raw signals from Reddit.", len(signals))

    # Filter to specifically SideProject and microSaaS
    sideproject_signals = [s for s in signals if "sideproject" in s.url.lower() or "microsaas" in s.url.lower()]
    logger.info("Found %d signals specifically from r/SideProject or r/microSaaS.", len(sideproject_signals))

    evaluated_records = []
    sem = asyncio.Semaphore(3)

    async def evaluate_single(s):
        t1_disqualify = OpportunityEvaluator.check_tier1_disqualification(s)
        if t1_disqualify is not None:
            return {
                "signal_id": s.id,
                "title": s.title,
                "author": s.author,
                "url": s.url,
                "content_preview": s.content[:300],
                "tier1_status": "DISQUALIFIED",
                "tier1_reason": t1_disqualify.rejection_reason,
                "total_score": t1_disqualify.total_score,
                "is_qualified": False,
            }

        async with sem:
            try:
                eval_res = await OpportunityEvaluator.evaluate_async(s)
                is_qualified = (
                    eval_res.is_structural_problem
                    and eval_res.total_score >= OpportunityEvaluator.MIN_PASSING_TOTAL
                    and eval_res.tam_score >= OpportunityEvaluator.MIN_DIMENSION_SCORE
                    and eval_res.urgency_score >= OpportunityEvaluator.MIN_DIMENSION_SCORE
                    and eval_res.willingness_to_pay_score >= OpportunityEvaluator.MIN_DIMENSION_SCORE
                    and eval_res.feasibility_score >= OpportunityEvaluator.MIN_DIMENSION_SCORE
                )
                return {
                    "signal_id": s.id,
                    "title": s.title,
                    "author": s.author,
                    "url": s.url,
                    "content_preview": s.content[:300],
                    "tier1_status": "PASSED",
                    "total_score": eval_res.total_score,
                    "tam": eval_res.tam_score,
                    "urgency": eval_res.urgency_score,
                    "wtp": eval_res.willingness_to_pay_score,
                    "feasibility": eval_res.feasibility_score,
                    "proposed_project_name": eval_res.proposed_project_name,
                    "project_type": eval_res.project_type,
                    "mvp_scope": eval_res.mvp_scope,
                    "pitch": eval_res.suggested_pitch,
                    "rationale": eval_res.rationale,
                    "rejection_reason": eval_res.rejection_reason,
                    "is_qualified": is_qualified,
                }
            except Exception as e:
                logger.error("Error evaluating signal %s: %s", s.id, e)
                return {
                    "signal_id": s.id,
                    "title": s.title,
                    "author": s.author,
                    "url": s.url,
                    "content_preview": s.content[:300],
                    "tier1_status": "ERROR",
                    "error": str(e),
                    "is_qualified": False,
                }

    logger.info("Evaluating %d signals with Tier 2 LLM...", len(sideproject_signals))
    evaluated_records = await asyncio.gather(*(evaluate_single(s) for s in sideproject_signals))

    output_path = "scratch/sideproject_analysis.json"
    import os

    os.makedirs("scratch", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(evaluated_records, f, indent=2)

    logger.info("Saved %d evaluated records to %s", len(evaluated_records), output_path)

    # Print summary
    qualified = [r for r in evaluated_records if r["is_qualified"]]
    tier1_dropped = [r for r in evaluated_records if r["tier1_status"] == "DISQUALIFIED"]
    tier2_dropped = [r for r in evaluated_records if r["tier1_status"] == "PASSED" and not r["is_qualified"]]

    print("\n" + "=" * 80)
    print("r/SideProject & r/microSaaS Analysis Summary")
    print("=" * 80)
    print(f"Total Posts Inspected: {len(evaluated_records)}")
    print(f"Tier 1 Disqualified:   {len(tier1_dropped)}")
    print(f"Tier 2 Disqualified:   {len(tier2_dropped)}")
    print(f"Qualified as Ideas:    {len(qualified)}")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
