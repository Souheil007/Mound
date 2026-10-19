"""GitHub Scout module querying GitHub Issues API for top requested features and enterprise gaps."""

import logging
from typing import Any

import httpx

from packages.scouts.models import PlatformSource, RawPainSignal

logger = logging.getLogger(__name__)

GITHUB_SEARCH_URL = "https://api.github.com/search/issues"

# Targeted GitHub search queries focusing on unresolved, heavily reacted feature requests and architectural gaps
GITHUB_SEARCH_QUERIES = [
    'is:issue is:open comments:>20 "out of scope" label:"feature-request"',
    'is:issue is:open reactions:>50 "pain" label:"enhancement"',
    'is:issue is:open comments:>30 "expensive" in:title,body',
    'is:issue is:open reactions:>100 "workaround" in:title,body',
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

    async def fetch_signals(self, limit_per_query: int = 5) -> list[RawPainSignal]:
        """Queries GitHub Issues search API for structural architectural gaps.

        Args:
            limit_per_query: Max issues to inspect per query keyword.

        Returns:
            List of normalized RawPainSignal objects.
        """
        signals: list[RawPainSignal] = []
        seen_ids: set[str] = set()

        async with httpx.AsyncClient(timeout=self.timeout_seconds, headers=self.headers) as client:
            for query in GITHUB_SEARCH_QUERIES:
                try:
                    params: dict[str, Any] = {
                        "q": query,
                        "sort": "reactions",
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
                                    "repository_url": issue.get("repository_url"),
                                },
                            )
                        )
                except Exception as exc:
                    logger.warning("GitHubScout query '%s' failed: %s", query, exc)
                    continue

        return signals
