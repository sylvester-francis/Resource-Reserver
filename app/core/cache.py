"""Redis caching layer for Resource-Reserver.

Provides a robust caching solution with:
- Async Redis client with connection pooling
- Graceful fallback when Redis is unavailable
- Cache decorators for common patterns
- TTL configuration per cache type
- Cache invalidation helpers

Author: Sylvester-Francis
"""

import functools
import hashlib
import json
import logging
from collections.abc import Callable
from typing import Any, TypeVar

import redis.asyncio as redis
from redis.asyncio import ConnectionPool
from redis.exceptions import RedisError

from app.config import get_settings

logger = logging.getLogger(__name__)

T = TypeVar("T")


class CacheManager:
    """Manages Redis cache connections and operations."""

    def __init__(self) -> None:
        self._pool: ConnectionPool | None = None
        self._client: redis.Redis | None = None
        self._connected: bool = False
        self._settings = get_settings()

    @property
    def enabled(self) -> bool:
        """Check if caching is enabled."""
        return self._settings.cache_enabled

    async def connect(self) -> bool:
        """Initialize Redis connection pool.

        Returns:
            True if connection successful, False otherwise.
        """
        if not self.enabled:
            logger.info("Cache disabled via configuration")
            return False

        if self._connected:
            return True

        try:
            self._pool = ConnectionPool.from_url(
                self._settings.redis_url,
                max_connections=10,
                decode_responses=True,
            )
            self._client = redis.Redis(connection_pool=self._pool)

            # Test connection
            await self._client.ping()
            self._connected = True
            logger.info("Redis cache connected successfully")
            return True

        except RedisError as e:
            logger.warning(f"Failed to connect to Redis: {e}. Caching disabled.")
            self._connected = False
            return False

    async def disconnect(self) -> None:
        """Close Redis connection pool."""
        if self._client:
            await self._client.aclose()
            self._client = None
        if self._pool:
            await self._pool.disconnect()
            self._pool = None
        self._connected = False
        logger.info("Redis cache disconnected")

    async def get(self, key: str) -> Any | None:
        """Get value from cache.

        Args:
            key: Cache key.

        Returns:
            Cached value or None if not found/error.
        """
        if not self._connected or not self._client:
            return None

        try:
            value = await self._client.get(key)
            if value:
                return json.loads(value)
            return None
        except (RedisError, json.JSONDecodeError) as e:
            logger.debug(f"Cache get error for key {key}: {e}")
            return None

    async def set(self, key: str, value: Any, ttl: int | None = None) -> bool:
        """Set value in cache.

        Args:
            key: Cache key.
            value: Value to cache (must be JSON serializable).
            ttl: Time-to-live in seconds. Uses default if not specified.

        Returns:
            True if successful, False otherwise.
        """
        if not self._connected or not self._client:
            return False

        try:
            serialized = json.dumps(value, default=str)
            if ttl:
                await self._client.setex(key, ttl, serialized)
            else:
                await self._client.set(key, serialized)
            return True
        except (RedisError, TypeError) as e:
            logger.debug(f"Cache set error for key {key}: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """Delete value from cache.

        Args:
            key: Cache key.

        Returns:
            True if deleted, False otherwise.
        """
        if not self._connected or not self._client:
            return False

        try:
            await self._client.delete(key)
            return True
        except RedisError as e:
            logger.debug(f"Cache delete error for key {key}: {e}")
            return False

    async def delete_pattern(self, pattern: str) -> int:
        """Delete all keys matching pattern.

        Args:
            pattern: Redis key pattern (e.g., 'resources:*').

        Returns:
            Number of keys deleted.
        """
        if not self._connected or not self._client:
            return 0

        try:
            keys = []
            async for key in self._client.scan_iter(match=pattern):
                keys.append(key)

            if keys:
                deleted = await self._client.delete(*keys)
                logger.debug(f"Deleted {deleted} keys matching pattern: {pattern}")
                return deleted
            return 0
        except RedisError as e:
            logger.debug(f"Cache delete_pattern error for {pattern}: {e}")
            return 0

    async def exists(self, key: str) -> bool:
        """Check if key exists in cache.

        Args:
            key: Cache key.

        Returns:
            True if exists, False otherwise.
        """
        if not self._connected or not self._client:
            return False

        try:
            return await self._client.exists(key) > 0
        except RedisError:
            return False

    async def incr(self, key: str, ttl: int | None = None) -> int | None:
        """Increment counter in cache.

        Args:
            key: Cache key.
            ttl: Set TTL if this is a new key.

        Returns:
            New counter value or None on error.
        """
        if not self._connected or not self._client:
            return None

        try:
            value = await self._client.incr(key)
            if ttl and value == 1:  # First increment, set TTL
                await self._client.expire(key, ttl)
            return value
        except RedisError as e:
            logger.debug(f"Cache incr error for key {key}: {e}")
            return None

    def is_connected(self) -> bool:
        """Check if Redis is connected."""
        return self._connected


# Global cache manager instance
cache_manager = CacheManager()


def _make_cache_key(prefix: str, *args: Any, **kwargs: Any) -> str:
    """Generate a cache key from prefix and arguments.

    Args:
        prefix: Key prefix (e.g., 'resources', 'stats').
        *args: Positional arguments to include in key.
        **kwargs: Keyword arguments to include in key.

    Returns:
        Cache key string.
    """
    key_parts = [prefix]

    for arg in args:
        if arg is not None:
            key_parts.append(str(arg))

    for k, v in sorted(kwargs.items()):
        if v is not None:
            key_parts.append(f"{k}={v}")

    key_data = ":".join(key_parts)

    # Use hash for long keys (not for security, just for shortening)
    if len(key_data) > 200:
        key_hash = hashlib.md5(key_data.encode(), usedforsecurity=False).hexdigest()[
            :16
        ]
        return f"{prefix}:{key_hash}"

    return key_data


def cached(
    prefix: str,
    ttl: int | None = None,
    key_builder: Callable[..., str] | None = None,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator to cache function results.

    Args:
        prefix: Cache key prefix.
        ttl: Time-to-live in seconds.
        key_builder: Optional custom function to build cache key.

    Returns:
        Decorated function with caching.

    Example:
        @cached("resources", ttl=30)
        async def get_resources(status: str):
            return await db.query(...)
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            # Skip cache if disabled
            if not cache_manager.is_connected():
                return await func(*args, **kwargs)

            # Build cache key
            if key_builder:
                cache_key = key_builder(*args, **kwargs)
            else:
                # Skip 'self' or 'db' arguments for key
                filtered_args = []
                for arg in args:
                    if not hasattr(arg, "__dict__"):  # Skip objects
                        filtered_args.append(arg)
                cache_key = _make_cache_key(prefix, *filtered_args, **kwargs)

            # Try to get from cache
            cached_value = await cache_manager.get(cache_key)
            if cached_value is not None:
                logger.debug(f"Cache hit: {cache_key}")
                return cached_value

            # Call function and cache result
            result = await func(*args, **kwargs)

            if result is not None:
                effective_ttl = ttl or get_settings().cache_ttl_resources
                await cache_manager.set(cache_key, result, effective_ttl)
                logger.debug(f"Cache set: {cache_key} (TTL: {effective_ttl}s)")

            return result

        return wrapper

    return decorator


async def invalidate_cache(pattern: str) -> int:
    """Invalidate cache entries matching pattern.

    Args:
        pattern: Redis key pattern (e.g., 'resources:*').

    Returns:
        Number of keys invalidated.
    """
    return await cache_manager.delete_pattern(pattern)


# Cache key prefixes
class CacheKeys:
    """Standard cache key prefixes."""

    RESOURCES = "resources"
    RESOURCES_LIST = "resources:list"
    RESOURCES_SEARCH = "resources:search"
    RESOURCE_AVAILABILITY = "resources:availability"
    STATS = "stats"
    USER_SESSION = "user:session"
    DASHBOARD = "dashboard"


# Convenience functions for common cache operations
async def cache_resource_list(
    key_suffix: str, data: list[dict[str, Any]], ttl: int | None = None
) -> bool:
    """Cache a resource list result.

    Args:
        key_suffix: Suffix for the cache key.
        data: List of resource dictionaries.
        ttl: Time-to-live in seconds.

    Returns:
        True if cached successfully.
    """
    settings = get_settings()
    cache_key = f"{CacheKeys.RESOURCES_LIST}:{key_suffix}"
    return await cache_manager.set(cache_key, data, ttl or settings.cache_ttl_resources)


async def get_cached_resource_list(key_suffix: str) -> list[dict[str, Any]] | None:
    """Get cached resource list.

    Args:
        key_suffix: Suffix for the cache key.

    Returns:
        Cached list or None.
    """
    cache_key = f"{CacheKeys.RESOURCES_LIST}:{key_suffix}"
    return await cache_manager.get(cache_key)


async def invalidate_resource_cache() -> int:
    """Invalidate all resource-related caches.

    Returns:
        Number of keys invalidated.
    """
    count = 0
    count += await cache_manager.delete_pattern(f"{CacheKeys.RESOURCES}:*")
    count += await cache_manager.delete_pattern(f"{CacheKeys.DASHBOARD}:*")
    logger.info(f"Invalidated {count} resource cache entries")
    return count


async def cache_stats(key: str, data: dict[str, Any], ttl: int | None = None) -> bool:
    """Cache dashboard/statistics data.

    Args:
        key: Stats cache key.
        data: Statistics dictionary.
        ttl: Time-to-live in seconds.

    Returns:
        True if cached successfully.
    """
    settings = get_settings()
    cache_key = f"{CacheKeys.STATS}:{key}"
    return await cache_manager.set(cache_key, data, ttl or settings.cache_ttl_stats)


async def get_cached_stats(key: str) -> dict[str, Any] | None:
    """Get cached statistics.

    Args:
        key: Stats cache key.

    Returns:
        Cached stats or None.
    """
    cache_key = f"{CacheKeys.STATS}:{key}"
    return await cache_manager.get(cache_key)
