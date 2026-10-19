"""Reddit Scout module polling public subreddits for developer and business workflow agony."""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from app.scouts.models import PlatformSource, RawPainSignal

logger = logging.getLogger(__name__)

TARGET_SUBREDDITS = [
    "SaaS",
    "devops",
    "sysadmin",
    "startups",
    "webdev",
]

# Keywords indicating commercial pain or willingness to pay
PAIN_KEYWORDS = [
    "expensive",
    "alternative",
    "manual",
    "pricing",
    "hate using",
    "wasting hours",
    "nightmare",
    "frustrated",
    "struggling with",
    "outage",
    "cloud bill",
    "soc2",
    "hipaa",
    "database",
]


class RedditScout:
    """Scout crawler scanning top tech and business subreddits for recurring commercial agony."""

    def __init__(self, timeout_seconds: float = 10.0):
        self.timeout_seconds = timeout_seconds
        # Custom descriptive User-Agent complying with Reddit's public API policy
        self.headers = {"User-Agent": "MoundScout/1.0 (by /u/mound_bot; opportunity-detector)"}

    async def fetch_signals(self, limit_per_sub: int = 15, window_hours: int = 2) -> list[RawPainSignal]:
        """Scrapes fresh submissions across targeted subreddits created within the timelapse window.

        Args:
            limit_per_sub: Max posts to inspect per subreddit.
            window_hours: Maximum age of posts in hours (default 2 hours).

        Returns:
            List of normalized RawPainSignal objects matching commercial pain patterns.
        """
        signals: list[RawPainSignal] = []
        seen_ids: set[str] = set()

        cutoff_utc = (datetime.now(timezone.utc) - timedelta(hours=window_hours)).timestamp()

        async with httpx.AsyncClient(timeout=self.timeout_seconds, headers=self.headers, follow_redirects=True) as client:
            for sub in TARGET_SUBREDDITS:
                # Query only "new" listing to enforce recency
                url = f"https://www.reddit.com/r/{sub}/new.json?limit={limit_per_sub}"
                try:
                    resp = await client.get(url)
                    if resp.status_code != 200:
                        continue

                    data = resp.json()
                    children = data.get("data", {}).get("children", [])

                    for post in children:
                        pdata = post.get("data", {})
                        post_id = pdata.get("id")
                        if not post_id or post_id in seen_ids:
                            continue
                        seen_ids.add(post_id)

                        # Enforce 2-hour timelapse cutoff
                        created_utc = pdata.get("created_utc", 0)
                        if created_utc < cutoff_utc:
                            continue

                        title = pdata.get("title", "")
                        selftext = pdata.get("selftext", "")
                        full_text = f"{title} {selftext}".lower()

                        # Filter for posts containing explicit pain markers
                        has_pain = any(kw in full_text for kw in PAIN_KEYWORDS)
                        if not has_pain:
                            continue

                        # Require meaningful length
                        if len(selftext) < 80:
                            continue

                        permalink = pdata.get("permalink", "")
                        post_url = f"https://www.reddit.com{permalink}" if permalink else f"https://reddit.com/r/{sub}/comments/{post_id}"
                        score = pdata.get("score", 0)
                        num_comments = pdata.get("num_comments", 0)

                        signals.append(
                            RawPainSignal(
                                id=f"reddit_{post_id}",
                                platform=PlatformSource.REDDIT,
                                title=title[:200],
                                content=selftext[:2000],
                                author=pdata.get("author", "anonymous"),
                                url=post_url,
                                engagement_count=int(score + num_comments),
                                metadata={
                                    "subreddit": sub,
                                    "upvotes": score,
                                    "comments": num_comments,
                                    "created_utc": created_utc,
                                },
                            )
                        )
                except Exception as exc:
                    logger.warning("RedditScout r/%s/new failed: %s", sub, exc)
                    continue

        return signals
