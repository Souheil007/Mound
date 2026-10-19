"""GitHub Scout module querying GitHub Issues API for top requested features and enterprise gaps."""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from app.scouts.models import PlatformSource, RawPainSignal

logger = logging.getLogger(__name__)

GITHUB_SEARCH_URL = "https://api.github.com/search/issues"

GITHUB_SEARCH_QUERIES = [
    'is:issue is:open comments:>5 "production outage" OR "data loss" in:title,body',
    'is:issue is:open comments:>5 "cloud bill" OR "finops" OR "expensive" label:"infrastructure"',
    'is:issue is:open comments:>5 "connection pool" OR "failover deadlock" in:title,body',
    'is:issue is:open comments:>5 "soc2" OR "hipaa" OR "compliance audit" in:title,body',
    'is:issue is:open comments:>5 "schema drift" OR "cdc pipeline" in:title,body',
]


class GitHubScout:
    """Scout crawler searching GitHub for deep architectural bottlenecks with community discussion."""

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
        """Queries GitHub Issues search API for structural architectural gaps and recent discussion comments.

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
                        html_url = issue.get("html_url", "")
                        comments_count = issue.get("comments", 0)
                        reactions = issue.get("reactions", {}).get("total_count", 0)
                        user = issue.get("user", {}).get("login", "anonymous")

                        # 1. Ingest Main Issue Post if substantive
                        if len(body) >= 100:
                            signals.append(
                                RawPainSignal(
                                    id=f"gh_issue_{issue_id}",
                                    platform=PlatformSource.GITHUB,
                                    title=title[:200],
                                    content=body[:2000],
                                    author=user,
                                    url=html_url,
                                    engagement_count=int(reactions + comments_count),
                                    metadata={
                                        "type": "issue_post",
                                        "reactions": reactions,
                                        "comments": comments_count,
                                        "updated_at": updated_at_str,
                                        "repository_url": issue.get("repository_url"),
                                    },
                                )
                            )

                        # 2. Ingest Latest Comments under this actively updated issue
                        comments_url = issue.get("comments_url")
                        if comments_count > 0 and comments_url:
                            try:
                                c_resp = await client.get(f"{comments_url}?per_page=2&sort=created&direction=desc")
                                if c_resp.status_code == 200:
                                    for c_data in c_resp.json():
                                        c_id = str(c_data.get("id"))
                                        if c_id in seen_ids:
                                            continue
                                        seen_ids.add(c_id)

                                        c_body = c_data.get("body", "") or ""
                                        c_author = c_data.get("user", {}).get("login", "anonymous")
                                        c_url = c_data.get("html_url") or html_url

                                        # Skip automated bot comments or trivial one-liners
                                        if len(c_body) < 100 or "[bot]" in c_author:
                                            continue

                                        signals.append(
                                            RawPainSignal(
                                                id=f"gh_comment_{c_id}",
                                                platform=PlatformSource.GITHUB,
                                                title=f"Re: {title[:160]}",
                                                content=c_body[:2000],
                                                author=c_author,
                                                url=c_url,
                                                engagement_count=int(reactions + comments_count),
                                                metadata={
                                                    "type": "issue_comment",
                                                    "parent_issue": html_url,
                                                    "created_at": c_data.get("created_at"),
                                                },
                                            )
                                        )
                            except Exception as c_exc:
                                logger.debug("Failed to fetch comments for issue %s: %s", issue_id, c_exc)

                except Exception as exc:
                    logger.warning("GitHubScout query '%s' failed: %s", query, exc)
                    continue

        return signals
