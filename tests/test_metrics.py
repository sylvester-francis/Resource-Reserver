"""Tests for the metrics collection module.

Author: Sylvester-Francis
"""

import pytest

from app.core.metrics import (
    CacheMetrics,
    DatabaseMetrics,
    MetricsCollector,
    RequestMetrics,
    WebSocketMetrics,
    check_liveness,
    metrics,
)


class TestRequestMetrics:
    """Tests for RequestMetrics dataclass."""

    def test_default_values(self):
        """Test default values for RequestMetrics."""
        req_metrics = RequestMetrics()
        assert req_metrics.total_requests == 0
        assert req_metrics.total_errors == 0
        assert req_metrics.request_duration_sum == 0.0
        assert req_metrics.request_duration_count == 0
        assert len(req_metrics.status_codes) == 0
        assert len(req_metrics.endpoints) == 0


class TestCacheMetrics:
    """Tests for CacheMetrics dataclass."""

    def test_default_values(self):
        """Test default values for CacheMetrics."""
        cache_metrics = CacheMetrics()
        assert cache_metrics.hits == 0
        assert cache_metrics.misses == 0
        assert cache_metrics.sets == 0
        assert cache_metrics.deletes == 0
        assert cache_metrics.errors == 0


class TestDatabaseMetrics:
    """Tests for DatabaseMetrics dataclass."""

    def test_default_values(self):
        """Test default values for DatabaseMetrics."""
        db_metrics = DatabaseMetrics()
        assert db_metrics.queries == 0
        assert db_metrics.query_duration_sum == 0.0
        assert db_metrics.errors == 0
        assert db_metrics.pool_size == 0
        assert db_metrics.pool_checked_out == 0


class TestWebSocketMetrics:
    """Tests for WebSocketMetrics dataclass."""

    def test_default_values(self):
        """Test default values for WebSocketMetrics."""
        ws_metrics = WebSocketMetrics()
        assert ws_metrics.active_connections == 0
        assert ws_metrics.total_connections == 0
        assert ws_metrics.messages_sent == 0
        assert ws_metrics.messages_received == 0


