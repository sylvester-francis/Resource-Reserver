"""Metrics collection and Prometheus format export.

Provides functionality for:
- Request/response metrics collection
- Database connection pool monitoring
- WebSocket connection tracking
- Cache hit/miss rates
- Prometheus format export

Author: Sylvester-Francis
"""

import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime
from threading import Lock
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class RequestMetrics:
    """Tracks request-level metrics."""

    total_requests: int = 0
    total_errors: int = 0
    request_duration_sum: float = 0.0
    request_duration_count: int = 0
    status_codes: dict[int, int] = field(default_factory=lambda: defaultdict(int))
    endpoints: dict[str, int] = field(default_factory=lambda: defaultdict(int))


@dataclass
class CacheMetrics:
    """Tracks cache-related metrics."""

    hits: int = 0
    misses: int = 0
    sets: int = 0
    deletes: int = 0
    errors: int = 0


@dataclass
class DatabaseMetrics:
    """Tracks database-related metrics."""

    queries: int = 0
    query_duration_sum: float = 0.0
    errors: int = 0
    pool_size: int = 0
    pool_checked_out: int = 0


@dataclass
class WebSocketMetrics:
    """Tracks WebSocket connection metrics."""

    active_connections: int = 0
    total_connections: int = 0
    messages_sent: int = 0
    messages_received: int = 0


