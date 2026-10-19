"""Hacker News Scout module querying Algolia HN API for real-time developer complaints."""

import logging
from typing import Any

import httpx

from packages.scouts.models import PlatformSource, RawPainSignal

logger = logging.getLogger(__name__)

HN_SEARCH_URL = "https://hn.algolia.com/api/v1/search"

# Targeted queries tuned for structural business and architectural pain
SEARCH_QUERIES = [
    "Ask HN software wish existed",
    "Ask HN biggest pain point",
    "SaaS expensive alternatives",
    "hate using software",
    "manual spreadsheet hours",
    "cloud bill outrageous",
    "compliance nightmare SOC2",
]


class HNScout:
    """Scout crawler monitoring Hacker News for high-signal architectural and SaaS complaints."""

    def __init__(self, timeout_seconds: float = 10.0):
        self.timeout_seconds = timeout_seconds
        self.headers = {"User-Agent": "MoundScout/1.0 (+https://mound.dev; opportunity-detector)"}

    async def fetch_signals(self, limit_per_query: int = 5) -> list[RawPainSignal]:
        """Fetches recent viral complaints from Hacker News discussions.

        Args:
            limit_per_query: Max items to inspect per query keyword.

        Returns:
            List of normalized RawPainSignal objects.
        """
        signals: list[RawPainSignal] = []
        seen_ids: set[str] = set()

        async with httpx.AsyncClient(timeout=self.timeout_seconds, headers=self.headers) as client:
            for query in SEARCH_QUERIES:
                try:
                    params: dict[str, Any] = {
                        "query": query,
                        "tags": "(story,comment)",
                        "hitsPerPage": limit_per_query,
                    }
                    resp = await client.get(HN_SEARCH_URL, params=params)
                    if resp.status_code != 200:
                        continue

                    data = resp.json()
                    hits = data.get("hits", [])

                    for hit in hits:
                        object_id = str(hit.get("objectID"))
                        if object_id in seen_ids:
                            continue
                        seen_ids.add(object_id)

                        title = hit.get("title") or hit.get("story_title") or "Hacker News Discussion"
                        comment_text = hit.get("comment_text") or hit.get("story_text") or ""
                        points = hit.get("points") or hit.get("num_comments") or 0
                        author = hit.get("author") or "anonymous"

                        # Require minimum substantive complaint length
                        body = comment_text if comment_text else title
                        if len(body) < 100:
                            continue

                        hn_url = f"https://news.ycombinator.com/item?id={object_id}"
                        signals.append(
                            RawPainSignal(
                                id=f"hn_{object_id}",
                                platform=PlatformSource.HACKERNEWS,
                                title=title[:200],
                                content=body[:2000],
                                author=author,
                                url=hn_url,
                                engagement_count=int(points),
                                metadata={"points": points, "created_at": hit.get("created_at")},
                            )
                        )
                except Exception as exc:
                    logger.warning("HNScout query '%s' failed: %s", query, exc)
                    continue

        return signals
