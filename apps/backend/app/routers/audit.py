"""Audit log endpoints for admin access.

Provides endpoints for:
- Querying audit logs with filters
- Viewing entity history
- Exporting logs (CSV, JSON)
- Viewing statistics
- Managing retention policies

Author: Sylvester-Francis
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app import models
from app.audit_service import AuditService
from app.auth import get_current_user
from app.database import get_db
from app.rbac import require_role

router = APIRouter(prefix="/api/v1/audit", tags=["audit"])


# ============================================================================
# Schemas
# ============================================================================


class AuditLogResponse(BaseModel):
    """Response schema for audit log entry."""

    id: int
    timestamp: datetime
    user_id: int | None
    username: str | None
    action: str
    entity_type: str
    entity_id: int | None
    entity_name: str | None
    ip_address: str | None
    user_agent: str | None
    request_method: str | None
    request_path: str | None
    old_values: dict | None
    new_values: dict | None
    details: str | None
    success: bool
    error_message: str | None

    model_config = {"from_attributes": True}


class AuditLogListResponse(BaseModel):
    """Paginated list of audit logs."""

    logs: list[AuditLogResponse]
    total: int
    skip: int
    limit: int


class AuditStatisticsResponse(BaseModel):
    """Audit log statistics."""

    by_action: dict[str, int]
    by_entity_type: dict[str, int]
    by_success: dict[str, int]
    most_active_users: list[dict]
    total_entries: int


class RetentionPolicyRequest(BaseModel):
    """Request for applying retention policy."""

    retention_days: int = Field(90, ge=1, le=365, description="Days to retain logs")


class RetentionPolicyResponse(BaseModel):
    """Response after applying retention policy."""

    deleted_count: int
    retention_days: int
    message: str


class AvailableFiltersResponse(BaseModel):
    """Available filter options."""

    actions: list[str]
    entity_types: list[str]


# ============================================================================
# Endpoints
# ============================================================================


@router.get("/logs", response_model=AuditLogListResponse)
def get_audit_logs(
    request: Request,
    user_id: int | None = Query(None, description="Filter by user ID"),
    action: str | None = Query(None, description="Filter by action type"),
    entity_type: str | None = Query(None, description="Filter by entity type"),
    entity_id: int | None = Query(None, description="Filter by entity ID"),
    start_date: datetime | None = Query(None, description="Filter from date"),
    end_date: datetime | None = Query(None, description="Filter until date"),
    success: bool | None = Query(None, description="Filter by success status"),
    ip_address: str | None = Query(None, description="Filter by IP address"),
    search: str | None = Query(None, description="Search in details/entity name"),
    skip: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(100, ge=1, le=1000, description="Pagination limit"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role("admin")),
):
    """Get audit logs with optional filters.

    Requires admin role.
    """
    service = AuditService(db)
    logs, total = service.get_logs(
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        start_date=start_date,
        end_date=end_date,
        success=success,
        ip_address=ip_address,
        search=search,
        skip=skip,
        limit=limit,
    )

    return AuditLogListResponse(
        logs=[AuditLogResponse.model_validate(log) for log in logs],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/logs/{log_id}", response_model=AuditLogResponse)
def get_audit_log(
    log_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role("admin")),
):
    """Get a specific audit log entry.

    Requires admin role.
    """
    service = AuditService(db)
    log = service.get_log_by_id(log_id)

    if not log:
        raise HTTPException(status_code=404, detail="Audit log entry not found")

    return AuditLogResponse.model_validate(log)


@router.get("/entity/{entity_type}/{entity_id}", response_model=list[AuditLogResponse])
def get_entity_history(
    entity_type: str,
    entity_id: int,
    request: Request,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role("admin")),
):
    """Get audit history for a specific entity.

    Requires admin role.
    """
    service = AuditService(db)
    logs = service.get_entity_history(entity_type, entity_id, limit)

    return [AuditLogResponse.model_validate(log) for log in logs]


@router.get("/user/{user_id}/activity", response_model=list[AuditLogResponse])
def get_user_activity(
    user_id: int,
    request: Request,
    days: int = Query(30, ge=1, le=365),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role("admin")),
):
    """Get recent activity for a specific user.

    Requires admin role.
    """
    service = AuditService(db)
    logs = service.get_user_activity(user_id, days, limit)

    return [AuditLogResponse.model_validate(log) for log in logs]


@router.get("/my-activity", response_model=list[AuditLogResponse])
def get_my_activity(
    request: Request,
    days: int = Query(30, ge=1, le=365),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Get your own recent activity.

    Available to all authenticated users.
    """
    service = AuditService(db)
    logs = service.get_user_activity(current_user.id, days, limit)

    return [AuditLogResponse.model_validate(log) for log in logs]


@router.get("/statistics", response_model=AuditStatisticsResponse)
def get_audit_statistics(
    request: Request,
    start_date: datetime | None = Query(None),
    end_date: datetime | None = Query(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role("admin")),
):
    """Get audit log statistics.

    Requires admin role.
    """
    service = AuditService(db)
    stats = service.get_action_statistics(start_date, end_date)

    return AuditStatisticsResponse(**stats)


@router.get("/export/csv")
def export_audit_logs_csv(
    request: Request,
    user_id: int | None = Query(None),
    action: str | None = Query(None),
    entity_type: str | None = Query(None),
    start_date: datetime | None = Query(None),
    end_date: datetime | None = Query(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role("admin")),
):
    """Export audit logs to CSV file.

    Requires admin role. Maximum 10,000 entries.
    """
    service = AuditService(db)
    csv_content = service.export_to_csv(
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        start_date=start_date,
        end_date=end_date,
    )

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=audit_logs.csv"},
    )


@router.get("/export/json")
def export_audit_logs_json(
    request: Request,
    user_id: int | None = Query(None),
    action: str | None = Query(None),
    entity_type: str | None = Query(None),
    start_date: datetime | None = Query(None),
    end_date: datetime | None = Query(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role("admin")),
):
    """Export audit logs to JSON file.

    Requires admin role. Maximum 10,000 entries.
    """
    service = AuditService(db)
    json_content = service.export_to_json(
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        start_date=start_date,
        end_date=end_date,
    )

    return Response(
        content=json_content,
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=audit_logs.json"},
    )


@router.get("/filters", response_model=AvailableFiltersResponse)
def get_available_filters(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role("admin")),
):
    """Get available filter options for audit logs.

    Requires admin role.
    """
    service = AuditService(db)

    return AvailableFiltersResponse(
        actions=service.get_available_actions(),
        entity_types=service.get_available_entity_types(),
    )


@router.post("/retention", response_model=RetentionPolicyResponse)
def apply_retention_policy(
    data: RetentionPolicyRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role("admin")),
):
    """Apply retention policy to delete old audit logs.

    Requires admin role.

    WARNING: This action is irreversible.
    """
    service = AuditService(db)

    # Log this action itself
    service.log_action(
        action="apply_retention",
        entity_type="audit_log",
        user_id=current_user.id,
        username=current_user.username,
        request=request,
        details=f"Applying {data.retention_days}-day retention policy",
    )

    deleted_count = service.apply_retention_policy(data.retention_days)

    return RetentionPolicyResponse(
        deleted_count=deleted_count,
        retention_days=data.retention_days,
        message=f"Successfully deleted {deleted_count} audit log entries older than {data.retention_days} days",
    )