class MetricsCollector:
    """Collects and exports application metrics."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._start_time = time.time()
        self.requests = RequestMetrics()
        self.cache = CacheMetrics()
        self.database = DatabaseMetrics()
        self.websocket = WebSocketMetrics()

    def record_request(
        self,
        method: str,
        path: str,
        status_code: int,
        duration: float,
    ) -> None:
        """Record a request metric."""
        with self._lock:
            self.requests.total_requests += 1
            if status_code >= 400:
                self.requests.total_errors += 1
            self.requests.request_duration_sum += duration
            self.requests.request_duration_count += 1
            self.requests.status_codes[status_code] += 1
            endpoint_key = f"{method}:{path}"
            self.requests.endpoints[endpoint_key] += 1

    def record_cache_hit(self) -> None:
        """Record a cache hit."""
        with self._lock:
            self.cache.hits += 1

    def record_cache_miss(self) -> None:
        """Record a cache miss."""
        with self._lock:
            self.cache.misses += 1

    def record_cache_set(self) -> None:
        """Record a cache set operation."""
        with self._lock:
            self.cache.sets += 1

    def record_cache_delete(self) -> None:
        """Record a cache delete operation."""
        with self._lock:
            self.cache.deletes += 1

    def record_cache_error(self) -> None:
        """Record a cache error."""
        with self._lock:
            self.cache.errors += 1

    def record_db_query(self, duration: float) -> None:
        """Record a database query."""
        with self._lock:
            self.database.queries += 1
            self.database.query_duration_sum += duration

    def record_db_error(self) -> None:
        """Record a database error."""
        with self._lock:
            self.database.errors += 1

    def update_db_pool_stats(self, pool_size: int, checked_out: int) -> None:
        """Update database pool statistics."""
        with self._lock:
            self.database.pool_size = pool_size
            self.database.pool_checked_out = checked_out

    def record_ws_connect(self) -> None:
        """Record a WebSocket connection."""
        with self._lock:
            self.websocket.active_connections += 1
            self.websocket.total_connections += 1

    def record_ws_disconnect(self) -> None:
        """Record a WebSocket disconnection."""
        with self._lock:
            self.websocket.active_connections = max(
                0, self.websocket.active_connections - 1
            )

    def record_ws_message_sent(self) -> None:
        """Record a WebSocket message sent."""
        with self._lock:
            self.websocket.messages_sent += 1

    def record_ws_message_received(self) -> None:
        """Record a WebSocket message received."""
        with self._lock:
            self.websocket.messages_received += 1

    def get_uptime_seconds(self) -> float:
        """Get application uptime in seconds."""
        return time.time() - self._start_time

    def get_summary(self) -> dict[str, Any]:
        """Get a summary of all metrics."""
        with self._lock:
            avg_request_duration = (
                self.requests.request_duration_sum
                / self.requests.request_duration_count
                if self.requests.request_duration_count > 0
                else 0
            )
            avg_query_duration = (
                self.database.query_duration_sum / self.database.queries
                if self.database.queries > 0
                else 0
            )
            cache_hit_rate = (
                self.cache.hits / (self.cache.hits + self.cache.misses)
                if (self.cache.hits + self.cache.misses) > 0
                else 0
            )

            return {
                "uptime_seconds": self.get_uptime_seconds(),
                "requests": {
                    "total": self.requests.total_requests,
                    "errors": self.requests.total_errors,
                    "avg_duration_ms": round(avg_request_duration * 1000, 2),
                    "error_rate": (
                        round(
                            self.requests.total_errors
                            / self.requests.total_requests
                            * 100,
                            2,
                        )
                        if self.requests.total_requests > 0
                        else 0
                    ),
                },
                "cache": {
                    "hits": self.cache.hits,
                    "misses": self.cache.misses,
                    "hit_rate": round(cache_hit_rate * 100, 2),
                    "sets": self.cache.sets,
                    "deletes": self.cache.deletes,
                    "errors": self.cache.errors,
                },
                "database": {
                    "queries": self.database.queries,
                    "avg_query_duration_ms": round(avg_query_duration * 1000, 2),
                    "errors": self.database.errors,
                    "pool_size": self.database.pool_size,
                    "pool_checked_out": self.database.pool_checked_out,
                },
                "websocket": {
                    "active_connections": self.websocket.active_connections,
                    "total_connections": self.websocket.total_connections,
                    "messages_sent": self.websocket.messages_sent,
                    "messages_received": self.websocket.messages_received,
                },
            }

    def export_prometheus(self) -> str:
        """Export metrics in Prometheus format."""
        lines = []
        uptime = self.get_uptime_seconds()

        with self._lock:
            # Uptime
            lines.append("# HELP app_uptime_seconds Application uptime in seconds")
            lines.append("# TYPE app_uptime_seconds gauge")
            lines.append(f"app_uptime_seconds {uptime:.2f}")

            # Request metrics
            lines.append("# HELP http_requests_total Total number of HTTP requests")
            lines.append("# TYPE http_requests_total counter")
            lines.append(f"http_requests_total {self.requests.total_requests}")

            lines.append(
                "# HELP http_request_errors_total Total number of HTTP request errors"
            )
            lines.append("# TYPE http_request_errors_total counter")
            lines.append(f"http_request_errors_total {self.requests.total_errors}")

            if self.requests.request_duration_count > 0:
                avg_duration = (
                    self.requests.request_duration_sum
                    / self.requests.request_duration_count
                )
                lines.append(
                    "# HELP http_request_duration_seconds_avg Average request duration"
                )
                lines.append("# TYPE http_request_duration_seconds_avg gauge")
                lines.append(f"http_request_duration_seconds_avg {avg_duration:.6f}")

            # Status code breakdown
            lines.append("# HELP http_requests_by_status HTTP requests by status code")
            lines.append("# TYPE http_requests_by_status counter")
            for code, count in sorted(self.requests.status_codes.items()):
                lines.append(f'http_requests_by_status{{code="{code}"}} {count}')

            # Cache metrics
            lines.append("# HELP cache_hits_total Total cache hits")
            lines.append("# TYPE cache_hits_total counter")
            lines.append(f"cache_hits_total {self.cache.hits}")

            lines.append("# HELP cache_misses_total Total cache misses")
            lines.append("# TYPE cache_misses_total counter")
            lines.append(f"cache_misses_total {self.cache.misses}")

            # Database metrics
            lines.append("# HELP db_queries_total Total database queries")
            lines.append("# TYPE db_queries_total counter")
            lines.append(f"db_queries_total {self.database.queries}")

            lines.append("# HELP db_errors_total Total database errors")
            lines.append("# TYPE db_errors_total counter")
            lines.append(f"db_errors_total {self.database.errors}")

            lines.append("# HELP db_pool_size Database connection pool size")
            lines.append("# TYPE db_pool_size gauge")
            lines.append(f"db_pool_size {self.database.pool_size}")

            lines.append("# HELP db_pool_checked_out Database connections checked out")
            lines.append("# TYPE db_pool_checked_out gauge")
            lines.append(f"db_pool_checked_out {self.database.pool_checked_out}")

            # WebSocket metrics
            lines.append(
                "# HELP websocket_connections_active Active WebSocket connections"
            )
            lines.append("# TYPE websocket_connections_active gauge")
            lines.append(
                f"websocket_connections_active {self.websocket.active_connections}"
            )

            lines.append(
                "# HELP websocket_connections_total Total WebSocket connections"
            )
            lines.append("# TYPE websocket_connections_total counter")
            lines.append(
                f"websocket_connections_total {self.websocket.total_connections}"
            )

            lines.append(
                "# HELP websocket_messages_sent_total Total WebSocket messages sent"
            )
            lines.append("# TYPE websocket_messages_sent_total counter")
            lines.append(
                f"websocket_messages_sent_total {self.websocket.messages_sent}"
            )

        return "\n".join(lines) + "\n"

    def reset(self) -> None:
        """Reset all metrics (useful for testing)."""
        with self._lock:
            self._start_time = time.time()
            self.requests = RequestMetrics()
            self.cache = CacheMetrics()
            self.database = DatabaseMetrics()
            self.websocket = WebSocketMetrics()


# Global metrics collector instance
metrics = MetricsCollector()


def get_component_status() -> dict[str, dict[str, Any]]:
    """Get detailed status of all components.

    Returns:
        Dictionary with component names and their status details
    """
    from app.config import get_settings
    from app.core.cache import cache_manager

    settings = get_settings()
    components = {}

    # Database status
    try:
        from app.database import engine

        with engine.connect() as conn:
            from sqlalchemy import text

            conn.execute(text("SELECT 1"))
            pool = engine.pool
            components["database"] = {
                "status": "healthy",
                "pool_size": pool.size() if hasattr(pool, "size") else 0,
                "checked_out": (
                    pool.checkedout() if hasattr(pool, "checkedout") else 0
                ),
                "overflow": pool.overflow() if hasattr(pool, "overflow") else 0,
            }
    except Exception as e:
        components["database"] = {
            "status": "unhealthy",
            "error": str(e)[:100],
        }

    # Cache status
    if settings.cache_enabled:
        components["cache"] = {
            "status": "connected" if cache_manager.is_connected() else "disconnected",
            "enabled": True,
        }
    else:
        components["cache"] = {
            "status": "disabled",
            "enabled": False,
        }

    # WebSocket manager status
    try:
        from app.websocket import manager as ws_manager

        components["websocket"] = {
            "status": "healthy",
            "active_connections": len(ws_manager.active_connections),
        }
    except Exception as e:
        components["websocket"] = {
            "status": "unknown",
            "error": str(e)[:100],
        }

    return components


def check_readiness() -> tuple[bool, dict[str, Any]]:
    """Check if the application is ready to receive traffic.

    Returns:
        Tuple of (is_ready, details)
    """
    components = get_component_status()

    # Database must be healthy for readiness
    db_ready = components.get("database", {}).get("status") == "healthy"

    # For now, only database is required for readiness
    # Cache can be disabled or disconnected (degraded mode is OK)
    is_ready = db_ready

    return is_ready, {
        "ready": is_ready,
        "components": components,
        "timestamp": datetime.now(UTC).isoformat(),
    }


def check_liveness() -> tuple[bool, dict[str, Any]]:
    """Check if the application is alive (basic health).

    Returns:
        Tuple of (is_alive, details)
    """
    # Application is alive if it can respond
    return True, {
        "alive": True,
        "timestamp": datetime.now(UTC).isoformat(),
        "uptime_seconds": round(metrics.get_uptime_seconds(), 2),
    }
