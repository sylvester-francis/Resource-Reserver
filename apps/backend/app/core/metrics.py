"""Metrics collection and Prometheus format export for application monitoring.

This module provides a comprehensive metrics collection system for tracking
application performance, resource utilization, and operational health. It
supports multiple metric types including request/response metrics, database
connection pool monitoring, WebSocket connection tracking, and cache
hit/miss rates.

Features:
    - Thread-safe metrics collection with lock-based synchronization
    - Request/response latency and error rate tracking
    - Database query performance and connection pool monitoring
    - WebSocket connection lifecycle and message tracking
    - Cache operation statistics with hit rate calculations
    - Prometheus-compatible metrics export format
    - Component health status reporting for readiness/liveness probes

Example:
    Basic usage with the global metrics collector::

        from app.core.metrics import metrics

        # Record an HTTP request
        metrics.record_request("GET", "/api/users", 200, 0.045)

        # Record cache operations
        metrics.record_cache_hit()
        metrics.record_cache_miss()

        # Get metrics summary
        summary = metrics.get_summary()
        print(f"Total requests: {summary['requests']['total']}")

        # Export for Prometheus scraping
        prometheus_output = metrics.export_prometheus()

    Health check usage::

        from app.core.metrics import check_readiness, check_liveness

        is_ready, details = check_readiness()
        is_alive, details = check_liveness()

Author:
    Sylvester-Francis
"""

import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime
from threading import Lock
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


@dataclass
class RequestMetrics:
    """Tracks HTTP request-level metrics for monitoring API performance.

    This dataclass aggregates metrics about incoming HTTP requests including
    total counts, error rates, response times, and endpoint-specific statistics.

    Attributes:
        total_requests: Cumulative count of all HTTP requests received.
        total_errors: Count of requests that resulted in 4xx or 5xx status codes.
        request_duration_sum: Sum of all request durations in seconds for
            calculating average latency.
        request_duration_count: Number of requests with recorded durations.
        status_codes: Dictionary mapping HTTP status codes to their occurrence
            counts. Uses defaultdict for automatic initialization.
        endpoints: Dictionary mapping endpoint keys (format: "METHOD:path") to
            their request counts. Uses defaultdict for automatic initialization.
    """

    total_requests: int = 0
    total_errors: int = 0
    request_duration_sum: float = 0.0
    request_duration_count: int = 0
    status_codes: dict[int, int] = field(default_factory=lambda: defaultdict(int))
    endpoints: dict[str, int] = field(default_factory=lambda: defaultdict(int))


@dataclass
class CacheMetrics:
    """Tracks cache operation metrics for monitoring cache effectiveness.

    This dataclass aggregates statistics about cache operations to help
    evaluate cache performance and identify potential issues.

    Attributes:
        hits: Count of successful cache lookups where the key was found.
        misses: Count of cache lookups where the key was not found.
        sets: Count of cache write operations (new entries or updates).
        deletes: Count of cache invalidation/deletion operations.
        errors: Count of cache operation failures due to connection issues
            or other errors.
    """

    hits: int = 0
    misses: int = 0
    sets: int = 0
    deletes: int = 0
    errors: int = 0


@dataclass
class DatabaseMetrics:
    """Tracks database operation metrics for monitoring query performance.

    This dataclass aggregates statistics about database operations and
    connection pool utilization.

    Attributes:
        queries: Total count of database queries executed.
        query_duration_sum: Sum of all query durations in seconds for
            calculating average query latency.
        errors: Count of failed database operations.
        pool_size: Current size of the database connection pool.
        pool_checked_out: Number of connections currently in use from the pool.
    """

    queries: int = 0
    query_duration_sum: float = 0.0
    errors: int = 0
    pool_size: int = 0
    pool_checked_out: int = 0


@dataclass
class WebSocketMetrics:
    """Tracks WebSocket connection metrics for monitoring real-time features.

    This dataclass aggregates statistics about WebSocket connections and
    message throughput.

    Attributes:
        active_connections: Current number of open WebSocket connections.
        total_connections: Cumulative count of all WebSocket connections
            established since application start.
        messages_sent: Total count of messages sent to WebSocket clients.
        messages_received: Total count of messages received from WebSocket clients.
    """

    active_connections: int = 0
    total_connections: int = 0
    messages_sent: int = 0
    messages_received: int = 0


