"""Redis caching layer for Resource-Reserver.

This module provides a robust, production-ready caching solution built on top of
Redis. It is designed to improve application performance by reducing database
load and providing fast access to frequently requested data.

Features:
    - Async Redis client with connection pooling for efficient resource usage
    - Graceful fallback when Redis is unavailable (fail-open design)
    - Cache decorators for common patterns with automatic key generation
    - Configurable TTL (Time-To-Live) per cache type
    - Pattern-based cache invalidation helpers
    - Thread-safe singleton cache manager instance
    - JSON serialization for complex data types

Example Usage:
    Basic cache operations::

        from app.core.cache import cache_manager

        # Initialize connection (typically done at app startup)
        await cache_manager.connect()

        # Store and retrieve values
        await cache_manager.set("my_key", {"data": "value"}, ttl=300)
        result = await cache_manager.get("my_key")

        # Delete specific keys or patterns
        await cache_manager.delete("my_key")
        await cache_manager.delete_pattern("resources:*")

    Using the cache decorator::

        from app.core.cache import cached, CacheKeys

        @cached(CacheKeys.RESOURCES, ttl=60)
        async def get_resource(resource_id: int):
            return await db.fetch_resource(resource_id)

    Convenience functions for common operations::

        from app.core.cache import (
            cache_resource_list,
            get_cached_resource_list,
            invalidate_resource_cache,
        )

        # Cache a list of resources
        await cache_resource_list("active", resources_data)

        # Retrieve cached resources
        cached_data = await get_cached_resource_list("active")

        # Invalidate all resource caches
        await invalidate_resource_cache()

Author:
    Sylvester-Francis
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
    """Manages Redis cache connections and operations.

    This class provides a centralized interface for all Redis cache operations.
    It handles connection management, serialization/deserialization, and provides
    a consistent API for cache operations with built-in error handling.

    The manager is designed to fail gracefully when Redis is unavailable,
    returning None or False for operations rather than raising exceptions.
    This ensures the application continues to function even without caching.

    Attributes:
        _pool: Redis connection pool for efficient connection reuse.
        _client: Redis async client instance.
        _connected: Boolean flag indicating current connection status.
        _settings: Application settings containing Redis configuration.

    Example:
        Typical usage in an application::

            manager = CacheManager()
            await manager.connect()

            # Perform cache operations
            await manager.set("key", {"data": "value"}, ttl=300)
            value = await manager.get("key")

            # Clean up on shutdown
            await manager.disconnect()
    """

    def __init__(self) -> None:
        """Initialize the CacheManager with default configuration.

        Creates a new CacheManager instance with no active connections.
        The connection must be established by calling connect() before
        performing any cache operations.
        """
        self._pool: ConnectionPool | None = None
        self._client: redis.Redis | None = None
        self._connected: bool = False
        self._settings = get_settings()

    @property
    def enabled(self) -> bool:
        """Check if caching is enabled in the application configuration.

        Returns:
            bool: True if caching is enabled via settings, False otherwise.
        """
        return self._settings.cache_enabled

    async def connect(self) -> bool:
        """Initialize the Redis connection pool and establish a connection.

        Attempts to connect to Redis using the URL specified in application
        settings. Creates a connection pool with a maximum of 10 connections
        for efficient resource usage.

        Returns:
            bool: True if connection was successful or already established,
                False if caching is disabled or connection failed.

        Note:
            This method is idempotent. Calling it multiple times when already
            connected will simply return True without creating new connections.
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
        """Close the Redis connection pool and release all connections.

        Gracefully shuts down the Redis client and connection pool.
        After calling this method, connect() must be called again before
        performing any cache operations.
        """
        if self._client:
            await self._client.aclose()
            self._client = None
        if self._pool:
            await self._pool.disconnect()
            self._pool = None
        self._connected = False
        logger.info("Redis cache disconnected")

    async def get(self, key: str) -> Any | None:
        """Retrieve a value from the cache by its key.

        Fetches the value associated with the given key and deserializes
        it from JSON format.

        Args:
            key: The cache key to look up.

        Returns:
            The deserialized cached value if found and valid,
            None if the key doesn't exist, cache is not connected,
            or an error occurs during retrieval/deserialization.
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
        """Store a value in the cache with optional expiration.

        Serializes the value to JSON format and stores it in Redis.
        Non-JSON-serializable objects are converted to strings using
        the default str() conversion.

        Args:
            key: The cache key under which to store the value.
            value: The value to cache. Must be JSON serializable or
                convertible to string.
            ttl: Optional time-to-live in seconds. If provided, the key
                will automatically expire after this duration. If None,
                the key will persist indefinitely.

        Returns:
            bool: True if the value was successfully stored,
                False if cache is not connected or an error occurred.
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
        """Remove a value from the cache by its key.

        Args:
            key: The cache key to delete.

        Returns:
            bool: True if the deletion command was executed successfully,
                False if cache is not connected or an error occurred.

        Note:
            Returns True even if the key did not exist, as the operation
            itself was successful.
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
        """Delete all cache keys matching a specified pattern.

        Uses Redis SCAN to iterate through keys matching the pattern
        and deletes them in a single batch operation. This is safer
        than KEYS for production use as it doesn't block the server.

        Args:
            pattern: Redis glob-style pattern to match keys.
                Examples: 'resources:*', 'user:*:session', '*temp*'

        Returns:
            int: The number of keys that were deleted. Returns 0 if
                cache is not connected, no keys matched, or an error occurred.
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
        """Check if a key exists in the cache.

        Args:
            key: The cache key to check.

        Returns:
            bool: True if the key exists in the cache,
                False if it doesn't exist, cache is not connected,
                or an error occurred.
        """
        if not self._connected or not self._client:
            return False

        try:
            return await self._client.exists(key) > 0
        except RedisError:
            return False

    async def incr(self, key: str, ttl: int | None = None) -> int | None:
        """Increment an integer counter stored at the given key.

        If the key does not exist, it is initialized to 0 before
        incrementing. This operation is atomic.

        Args:
            key: The cache key containing the counter.
            ttl: Optional time-to-live in seconds. Only applied when
                the key is first created (counter value becomes 1).

        Returns:
            int: The new value of the counter after incrementing.
            None: If cache is not connected or an error occurred.

        Note:
            The TTL is only set on the first increment (when value becomes 1)
            to avoid resetting the expiration on subsequent increments.
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
        """Check if the cache manager has an active Redis connection.

        Returns:
            bool: True if connected to Redis and ready for operations,
                False otherwise.
        """
        return self._connected


# Global cache manager instance
cache_manager = CacheManager()


def _make_cache_key(prefix: str, *args: Any, **kwargs: Any) -> str:
    """Generate a deterministic cache key from a prefix and arguments.

    Creates a cache key by joining the prefix with string representations
    of the provided arguments. For long keys (over 200 characters), an
    MD5 hash is used to shorten the key while maintaining uniqueness.

    Args:
        prefix: The key prefix identifying the cache category
            (e.g., 'resources', 'stats', 'user').
        *args: Positional arguments to include in the key. None values
            are skipped.
        **kwargs: Keyword arguments to include in the key. None values
            are skipped. Arguments are sorted by key name for consistency.

    Returns:
        str: A cache key string in the format 'prefix:arg1:arg2:key=value'
            or 'prefix:hash' for long keys.

    Example:
        >>> _make_cache_key("resources", 123, status="active")
        'resources:123:status=active'
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
    """Decorator to automatically cache async function results.

    Wraps an async function to cache its return value based on the
    function arguments. On subsequent calls with the same arguments,
    the cached value is returned instead of executing the function.

    Args:
        prefix: Cache key prefix used to namespace the cached values.
            Should describe the type of data being cached.
        ttl: Time-to-live in seconds for cached values. If None,
            uses the default TTL from application settings
            (cache_ttl_resources).
        key_builder: Optional custom function to generate cache keys.
            If provided, it receives the same arguments as the decorated
            function and should return a string cache key.

    Returns:
        Callable: A decorator function that wraps async functions
            with caching behavior.

    Example:
        Basic usage with automatic key generation::

            @cached("resources", ttl=30)
            async def get_resources(status: str):
                return await db.query(...)

        With custom key builder::

            def custom_key(user_id: int, **kwargs) -> str:
                return f"user:{user_id}:profile"

            @cached("user", key_builder=custom_key)
            async def get_user_profile(user_id: int):
                return await db.get_user(user_id)

    Note:
        - Only works with async functions
        - None return values are not cached
        - Object arguments (those with __dict__) are filtered from
          automatic key generation to avoid including db sessions, etc.
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        """Inner decorator that wraps the target function.

        Args:
            func: The async function to wrap with caching.

        Returns:
            Callable: The wrapped function with caching behavior.
        """

        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            """Wrapper function that implements the caching logic.

            Args:
                *args: Positional arguments passed to the wrapped function.
                **kwargs: Keyword arguments passed to the wrapped function.

            Returns:
                The cached value if available, otherwise the result
                of calling the wrapped function.
            """
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
    """Invalidate all cache entries matching a specified pattern.

    Convenience function that wraps cache_manager.delete_pattern()
    for invalidating groups of related cache entries.

    Args:
        pattern: Redis glob-style pattern to match keys for deletion.
            Examples: 'resources:*', 'user:123:*'

    Returns:
        int: The number of cache keys that were invalidated.
    """
    return await cache_manager.delete_pattern(pattern)


class CacheKeys:
    """Standard cache key prefixes for consistent cache organization.

    This class defines constant prefixes used throughout the application
    to namespace different types of cached data. Using these constants
    ensures consistency and makes cache invalidation predictable.

    Attributes:
        RESOURCES: Prefix for individual resource cache entries.
        RESOURCES_LIST: Prefix for cached lists of resources.
        RESOURCES_SEARCH: Prefix for cached search results.
        RESOURCE_AVAILABILITY: Prefix for resource availability data.
        STATS: Prefix for statistics and analytics data.
        USER_SESSION: Prefix for user session data.
        DASHBOARD: Prefix for dashboard-related cached data.

    Example:
        Using prefixes with the cached decorator::

            @cached(CacheKeys.RESOURCES, ttl=60)
            async def get_resource(resource_id: int):
                ...

        Manual cache key construction::

            cache_key = f"{CacheKeys.STATS}:daily_summary"
            await cache_manager.set(cache_key, stats_data)
    """

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
    """Cache a list of resources with a specified key suffix.

    Convenience function for caching resource list query results
    with consistent key formatting.

    Args:
        key_suffix: Suffix to append to the resources:list prefix.
            Should describe the filter or context (e.g., 'active',
            'available', 'user_123').
        data: List of resource dictionaries to cache.
        ttl: Time-to-live in seconds. If None, uses the default
            cache_ttl_resources from settings.

    Returns:
        bool: True if the list was successfully cached, False otherwise.

    Example:
        >>> resources = [{"id": 1, "name": "Room A"}, {"id": 2, "name": "Room B"}]
        >>> await cache_resource_list("active", resources, ttl=300)
        True
    """
    settings = get_settings()
    cache_key = f"{CacheKeys.RESOURCES_LIST}:{key_suffix}"
    return await cache_manager.set(cache_key, data, ttl or settings.cache_ttl_resources)


async def get_cached_resource_list(key_suffix: str) -> list[dict[str, Any]] | None:
    """Retrieve a cached list of resources by key suffix.

    Args:
        key_suffix: The suffix used when the list was cached.

    Returns:
        list: The cached list of resource dictionaries if found.
        None: If the cache key doesn't exist or cache is unavailable.

    Example:
        >>> cached_resources = await get_cached_resource_list("active")
        >>> if cached_resources:
        ...     return cached_resources
        >>> # Fallback to database query
    """
    cache_key = f"{CacheKeys.RESOURCES_LIST}:{key_suffix}"
    return await cache_manager.get(cache_key)


async def invalidate_resource_cache() -> int:
    """Invalidate all resource-related cache entries.

    Clears all cached data under the resources and dashboard prefixes.
    This should be called whenever resources are created, updated,
    or deleted to ensure cache consistency.

    Returns:
        int: Total number of cache keys that were invalidated.

    Note:
        This invalidates both resource caches and dashboard caches,
        as dashboard data typically depends on resource state.
    """
    count = 0
    count += await cache_manager.delete_pattern(f"{CacheKeys.RESOURCES}:*")
    count += await cache_manager.delete_pattern(f"{CacheKeys.DASHBOARD}:*")
    logger.info(f"Invalidated {count} resource cache entries")
    return count


async def cache_stats(key: str, data: dict[str, Any], ttl: int | None = None) -> bool:
    """Cache dashboard or statistics data.

    Convenience function for caching computed statistics and
    analytics data that may be expensive to generate.

    Args:
        key: Identifier for the statistics data (e.g., 'daily_summary',
            'usage_report', 'weekly_trends').
        data: Dictionary containing the statistics to cache.
        ttl: Time-to-live in seconds. If None, uses the default
            cache_ttl_stats from settings.

    Returns:
        bool: True if the statistics were successfully cached,
            False otherwise.

    Example:
        >>> stats = {"total_reservations": 150, "active_resources": 25}
        >>> await cache_stats("daily_summary", stats, ttl=3600)
        True
    """
    settings = get_settings()
    cache_key = f"{CacheKeys.STATS}:{key}"
    return await cache_manager.set(cache_key, data, ttl or settings.cache_ttl_stats)


async def get_cached_stats(key: str) -> dict[str, Any] | None:
    """Retrieve cached statistics data by key.

    Args:
        key: The identifier used when the statistics were cached.

    Returns:
        dict: The cached statistics dictionary if found.
        None: If the cache key doesn't exist or cache is unavailable.

    Example:
        >>> cached_stats = await get_cached_stats("daily_summary")
        >>> if cached_stats:
        ...     return cached_stats
        >>> # Fallback to computing stats from database
    """
    cache_key = f"{CacheKeys.STATS}:{key}"
    return await cache_manager.get(cache_key)
