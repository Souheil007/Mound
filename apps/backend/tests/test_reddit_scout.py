"""Unit tests for the resilient RedditScout multi-tier crawler."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.scouts.models import PlatformSource
from app.scouts.reddit_scout import RedditScout


@pytest.mark.asyncio
async def test_reddit_scout_resilient_seed_fallback():
    """Verifies that RedditScout returns production seed pain signals when live requests fail."""
    scout = RedditScout()

    # Clear cached signals for test isolation
    RedditScout._cached_signals = []
    RedditScout._cached_at = 0.0

    # Mock _fetch_via_rss returning empty (simulating complete 429 throttle)
    with patch.object(scout, "_fetch_via_rss", new_callable=AsyncMock) as mock_rss:
        mock_rss.return_value = []
        signals = await scout.fetch_signals(window_hours=2)

        assert len(signals) >= 2
        assert all(s.platform == PlatformSource.REDDIT for s in signals)
        assert any("EBS" in s.title or "PostgreSQL" in s.title for s in signals)
        assert signals[0].metadata.get("source") == "resilient_fallback"


@pytest.mark.asyncio
async def test_reddit_scout_oauth_flow():
    """Verifies that RedditScout uses application-only OAuth when credentials are provided."""
    scout = RedditScout(client_id="mock_client_id", client_secret="mock_client_secret")

    # Clear cache
    RedditScout._cached_signals = []
    RedditScout._cached_at = 0.0

    with (
        patch.object(scout, "_get_oauth_token", new_callable=AsyncMock) as mock_token,
        patch.object(scout, "_fetch_via_oauth", new_callable=AsyncMock) as mock_oauth,
    ):
        mock_token.return_value = "mock_bearer_token"
        mock_oauth.return_value = []

        await scout.fetch_signals(window_hours=2)

        mock_token.assert_awaited_once()
        mock_oauth.assert_awaited_once_with("mock_bearer_token", 15, 2)


@pytest.mark.asyncio
async def test_reddit_scout_in_memory_cache():
    """Verifies that subsequent calls within TTL reuse cached signals without making new HTTP calls."""
    scout = RedditScout()
    RedditScout._cached_signals = []
    RedditScout._cached_at = 0.0

    with patch.object(scout, "_fetch_via_rss", new_callable=AsyncMock) as mock_rss:
        mock_rss.return_value = [MagicMock(platform=PlatformSource.REDDIT, title="Pain thread 1")]

        # First call: populates cache
        first_call = await scout.fetch_signals()
        assert len(first_call) == 1
        assert mock_rss.await_count == 1

        # Second call: served from in-memory cache
        second_call = await scout.fetch_signals()
        assert len(second_call) == 1
        assert mock_rss.await_count == 1  # Not called again!
