"""Scout Swarm live sweep runner script."""

import asyncio
import json
import logging
import sys

from app.workers.scout_orchestrator import ScoutOrchestrator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("scout_sweep")


async def main():
    logger.info("Initializing Scout Swarm Orchestrator...")
    orchestrator = ScoutOrchestrator()

    logger.info("Triggering comprehensive live scout cycle (window_hours=72)...")
    res = await orchestrator.run_scout_cycle(window_hours=72)

    logger.info("Scout sweep completed successfully!")
    print("\n" + "=" * 80)
    print("SCOUT SWARM LIVE SWEEP EXECUTION SUMMARY")
    print("=" * 80)
    print(f"Total Signals Scraped:       {res.get('signals_scraped', 0)}")
    print(f"Opportunities Qualified:     {res.get('opportunities_qualified', 0)}")
    print(f"Blueprints Created & Saved:  {len(res.get('blueprints_published', []))}")
    print("=" * 80)

    if res.get("blueprints_published"):
        print("\n--- PUBLISHED BLUEPRINTS ---")
        for i, bp in enumerate(res["blueprints_published"], 1):
            print(f"\n[{i}] {bp.get('title')}")
            print(f"    - Platform:    {bp.get('platform')}")
            print(f"    - Scout Agent: {bp.get('scout_agent')}")
            print(f"    - Score:       {bp.get('score')}/100")
            print(f"    - Blueprint:   {bp.get('slug')} (ID: {bp.get('blueprint_id')})")
            print(f"    - Source URL:  {bp.get('source_url')}")
    else:
        print("\nNo blueprints published in this pass.")

    print("\n" + json.dumps(res, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