class TestMetricsCollector:
    """Tests for MetricsCollector class."""

    @pytest.fixture
    def collector(self):
        """Create a fresh MetricsCollector for each test."""
        collector = MetricsCollector()
        yield collector
        collector.reset()

    def test_record_request(self, collector):
        """Test recording a request metric."""
        collector.record_request("GET", "/api/v1/resources", 200, 0.05)

        assert collector.requests.total_requests == 1
        assert collector.requests.total_errors == 0
        assert collector.requests.request_duration_sum == 0.05
        assert collector.requests.request_duration_count == 1
        assert collector.requests.status_codes[200] == 1
        assert collector.requests.endpoints["GET:/api/v1/resources"] == 1

    def test_record_error_request(self, collector):
        """Test recording an error request."""
        collector.record_request("POST", "/api/v1/resources", 500, 0.1)

        assert collector.requests.total_requests == 1
        assert collector.requests.total_errors == 1
        assert collector.requests.status_codes[500] == 1

    def test_record_4xx_as_error(self, collector):
        """Test that 4xx status codes are counted as errors."""
        collector.record_request("GET", "/api/v1/resources/999", 404, 0.02)

        assert collector.requests.total_errors == 1
        assert collector.requests.status_codes[404] == 1

    def test_record_cache_hit(self, collector):
        """Test recording cache hits."""
        collector.record_cache_hit()
        collector.record_cache_hit()

        assert collector.cache.hits == 2

    def test_record_cache_miss(self, collector):
        """Test recording cache misses."""
        collector.record_cache_miss()

        assert collector.cache.misses == 1

    def test_record_cache_set(self, collector):
        """Test recording cache sets."""
        collector.record_cache_set()

        assert collector.cache.sets == 1

    def test_record_cache_delete(self, collector):
        """Test recording cache deletes."""
        collector.record_cache_delete()

        assert collector.cache.deletes == 1

    def test_record_cache_error(self, collector):
        """Test recording cache errors."""
        collector.record_cache_error()

        assert collector.cache.errors == 1

    def test_record_db_query(self, collector):
        """Test recording database queries."""
        collector.record_db_query(0.01)
        collector.record_db_query(0.02)

        assert collector.database.queries == 2
        assert collector.database.query_duration_sum == 0.03

    def test_record_db_error(self, collector):
        """Test recording database errors."""
        collector.record_db_error()

        assert collector.database.errors == 1

    def test_update_db_pool_stats(self, collector):
        """Test updating database pool statistics."""
        collector.update_db_pool_stats(10, 3)

        assert collector.database.pool_size == 10
        assert collector.database.pool_checked_out == 3

    def test_record_ws_connect(self, collector):
        """Test recording WebSocket connections."""
        collector.record_ws_connect()

        assert collector.websocket.active_connections == 1
        assert collector.websocket.total_connections == 1

    def test_record_ws_disconnect(self, collector):
        """Test recording WebSocket disconnections."""
        collector.record_ws_connect()
        collector.record_ws_connect()
        collector.record_ws_disconnect()

        assert collector.websocket.active_connections == 1
        assert collector.websocket.total_connections == 2

    def test_record_ws_disconnect_prevents_negative(self, collector):
        """Test that active connections cannot go negative."""
        collector.record_ws_disconnect()

        assert collector.websocket.active_connections == 0

    def test_record_ws_message_sent(self, collector):
        """Test recording WebSocket messages sent."""
        collector.record_ws_message_sent()

        assert collector.websocket.messages_sent == 1

    def test_record_ws_message_received(self, collector):
        """Test recording WebSocket messages received."""
        collector.record_ws_message_received()

        assert collector.websocket.messages_received == 1

    def test_get_uptime_seconds(self, collector):
        """Test getting uptime in seconds."""
        uptime = collector.get_uptime_seconds()

        assert uptime >= 0

    def test_get_summary(self, collector):
        """Test getting metrics summary."""
        collector.record_request("GET", "/api/v1/resources", 200, 0.05)
        collector.record_cache_hit()
        collector.record_cache_miss()
        collector.record_db_query(0.01)

        summary = collector.get_summary()

        assert "uptime_seconds" in summary
        assert summary["requests"]["total"] == 1
        assert summary["cache"]["hits"] == 1
        assert summary["cache"]["misses"] == 1
        assert summary["cache"]["hit_rate"] == 50.0
        assert summary["database"]["queries"] == 1

    def test_get_summary_with_no_data(self, collector):
        """Test getting summary with no recorded data."""
        summary = collector.get_summary()

        assert summary["requests"]["total"] == 0
        assert summary["requests"]["avg_duration_ms"] == 0
        assert summary["requests"]["error_rate"] == 0
        assert summary["cache"]["hit_rate"] == 0
        assert summary["database"]["avg_query_duration_ms"] == 0

    def test_export_prometheus(self, collector):
        """Test exporting metrics in Prometheus format."""
        collector.record_request("GET", "/api/v1/resources", 200, 0.05)
        collector.record_cache_hit()

        prometheus_output = collector.export_prometheus()

        assert "# HELP app_uptime_seconds" in prometheus_output
        assert "# TYPE app_uptime_seconds gauge" in prometheus_output
        assert "http_requests_total 1" in prometheus_output
        assert "cache_hits_total 1" in prometheus_output

    def test_export_prometheus_with_status_codes(self, collector):
        """Test Prometheus export includes status code breakdown."""
        collector.record_request("GET", "/test", 200, 0.01)
        collector.record_request("GET", "/test", 404, 0.01)
        collector.record_request("POST", "/test", 500, 0.01)

        prometheus_output = collector.export_prometheus()

        assert 'http_requests_by_status{code="200"} 1' in prometheus_output
        assert 'http_requests_by_status{code="404"} 1' in prometheus_output
        assert 'http_requests_by_status{code="500"} 1' in prometheus_output

    def test_reset(self, collector):
        """Test resetting all metrics."""
        collector.record_request("GET", "/test", 200, 0.05)
        collector.record_cache_hit()
        collector.record_db_query(0.01)
        collector.record_ws_connect()

        collector.reset()

        assert collector.requests.total_requests == 0
        assert collector.cache.hits == 0
        assert collector.database.queries == 0
        assert collector.websocket.active_connections == 0


class TestGlobalMetrics:
    """Tests for the global metrics instance."""

    def test_global_metrics_exists(self):
        """Test that the global metrics instance exists."""
        assert metrics is not None
        assert isinstance(metrics, MetricsCollector)


class TestLivenessCheck:
    """Tests for the liveness check function."""

    def test_liveness_check_returns_alive(self):
        """Test that liveness check returns alive status."""
        is_alive, details = check_liveness()

        assert is_alive is True
        assert details["alive"] is True
        assert "timestamp" in details
        assert "uptime_seconds" in details
