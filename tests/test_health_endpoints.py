"""Tests for health check and metrics endpoints.

Author: Sylvester-Francis
"""

from fastapi.testclient import TestClient


class TestHealthEndpoint:
    """Tests for the /health endpoint."""

    def test_health_check_returns_200(self, client: TestClient):
        """Test that health check returns 200."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "timestamp" in data
        assert "version" in data
        assert "database" in data
        assert "api" in data
        assert "cache" in data
        assert "background_tasks" in data

    def test_health_check_shows_healthy_status(self, client: TestClient):
        """Test that health check shows healthy status."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["database"] == "healthy"


class TestReadyEndpoint:
    """Tests for the /ready endpoint."""

    def test_ready_check_returns_200_when_ready(self, client: TestClient):
        """Test that readiness check returns 200 when application is ready."""
        response = client.get("/ready")

        assert response.status_code == 200
        data = response.json()
        assert data["ready"] is True
        assert "components" in data
        assert "timestamp" in data

    def test_ready_check_includes_database_status(self, client: TestClient):
        """Test that readiness check includes database component status."""
        response = client.get("/ready")

        assert response.status_code == 200
        data = response.json()
        assert "database" in data["components"]
        assert data["components"]["database"]["status"] == "healthy"


class TestLiveEndpoint:
    """Tests for the /live endpoint."""

    def test_live_check_returns_200(self, client: TestClient):
        """Test that liveness check returns 200."""
        response = client.get("/live")

        assert response.status_code == 200
        data = response.json()
        assert data["alive"] is True
        assert "timestamp" in data
        assert "uptime_seconds" in data

    def test_live_check_uptime_is_positive(self, client: TestClient):
        """Test that uptime is a positive number."""
        response = client.get("/live")

        assert response.status_code == 200
        data = response.json()
        assert data["uptime_seconds"] >= 0


class TestMetricsEndpoint:
    """Tests for the /metrics endpoint."""

    def test_metrics_returns_prometheus_format(self, client: TestClient):
        """Test that metrics endpoint returns Prometheus format."""
        response = client.get("/metrics")

        assert response.status_code == 200
        assert response.headers["content-type"] == "text/plain; charset=utf-8"

        content = response.text
        assert "# HELP app_uptime_seconds" in content
        assert "# TYPE app_uptime_seconds gauge" in content
        assert "app_uptime_seconds" in content

    def test_metrics_includes_http_counters(self, client: TestClient):
        """Test that metrics include HTTP request counters."""
        # Make a request first to generate some metrics
        client.get("/health")

        response = client.get("/metrics")

        assert response.status_code == 200
        content = response.text
        assert "http_requests_total" in content

    def test_metrics_includes_cache_counters(self, client: TestClient):
        """Test that metrics include cache counters."""
        response = client.get("/metrics")

        assert response.status_code == 200
        content = response.text
        assert "cache_hits_total" in content
        assert "cache_misses_total" in content

    def test_metrics_includes_database_counters(self, client: TestClient):
        """Test that metrics include database counters."""
        response = client.get("/metrics")

        assert response.status_code == 200
        content = response.text
        assert "db_queries_total" in content
        assert "db_pool_size" in content

    def test_metrics_includes_websocket_counters(self, client: TestClient):
        """Test that metrics include WebSocket counters."""
        response = client.get("/metrics")

        assert response.status_code == 200
        content = response.text
        assert "websocket_connections_active" in content
        assert "websocket_connections_total" in content


class TestMetricsSummaryEndpoint:
    """Tests for the /api/v1/metrics/summary endpoint."""

    def test_metrics_summary_requires_auth(self, client: TestClient):
        """Test that metrics summary requires authentication."""
        response = client.get("/api/v1/metrics/summary")

        assert response.status_code == 401

    def test_metrics_summary_returns_json(self, client: TestClient, auth_headers: dict):
        """Test that authenticated request returns JSON summary."""
        response = client.get("/api/v1/metrics/summary", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert "uptime_seconds" in data
        assert "requests" in data
        assert "cache" in data
        assert "database" in data
        assert "websocket" in data

    def test_metrics_summary_includes_request_stats(
        self, client: TestClient, auth_headers: dict
    ):
        """Test that summary includes request statistics."""
        # Make a few requests to generate metrics
        client.get("/health")
        client.get("/live")
        client.get("/ready")

        response = client.get("/api/v1/metrics/summary", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["requests"]["total"] >= 3
        assert "avg_duration_ms" in data["requests"]
        assert "error_rate" in data["requests"]

    def test_metrics_summary_includes_cache_stats(
        self, client: TestClient, auth_headers: dict
    ):
        """Test that summary includes cache statistics."""
        response = client.get("/api/v1/metrics/summary", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert "hits" in data["cache"]
        assert "misses" in data["cache"]
        assert "hit_rate" in data["cache"]
