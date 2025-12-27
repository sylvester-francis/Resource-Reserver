"""Tests for the Redis cache module.

Author: Sylvester-Francis
"""

from unittest.mock import AsyncMock, patch

import pytest

from app.core.cache import (
    CacheKeys,
    CacheManager,
    _make_cache_key,
    cache_manager,
)


class TestMakeCacheKey:
    """Tests for cache key generation."""

    def test_simple_key(self):
        """Test generating a simple cache key."""
        key = _make_cache_key("resources", 1)
        assert key == "resources:1"

    def test_key_with_kwargs(self):
        """Test generating key with keyword arguments."""
        key = _make_cache_key("resources", status="available", limit=10)
        assert "resources" in key
        assert "status=available" in key
        assert "limit=10" in key

    def test_key_with_none_values(self):
        """Test that None values are excluded from key."""
        key = _make_cache_key("resources", None, status=None, limit=10)
        assert key == "resources:limit=10"

    def test_long_key_hashed(self):
        """Test that very long keys are hashed."""
        long_value = "x" * 300
        key = _make_cache_key("resources", long_value)
        assert len(key) < 250  # Should be shorter due to hashing
        assert key.startswith("resources:")


class TestCacheManager:
    """Tests for CacheManager class."""

    @pytest.fixture
    def cache_mgr(self):
        """Create a fresh CacheManager instance."""
        return CacheManager()

    def test_initial_state(self, cache_mgr):
        """Test initial state of cache manager."""
        assert not cache_mgr.is_connected()
        assert cache_mgr._client is None
        assert cache_mgr._pool is None

    @pytest.mark.asyncio
    async def test_connect_when_disabled(self, cache_mgr):
        """Test connection fails gracefully when cache is disabled."""
        with patch.object(cache_mgr, "_settings") as mock_settings:
            mock_settings.cache_enabled = False
            result = await cache_mgr.connect()
            assert result is False
            assert not cache_mgr.is_connected()

    @pytest.mark.asyncio
    async def test_get_when_not_connected(self, cache_mgr):
        """Test get returns None when not connected."""
        result = await cache_mgr.get("test_key")
        assert result is None

    @pytest.mark.asyncio
    async def test_set_when_not_connected(self, cache_mgr):
        """Test set returns False when not connected."""
        result = await cache_mgr.set("test_key", {"data": "value"})
        assert result is False

    @pytest.mark.asyncio
    async def test_delete_when_not_connected(self, cache_mgr):
        """Test delete returns False when not connected."""
        result = await cache_mgr.delete("test_key")
        assert result is False

    @pytest.mark.asyncio
    async def test_exists_when_not_connected(self, cache_mgr):
        """Test exists returns False when not connected."""
        result = await cache_mgr.exists("test_key")
        assert result is False

    @pytest.mark.asyncio
    async def test_delete_pattern_when_not_connected(self, cache_mgr):
        """Test delete_pattern returns 0 when not connected."""
        result = await cache_mgr.delete_pattern("resources:*")
        assert result == 0

    @pytest.mark.asyncio
    async def test_incr_when_not_connected(self, cache_mgr):
        """Test incr returns None when not connected."""
        result = await cache_mgr.incr("counter_key")
        assert result is None


class TestCacheManagerWithMockedRedis:
    """Tests for CacheManager with mocked Redis client."""

    @pytest.fixture
    def connected_cache(self):
        """Create a CacheManager with mocked Redis connection."""
        cache = CacheManager()
        cache._connected = True
        cache._client = AsyncMock()
        return cache

    @pytest.mark.asyncio
    async def test_get_success(self, connected_cache):
        """Test successful cache get."""
        connected_cache._client.get = AsyncMock(return_value='{"key": "value"}')
        result = await connected_cache.get("test_key")
        assert result == {"key": "value"}
        connected_cache._client.get.assert_called_once_with("test_key")

    @pytest.mark.asyncio
    async def test_get_cache_miss(self, connected_cache):
        """Test cache miss returns None."""
        connected_cache._client.get = AsyncMock(return_value=None)
        result = await connected_cache.get("missing_key")
        assert result is None

    @pytest.mark.asyncio
    async def test_set_without_ttl(self, connected_cache):
        """Test set without TTL."""
        connected_cache._client.set = AsyncMock()
        result = await connected_cache.set("test_key", {"data": "value"})
        assert result is True
        connected_cache._client.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_set_with_ttl(self, connected_cache):
        """Test set with TTL."""
        connected_cache._client.setex = AsyncMock()
        result = await connected_cache.set("test_key", {"data": "value"}, ttl=60)
        assert result is True
        connected_cache._client.setex.assert_called_once_with(
            "test_key", 60, '{"data": "value"}'
        )

    @pytest.mark.asyncio
    async def test_delete_success(self, connected_cache):
        """Test successful cache delete."""
        connected_cache._client.delete = AsyncMock()
        result = await connected_cache.delete("test_key")
        assert result is True
        connected_cache._client.delete.assert_called_once_with("test_key")

    @pytest.mark.asyncio
    async def test_exists_true(self, connected_cache):
        """Test exists returns True when key exists."""
        connected_cache._client.exists = AsyncMock(return_value=1)
        result = await connected_cache.exists("test_key")
        assert result is True

    @pytest.mark.asyncio
    async def test_exists_false(self, connected_cache):
        """Test exists returns False when key doesn't exist."""
        connected_cache._client.exists = AsyncMock(return_value=0)
        result = await connected_cache.exists("missing_key")
        assert result is False

    @pytest.mark.asyncio
    async def test_incr_first_call(self, connected_cache):
        """Test incr on new key sets TTL."""
        connected_cache._client.incr = AsyncMock(return_value=1)
        connected_cache._client.expire = AsyncMock()
        result = await connected_cache.incr("counter", ttl=60)
        assert result == 1
        connected_cache._client.expire.assert_called_once_with("counter", 60)

    @pytest.mark.asyncio
    async def test_incr_subsequent_call(self, connected_cache):
        """Test incr on existing key doesn't set TTL."""
        connected_cache._client.incr = AsyncMock(return_value=5)
        connected_cache._client.expire = AsyncMock()
        result = await connected_cache.incr("counter", ttl=60)
        assert result == 5
        connected_cache._client.expire.assert_not_called()


class TestCacheKeys:
    """Tests for CacheKeys constants."""

    def test_cache_key_prefixes(self):
        """Test that all cache key prefixes are defined."""
        assert CacheKeys.RESOURCES == "resources"
        assert CacheKeys.RESOURCES_LIST == "resources:list"
        assert CacheKeys.RESOURCES_SEARCH == "resources:search"
        assert CacheKeys.RESOURCE_AVAILABILITY == "resources:availability"
        assert CacheKeys.STATS == "stats"
        assert CacheKeys.USER_SESSION == "user:session"
        assert CacheKeys.DASHBOARD == "dashboard"


class TestGlobalCacheManager:
    """Tests for the global cache_manager instance."""

    def test_global_instance_exists(self):
        """Test that global cache_manager instance exists."""
        assert cache_manager is not None
        assert isinstance(cache_manager, CacheManager)

    def test_global_instance_properties(self):
        """Test global cache_manager properties."""
        # enabled property should return a boolean based on settings
        assert isinstance(cache_manager.enabled, bool)
