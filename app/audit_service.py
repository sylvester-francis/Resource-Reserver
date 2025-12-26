"""Audit logging service for tracking system actions.

Provides functionality for:
- Logging user actions with context
- Querying audit logs with filters
- Exporting audit logs (CSV, JSON)
- Retention policy management

Author: Sylvester-Francis
"""

import csv
import json
import logging
from datetime import UTC, datetime, timedelta
from io import StringIO
from typing import Any

from fastapi import Request
from sqlalchemy import and_, func
from sqlalchemy.orm import Session

from app import models

logger = logging.getLogger(__name__)


def utcnow():
    """Get current UTC datetime."""
    return datetime.now(UTC)


class AuditService:
    """Service for audit log operations."""

    def __init__(self, db: Session):
        self.db = db

    def log_action(
        self,
        action: str,
        entity_type: str,
        entity_id: int | None = None,
        entity_name: str | None = None,
        user_id: int | None = None,
        username: str | None = None,
        request: Request | None = None,
        old_values: dict | None = None,
        new_values: dict | None = None,
        details: str | None = None,
        success: bool = True,
        error_message: str | None = None,
    ) -> models.AuditLog:
        """Log an action to the audit log.

        Args:
            action: Action type (create, update, delete, login, etc.)
            entity_type: Type of entity (reservation, resource, user, etc.)
            entity_id: ID of the affected entity
            entity_name: Human-readable name of the entity
            user_id: ID of the user performing the action
            username: Username (denormalized for history)
            request: FastAPI request object for context
            old_values: Previous state of the entity
            new_values: New state of the entity
            details: Human-readable description
            success: Whether the action was successful
            error_message: Error message if action failed

        Returns:
            The created AuditLog entry
        """
        # Extract request context
        ip_address = None
        user_agent = None
        request_method = None
        request_path = None

        if request:
            # Get client IP (handle proxies)
            forwarded_for = request.headers.get("X-Forwarded-For")
            if forwarded_for:
                ip_address = forwarded_for.split(",")[0].strip()
            else:
                ip_address = request.client.host if request.client else None

            user_agent = request.headers.get("User-Agent", "")[:500]
            request_method = request.method
            request_path = str(request.url.path)[:500]

        audit_log = models.AuditLog(
            user_id=user_id,
            username=username,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            entity_name=entity_name,
            ip_address=ip_address,
            user_agent=user_agent,
            request_method=request_method,
            request_path=request_path,
            old_values=old_values,
            new_values=new_values,
            details=details,
            success=success,
            error_message=error_message,
        )

        self.db.add(audit_log)
        self.db.commit()
        self.db.refresh(audit_log)

        logger.info(
            f"Audit: {action} on {entity_type}:{entity_id} by user:{user_id} - "
            f"{'success' if success else 'failed'}"
        )

        return audit_log

    def get_logs(
        self,
        user_id: int | None = None,
        action: str | None = None,
        entity_type: str | None = None,
        entity_id: int | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        success: bool | None = None,
        ip_address: str | None = None,
        search: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[list[models.AuditLog], int]:
        """Query audit logs with filters.

        Args:
            user_id: Filter by user ID
            action: Filter by action type
            entity_type: Filter by entity type
            entity_id: Filter by entity ID
            start_date: Filter by start timestamp
            end_date: Filter by end timestamp
            success: Filter by success status
            ip_address: Filter by IP address
            search: Full-text search in details/entity_name
            skip: Pagination offset
            limit: Pagination limit

        Returns:
            Tuple of (logs list, total count)
        """
        query = self.db.query(models.AuditLog)
        filters = []

        if user_id is not None:
            filters.append(models.AuditLog.user_id == user_id)

        if action:
            filters.append(models.AuditLog.action == action)

        if entity_type:
            filters.append(models.AuditLog.entity_type == entity_type)

        if entity_id is not None:
            filters.append(models.AuditLog.entity_id == entity_id)

        if start_date:
            filters.append(models.AuditLog.timestamp >= start_date)

        if end_date:
            filters.append(models.AuditLog.timestamp <= end_date)

        if success is not None:
            filters.append(models.AuditLog.success == success)

        if ip_address:
            filters.append(models.AuditLog.ip_address == ip_address)

        if search:
            search_pattern = f"%{search}%"
            filters.append(
                (models.AuditLog.details.ilike(search_pattern))
                | (models.AuditLog.entity_name.ilike(search_pattern))
                | (models.AuditLog.username.ilike(search_pattern))
            )

        if filters:
            query = query.filter(and_(*filters))

        total = query.count()
        logs = (
            query.order_by(models.AuditLog.timestamp.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

        return logs, total

    def get_log_by_id(self, log_id: int) -> models.AuditLog | None:
        """Get a single audit log entry by ID."""
        return (
            self.db.query(models.AuditLog).filter(models.AuditLog.id == log_id).first()
        )

    def get_entity_history(
        self, entity_type: str, entity_id: int, limit: int = 50
    ) -> list[models.AuditLog]:
        """Get audit history for a specific entity."""
        return (
            self.db.query(models.AuditLog)
            .filter(
                models.AuditLog.entity_type == entity_type,
                models.AuditLog.entity_id == entity_id,
            )
            .order_by(models.AuditLog.timestamp.desc())
            .limit(limit)
            .all()
        )

    def get_user_activity(
        self, user_id: int, days: int = 30, limit: int = 100
    ) -> list[models.AuditLog]:
        """Get recent activity for a user."""
        since = utcnow() - timedelta(days=days)
        return (
            self.db.query(models.AuditLog)
            .filter(
                models.AuditLog.user_id == user_id,
                models.AuditLog.timestamp >= since,
            )
            .order_by(models.AuditLog.timestamp.desc())
            .limit(limit)
            .all()
        )

    def get_action_statistics(
        self, start_date: datetime | None = None, end_date: datetime | None = None
    ) -> dict[str, Any]:
        """Get statistics about audit log actions."""
        query = self.db.query(models.AuditLog)

        if start_date:
            query = query.filter(models.AuditLog.timestamp >= start_date)
        if end_date:
            query = query.filter(models.AuditLog.timestamp <= end_date)

        # Action counts
        action_counts = (
            query.with_entities(models.AuditLog.action, func.count(models.AuditLog.id))
            .group_by(models.AuditLog.action)
            .all()
        )

        # Entity type counts
        entity_counts = (
            query.with_entities(
                models.AuditLog.entity_type, func.count(models.AuditLog.id)
            )
            .group_by(models.AuditLog.entity_type)
            .all()
        )

        # Success/failure counts
        success_counts = (
            query.with_entities(models.AuditLog.success, func.count(models.AuditLog.id))
            .group_by(models.AuditLog.success)
            .all()
        )

        # Most active users
        active_users = (
            query.with_entities(
                models.AuditLog.username, func.count(models.AuditLog.id)
            )
            .filter(models.AuditLog.username.isnot(None))
            .group_by(models.AuditLog.username)
            .order_by(func.count(models.AuditLog.id).desc())
            .limit(10)
            .all()
        )

        return {
            "by_action": dict(action_counts),
            "by_entity_type": dict(entity_counts),
            "by_success": {
                "success": next((c for s, c in success_counts if s), 0),
                "failed": next((c for s, c in success_counts if not s), 0),
            },
            "most_active_users": [
                {"username": username, "action_count": count}
                for username, count in active_users
            ],
            "total_entries": query.count(),
        }

    def export_to_csv(
        self,
        user_id: int | None = None,
        action: str | None = None,
        entity_type: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> str:
        """Export audit logs to CSV format."""
        logs, _ = self.get_logs(
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            start_date=start_date,
            end_date=end_date,
            limit=10000,  # Max export limit
        )

        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(
            [
                "id",
                "timestamp",
                "user_id",
                "username",
                "action",
                "entity_type",
                "entity_id",
                "entity_name",
                "ip_address",
                "request_method",
                "request_path",
                "success",
                "details",
                "error_message",
            ]
        )

        for log in logs:
            writer.writerow(
                [
                    log.id,
                    log.timestamp.isoformat() if log.timestamp else "",
                    log.user_id or "",
                    log.username or "",
                    log.action,
                    log.entity_type,
                    log.entity_id or "",
                    log.entity_name or "",
                    log.ip_address or "",
                    log.request_method or "",
                    log.request_path or "",
                    log.success,
                    log.details or "",
                    log.error_message or "",
                ]
            )

        return output.getvalue()

    def export_to_json(
        self,
        user_id: int | None = None,
        action: str | None = None,
        entity_type: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> str:
        """Export audit logs to JSON format."""
        logs, total = self.get_logs(
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            start_date=start_date,
            end_date=end_date,
            limit=10000,
        )

        data = {
            "total": total,
            "exported_at": utcnow().isoformat(),
            "logs": [
                {
                    "id": log.id,
                    "timestamp": log.timestamp.isoformat() if log.timestamp else None,
                    "user_id": log.user_id,
                    "username": log.username,
                    "action": log.action,
                    "entity_type": log.entity_type,
                    "entity_id": log.entity_id,
                    "entity_name": log.entity_name,
                    "ip_address": log.ip_address,
                    "user_agent": log.user_agent,
                    "request_method": log.request_method,
                    "request_path": log.request_path,
                    "old_values": log.old_values,
                    "new_values": log.new_values,
                    "details": log.details,
                    "success": log.success,
                    "error_message": log.error_message,
                }
                for log in logs
            ],
        }

        return json.dumps(data, indent=2)

    def apply_retention_policy(self, retention_days: int = 90) -> int:
        """Delete audit logs older than retention period.

        Args:
            retention_days: Number of days to retain logs

        Returns:
            Number of deleted entries
        """
        cutoff_date = utcnow() - timedelta(days=retention_days)

        deleted_count = (
            self.db.query(models.AuditLog)
            .filter(models.AuditLog.timestamp < cutoff_date)
            .delete(synchronize_session=False)
        )

        self.db.commit()

        logger.info(
            f"Audit log retention policy applied: deleted {deleted_count} entries "
            f"older than {retention_days} days"
        )

        return deleted_count

    def get_available_actions(self) -> list[str]:
        """Get list of all unique actions in audit logs."""
        results = (
            self.db.query(models.AuditLog.action)
            .distinct()
            .order_by(models.AuditLog.action)
            .all()
        )
        return [r[0] for r in results]

    def get_available_entity_types(self) -> list[str]:
        """Get list of all unique entity types in audit logs."""
        results = (
            self.db.query(models.AuditLog.entity_type)
            .distinct()
            .order_by(models.AuditLog.entity_type)
            .all()
        )
        return [r[0] for r in results]


def get_audit_context(request: Request, user: models.User | None = None) -> dict:
    """Helper to extract audit context from request."""
    context = {
        "request": request,
    }

    if user:
        context["user_id"] = user.id
        context["username"] = user.username

    return context
