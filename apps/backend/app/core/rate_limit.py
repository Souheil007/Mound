"""Sliding-window token bucket rate limiter powered by Redis."""

import time
import uuid

import redis.asyncio as aioredis
from fastapi import HTTPException, status

from app.core.config import settings

_pool: aioredis.ConnectionPool | None = None


def get_redis_client() -> aioredis.Redis:
    """Returns an async Redis client backed by a connection pool.

    Returns:
        An aioredis.Redis client instance.
    """
    global _pool
    if _pool is None:
        _pool = aioredis.ConnectionPool.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
    return aioredis.Redis(connection_pool=_pool)


async def close_redis() -> None:
    """Closes and resets the global Redis connection pool."""
    global _pool
    if _pool is not None:
        await _pool.disconnect()
        _pool = None


# Sliding window rate limiter in Lua:
# Keys: [rate_limit_key]
# Args: [current_timestamp, window_seconds, max_limit]
SLIDING_WINDOW_LUA = """
local key = KEYS[1]
local now = tonumber(ARGV[1])
local window = tonumber(ARGV[2])
local limit = tonumber(ARGV[3])

local clear_before = now - window
redis.call('ZREMRANGEBYSCORE', key, 0, clear_before)

local current_count = redis.call('ZCARD', key)

if current_count < limit then
    redis.call('ZADD', key, now, tostring(now) .. '-' .. tostring(math.random(1000, 9999)))
    redis.call('EXPIRE', key, window)
    return {1, limit - current_count - 1, 0}
else
    local oldest = redis.call('ZRANGE', key, 0, 0, 'WITHSCORES')
    local reset_after = 0
    if #oldest > 0 then
        reset_after = math.ceil(tonumber(oldest[2]) + window - now)
    else
        reset_after = window
    end
    if reset_after < 0 then reset_after = 0 end
    return {0, 0, reset_after}
end
"""


class RateLimiter:
    """Enforces sliding-window rate limits per agent using Redis sorted sets."""

    @classmethod
    async def check_rate_limit(
        cls,
        agent_id: uuid.UUID,
        action: str,
        limit: int,
        window_seconds: int = 86400,
    ) -> dict[str, int]:
        """Checks and records an action attempt under the sliding window rate limit.

        Args:
            agent_id: UUID of the agent performing the action.
            action: Action identifier (e.g., 'proposals', 'amendments').
            limit: Maximum allowed attempts in the sliding window.
            window_seconds: Duration of the sliding window in seconds (default 86400 = 24h).

        Returns:
            A dict with limit, remaining, and reset_after_seconds.

        Raises:
            HTTPException: 429 Too Many Requests if the limit is exceeded.
        """
        if not settings.rate_limit_enabled:
            return {"limit": limit, "remaining": limit - 1, "reset_after_seconds": 0}

        r = get_redis_client()
        key = f"mound:ratelimit:{agent_id}:{action}"
        now = time.time()

        result = await r.eval(
            SLIDING_WINDOW_LUA,
            1,
            key,
            now,
            window_seconds,
            limit,
        )

        allowed = bool(result[0])
        remaining = int(result[1])
        reset_after = int(result[2])

        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded for '{action}'. Limit is {limit} per {window_seconds // 3600} hours.",
                headers={
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(now + reset_after)),
                    "Retry-After": str(reset_after),
                },
            )

        return {
            "limit": limit,
            "remaining": remaining,
            "reset_after_seconds": reset_after,
        }

    @classmethod
    async def check_user_rate_limit(
        cls,
        user_id: uuid.UUID,
        action: str,
        limit: int,
        window_seconds: int = 300,
    ) -> dict[str, int]:
        """Enforces rate limiting per human developer user (e.g. for agent creation).

        Args:
            user_id: UUID of the developer.
            action: Action identifier (e.g., 'agent_register').
            limit: Maximum attempts allowed within the sliding window.
            window_seconds: Duration of the sliding window in seconds (default 300 = 5m).

        Returns:
            Dict with limit, remaining, and reset_after_seconds.

        Raises:
            HTTPException: 429 Too Many Requests if the limit is exceeded.
        """
        if not settings.rate_limit_enabled:
            return {"limit": limit, "remaining": limit - 1, "reset_after_seconds": 0}

        r = get_redis_client()
        key = f"mound:ratelimit:user:{user_id}:{action}"
        now = time.time()

        result = await r.eval(
            SLIDING_WINDOW_LUA,
            1,
            key,
            now,
            window_seconds,
            limit,
        )

        allowed = bool(result[0])
        remaining = int(result[1])
        reset_after = int(result[2])

        if not allowed:
            if action == "proposals":
                detail_msg = f"Daily proposal quota exceeded ({limit} per 24 hours). Please wait {max(1, reset_after // 3600)} hour(s) before submitting another proposal."
            else:
                detail_msg = f"Registration velocity limit exceeded. Please wait {reset_after} seconds before connecting another agent."
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=detail_msg,
                headers={
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(now + reset_after)),
                    "Retry-After": str(reset_after),
                },
            )

        return {
            "limit": limit,
            "remaining": remaining,
            "reset_after_seconds": reset_after,
        }

    @classmethod
    async def get_user_rate_limit_usage(
        cls,
        user_id: uuid.UUID,
        action: str,
        window_seconds: int = 86400,
    ) -> int:
        """Returns the current number of events recorded in the sliding window for a user."""
        if not settings.rate_limit_enabled:
            return 0
        try:
            r = get_redis_client()
            key = f"mound:ratelimit:user:{user_id}:{action}"
            now = time.time()
            clear_before = now - window_seconds
            await r.zremrangebyscore(key, 0, clear_before)
            count = await r.zcard(key)
            return int(count or 0)
        except Exception:
            return 0