class MetricsCollector:
    """Thread-safe collector for application metrics with Prometheus export support.

    This class provides a centralized, thread-safe mechanism for collecting
    various application metrics. It supports recording HTTP request metrics,
    cache operations, database queries, and WebSocket activity. Metrics can
    be exported in Prometheus text format for scraping.

    Attributes:
        requests: RequestMetrics instance tracking HTTP request statistics.
        cache: CacheMetrics instance tracking cache operation statistics.
        database: DatabaseMetrics instance tracking database query statistics.
        websocket: WebSocketMetrics instance tracking WebSocket statistics.

    Example:
        Create and use a metrics collector::

            collector = MetricsCollector()
            collector.record_request("POST", "/api/resources", 201, 0.032)
            collector.record_cache_hit()

            summary = collector.get_summary()
            prometheus_data = collector.export_prometheus()
    """

    def __init__(self) -> None:
        """Initialize the metrics collector with default values.

        Creates a new MetricsCollector with all metric counters reset to zero
        and records the initialization time for uptime calculations.
        """
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
        """Record metrics for an HTTP request.

        Updates request counters, duration statistics, status code distribution,
        and endpoint-specific metrics in a thread-safe manner.

        Args:
            method: The HTTP method of the request (e.g., "GET", "POST").
            path: The request path (e.g., "/api/users/123").
            status_code: The HTTP response status code (e.g., 200, 404, 500).
            duration: The request duration in seconds.
        """
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
        """Record a successful cache lookup.

        Increments the cache hit counter in a thread-safe manner.
        """
        with self._lock:
            self.cache.hits += 1

    def record_cache_miss(self) -> None:
        """Record an unsuccessful cache lookup.

        Increments the cache miss counter in a thread-safe manner.
        """
        with self._lock:
            self.cache.misses += 1

    def record_cache_set(self) -> None:
        """Record a cache write operation.

        Increments the cache set counter in a thread-safe manner.
        """
        with self._lock:
            self.cache.sets += 1

    def record_cache_delete(self) -> None:
        """Record a cache deletion operation.

        Increments the cache delete counter in a thread-safe manner.
        """
        with self._lock:
            self.cache.deletes += 1

    def record_cache_error(self) -> None:
        """Record a cache operation error.

        Increments the cache error counter in a thread-safe manner.
        """
        with self._lock:
            self.cache.errors += 1

    def record_db_query(self, duration: float) -> None:
        """Record a database query execution.

        Updates query count and duration sum for calculating average
        query latency.

        Args:
            duration: The query execution time in seconds.
        """
        with self._lock:
            self.database.queries += 1
            self.database.query_duration_sum += duration

    def record_db_error(self) -> None:
        """Record a database operation error.

        Increments the database error counter in a thread-safe manner.
        """
        with self._lock:
            self.database.errors += 1

    def update_db_pool_stats(self, pool_size: int, checked_out: int) -> None:
        """Update database connection pool statistics.

        Args:
            pool_size: The current total size of the connection pool.
            checked_out: The number of connections currently in use.
        """
        with self._lock:
            self.database.pool_size = pool_size
            self.database.pool_checked_out = checked_out

    def record_ws_connect(self) -> None:
        """Record a new WebSocket connection.

        Increments both the active and total connection counters.
        """
        with self._lock:
            self.websocket.active_connections += 1
            self.websocket.total_connections += 1

    def record_ws_disconnect(self) -> None:
        """Record a WebSocket disconnection.

        Decrements the active connection counter, ensuring it does not
        go below zero.
        """
        with self._lock:
            self.websocket.active_connections = max(
                0, self.websocket.active_connections - 1
            )

    def record_ws_message_sent(self) -> None:
        """Record an outgoing WebSocket message.

        Increments the messages sent counter in a thread-safe manner.
        """
        with self._lock:
            self.websocket.messages_sent += 1

    def record_ws_message_received(self) -> None:
        """Record an incoming WebSocket message.

        Increments the messages received counter in a thread-safe manner.
        """
        with self._lock:
            self.websocket.messages_received += 1

    def get_uptime_seconds(self) -> float:
        """Calculate the application uptime.

        Returns:
            The number of seconds since the MetricsCollector was initialized.
        """
        return time.time() - self._start_time

    def get_summary(self) -> dict[str, Any]:
        """Generate a comprehensive summary of all collected metrics.

        Computes derived metrics such as average durations, error rates,
        and cache hit rates from the raw counters.

        Returns:
            A dictionary containing categorized metrics with the following
            top-level keys:
                - uptime_seconds: Application uptime in seconds.
                - requests: HTTP request statistics including total, errors,
                  avg_duration_ms, and error_rate percentage.
                - cache: Cache statistics including hits, misses, hit_rate
                  percentage, sets, deletes, and errors.
                - database: Database statistics including queries,
                  avg_query_duration_ms, errors, pool_size, and pool_checked_out.
                - websocket: WebSocket statistics including active_connections,
                  total_connections, messages_sent, and messages_received.
        """
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
        """Export all metrics in Prometheus text exposition format.

        Generates a text output compatible with Prometheus scraping,
        including HELP and TYPE annotations for each metric.

        Returns:
            A string containing all metrics formatted according to the
            Prometheus text exposition format, with each metric including
            HELP (description), TYPE (counter/gauge), and value lines.

        Example:
            The output format follows Prometheus conventions::

                # HELP app_uptime_seconds Application uptime in seconds
                # TYPE app_uptime_seconds gauge
                app_uptime_seconds 3600.00
                # HELP http_requests_total Total number of HTTP requests
                # TYPE http_requests_total counter
                http_requests_total 1000
        """
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
        """Reset all metrics to their initial values.

        Clears all collected metrics and resets the start time. This is
        primarily useful for testing purposes to ensure a clean state
        between test cases.
        """
        with self._lock:
            self._start_time = time.time()
            self.requests = RequestMetrics()
            self.cache = CacheMetrics()
            self.database = DatabaseMetrics()
            self.websocket = WebSocketMetrics()


