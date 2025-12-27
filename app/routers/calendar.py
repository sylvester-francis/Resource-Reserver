"""Calendar integration endpoints for iCal feeds.

Provides endpoints for:
- Getting iCal subscription URL
- Downloading iCal feed
- Downloading single reservation as .ics
- Managing calendar tokens

Author: Sylvester-Francis
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app import models
from app.auth import get_current_user
from app.calendar_service import CalendarService
from app.database import get_db

router = APIRouter(prefix="/api/v1/calendar", tags=["calendar"])


class SubscriptionUrlResponse(BaseModel):
    """Response with calendar subscription URL."""

    url: str
    token: str


class TokenResponse(BaseModel):
    """Response with new calendar token."""

    token: str
    url: str


# ============================================================================
# Public Endpoints (Token-based authentication)
# ============================================================================


@router.get("/feed/{token}.ics")
async def get_calendar_feed(
    token: str,
    days_back: int = Query(30, ge=0, le=365, description="Days of history to include"),
    days_ahead: int = Query(90, ge=1, le=365, description="Days ahead to include"),
    db: Session = Depends(get_db),
):
    """Get iCal feed for a user (public with token auth).

    This endpoint is publicly accessible but requires a valid calendar token.
    The token is included in the URL for compatibility with calendar apps.
    """
    service = CalendarService(db)
    user = service.get_user_by_token(token)

    if not user:
        raise HTTPException(status_code=404, detail="Invalid calendar token")

    try:
        ical_content = service.generate_ical_feed(user.id, days_back, days_ahead)
        return Response(
            content=ical_content,
            media_type="text/calendar",
            headers={
                "Content-Disposition": "attachment; filename=reservations.ics",
                "Cache-Control": "no-cache, must-revalidate",
            },
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


# ============================================================================
# Authenticated Endpoints
# ============================================================================


@router.get("/subscription-url", response_model=SubscriptionUrlResponse)
async def get_subscription_url(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Get the calendar subscription URL for the current user.

    Returns a URL that can be used to subscribe to the calendar
    in Google Calendar, Apple Calendar, Outlook, etc.
    """
    service = CalendarService(db)
    token = service.get_or_create_token(current_user.id)
    url = service.get_subscription_url(current_user.id, base_url=str(request.base_url))

    return SubscriptionUrlResponse(url=url, token=token)


@router.post("/regenerate-token", response_model=TokenResponse)
async def regenerate_calendar_token(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Regenerate the calendar token.

    This invalidates the old subscription URL. Users will need to
    update their calendar subscriptions with the new URL.
    """
    service = CalendarService(db)
    token = service.regenerate_token(current_user.id)
    url = service.get_subscription_url(current_user.id, base_url=str(request.base_url))

    return TokenResponse(token=token, url=url)


@router.get("/export/{reservation_id}.ics")
async def export_reservation(
    reservation_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Download a single reservation as an .ics file.

    This allows users to add a specific reservation to their calendar
    without subscribing to the full feed.
    """
    service = CalendarService(db)

    try:
        ical_content = service.generate_single_event(reservation_id, current_user.id)
        return Response(
            content=ical_content,
            media_type="text/calendar",
            headers={
                "Content-Disposition": f"attachment; filename=reservation-{reservation_id}.ics",
            },
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.get("/my-feed")
async def get_my_calendar_feed(
    days_back: int = Query(30, ge=0, le=365, description="Days of history to include"),
    days_ahead: int = Query(90, ge=1, le=365, description="Days ahead to include"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Get iCal feed for the current user (authenticated).

    This is an authenticated alternative to the token-based feed endpoint.
    Useful for direct download via the API.
    """
    service = CalendarService(db)

    try:
        ical_content = service.generate_ical_feed(
            current_user.id, days_back, days_ahead
        )
        return Response(
            content=ical_content,
            media_type="text/calendar",
            headers={
                "Content-Disposition": "attachment; filename=reservations.ics",
            },
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
