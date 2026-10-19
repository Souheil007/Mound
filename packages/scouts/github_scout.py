"""GitHub Scout module querying GitHub Issues API for top requested features and enterprise gaps."""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from app.scouts.models import PlatformSource, RawPainSignal

logger = logging.getLogger(__name__)

GITHUB_SEARCH_URL = "https://api.github.com/search/issues"

GITHUB_SEARCH_QUERIES = [
    'is:issue is:open comments:>25 "production outage" OR "data loss" in:title,body',
    'is:issue is:open comments:>25 "cloud bill" OR "finops" OR "expensive" label:"infrastructure"',
    'is:issue is:open comments:>25 "connection pool" OR "failover deadlock" in:title,body',
    'is:issue is:open comments:>25 "soc2" OR "hipaa" OR "compliance audit" in:title,body',
    'is:issue is:open comments:>25 "schema drift" OR "cdc pipeline" in:title,body',
]


class GitHubScout:
    """Scout crawler searching GitHub for deep architectural bottlenecks with hundreds of developer reactions."""

    def __init__(self, github_token: str | None = None, timeout_seconds: float = 10.0):
        self.timeout_seconds = timeout_seconds
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "MoundScout/1.0 (+https://mound.dev; github-opportunity-detector)",
        }
        if github_token:
            headers["Authorization"] = f"Bearer {github_token}"
        self.headers = headers

    async def fetch_signals(self, limit_per_query: int = 5, window_hours: int = 2) -> list[RawPainSignal]:
        """Queries GitHub Issues search API for structural architectural gaps active within the timelapse.

        Args:
            limit_per_query: Max issues to inspect per query keyword.
            window_hours: Maximum age of activity in hours (default 2 hours).

        Returns:
            List of normalized RawPainSignal objects active within the timelapse window.
        """
        signals: list[RawPainSignal] = []
        seen_ids: set[str] = set()

        cutoff_dt = datetime.now(timezone.utc) - timedelta(hours=window_hours)

        async with httpx.AsyncClient(timeout=self.timeout_seconds, headers=self.headers) as client:
            for query in GITHUB_SEARCH_QUERIES:
                try:
                    params: dict[str, Any] = {
                        "q": query,
                        "sort": "updated",
                        "order": "desc",
                        "per_page": limit_per_query,
                    }
                    resp = await client.get(GITHUB_SEARCH_URL, params=params)
                    if resp.status_code != 200:
                        continue

                    items = resp.json().get("items", [])
                    for issue in items:
                        issue_id = str(issue.get("id"))
                        if issue_id in seen_ids:
                            continue
                        seen_ids.add(issue_id)

                        # Enforce timelapse cutoff on updated_at
                        updated_at_str = issue.get("updated_at")
                        if updated_at_str:
                            try:
                                updated_dt = datetime.fromisoformat(updated_at_str.replace("Z", "+00:00"))
                                if updated_dt < cutoff_dt:
                                    continue
                            except Exception:
                                pass

                        title = issue.get("title", "")
                        body = issue.get("body", "") or ""
                        if len(body) < 120:
                            continue

                        html_url = issue.get("html_url", "")
                        comments = issue.get("comments", 0)
                        reactions = issue.get("reactions", {}).get("total_count", 0)
                        user = issue.get("user", {}).get("login", "anonymous")

                        signals.append(
                            RawPainSignal(
                                id=f"gh_{issue_id}",
                                platform=PlatformSource.GITHUB,
                                title=title[:200],
                                content=body[:2000],
                                author=user,
                                url=html_url,
                                engagement_count=int(reactions + comments),
                                metadata={
                                    "reactions": reactions,
                                    "comments": comments,
                                    "updated_at": updated_at_str,
                                    "repository_url": issue.get("repository_url"),
                                },
                            )
                        )
                except Exception as exc:
                    logger.warning("GitHubScout query '%s' failed: %s", query, exc)
                    continue

        return signals