# Global metrics collector instance
metrics = MetricsCollector()


def get_component_status(
    db_session: "Session | None" = None,
) -> dict[str, dict[str, Any]]:
    """Retrieve detailed health status of all application components.

    Checks the operational status of critical application components
    including the database, cache, and WebSocket manager. This function
    is typically used by health check endpoints.

    Returns:
        A dictionary mapping component names to their status dictionaries.
        Each component status includes at minimum a "status" key with
        values like "healthy", "unhealthy", "connected", "disconnected",
        or "disabled". Additional keys vary by component:

        - database: pool_size, checked_out, overflow (when healthy);
          error (when unhealthy)
        - cache: enabled, status
        - websocket: active_connections (when healthy); error (when unknown)

    Example:
        Check component status for monitoring::

            status = get_component_status()
            if status["database"]["status"] == "healthy":
                print("Database is operational")
    """
    from app.config import get_settings
    from app.core.cache import cache_manager

    settings = get_settings()
    components = {}

    # Database status
    try:
        from sqlalchemy import text

        if db_session is not None:
            db_session.execute(text("SELECT 1"))
            components["database"] = {"status": "healthy"}
        else:
            from app.database import engine

            with engine.connect() as conn:
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


def check_readiness(
    db_session: "Session | None" = None,
) -> tuple[bool, dict[str, Any]]:
    """Check if the application is ready to receive traffic.

    Performs readiness checks on critical components to determine if
    the application can handle incoming requests. This is used by
    Kubernetes readiness probes or load balancer health checks.

    The application is considered ready when the database is healthy.
    Cache can be disabled or disconnected (degraded mode is acceptable).

    Returns:
        A tuple containing:
            - bool: True if the application is ready, False otherwise.
            - dict: Details including:
                - ready: Boolean readiness status.
                - components: Dictionary of component statuses from
                  get_component_status().
                - timestamp: ISO 8601 formatted timestamp of the check.

    Example:
        Use in a health check endpoint::

            is_ready, details = check_readiness()
            if not is_ready:
                return JSONResponse(details, status_code=503)
            return JSONResponse(details, status_code=200)
    """
    components = get_component_status(db_session)

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
    """Check if the application process is alive and responsive.

    Performs a basic liveness check to verify the application can
    respond to requests. This is used by Kubernetes liveness probes
    to detect hung or deadlocked processes.

    Unlike readiness checks, liveness checks do not verify external
    dependencies. The application is considered alive if it can
    execute this function.

    Returns:
        A tuple containing:
            - bool: Always True if the function executes successfully.
            - dict: Details including:
                - alive: Boolean liveness status (always True).
                - timestamp: ISO 8601 formatted timestamp of the check.
                - uptime_seconds: Application uptime rounded to 2 decimals.

    Example:
        Use in a liveness probe endpoint::

            is_alive, details = check_liveness()
            return JSONResponse(details, status_code=200)
    """
    # Application is alive if it can respond
    return True, {
        "alive": True,
        "timestamp": datetime.now(UTC).isoformat(),
        "uptime_seconds": round(metrics.get_uptime_seconds(), 2),
    }
