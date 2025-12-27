"""Calendar integration endpoints for iCal feeds.

This module provides RESTful API endpoints for calendar integration functionality,
enabling users to subscribe to their reservation calendars using standard iCal
format. It supports both token-based public access for calendar applications
and authenticated endpoints for direct API usage.

Features:
    - iCal subscription URL generation for calendar app integration
    - Token-based public calendar feed access (compatible with Google Calendar,
      Apple Calendar, Outlook, and other calendar applications)
    - Single reservation export as .ics file
    - Secure token regeneration for subscription URL management
    - Configurable date range for historical and future reservations
    - Authenticated calendar feed download for direct API access

Example Usage:
    Subscribe to calendar in Google Calendar:
        1. Call GET /api/v1/calendar/subscription-url to obtain the subscription URL
        2. In Google Calendar, select "Add calendar" -> "From URL"
        3. Paste the subscription URL and confirm

    Download a single reservation:
        GET /api/v1/calendar/export/123.ics
        -> Downloads reservation ID 123 as an .ics file

    Regenerate token (invalidates old subscription URL):
        POST /api/v1/calendar/regenerate-token
        -> Returns new token and subscription URL

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
    """Response model containing calendar subscription URL and token.

    Attributes:
        url: The full subscription URL that can be added to calendar applications.
            This URL includes the user's unique token for authentication.
        token: The unique calendar token associated with the user's subscription.
            This token is embedded in the URL for public access authentication.
    """

    url: str
    token: str


class TokenResponse(BaseModel):
    """Response model for calendar token regeneration.

    Attributes:
        token: The newly generated calendar token. The previous token is
            invalidated and can no longer be used to access the calendar feed.
        url: The updated subscription URL containing the new token.
            Users must update their calendar subscriptions with this new URL.
    """

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
    """Retrieve iCal feed for a user using token-based authentication.

    This endpoint is publicly accessible and designed for integration with
    calendar applications that require a static URL for subscription. The
    token embedded in the URL serves as the authentication mechanism,
    eliminating the need for session-based authentication which calendar
    apps cannot provide.

    Args:
        token: Unique calendar token identifying the user. This token is
            generated when the user first requests their subscription URL
            and can be regenerated to invalidate old subscriptions.
        days_back: Number of days of historical reservations to include
            in the feed. Must be between 0 and 365. Defaults to 30.
        days_ahead: Number of days of future reservations to include
            in the feed. Must be between 1 and 365. Defaults to 90.
        db: Database session dependency injected by FastAPI.

    Returns:
        Response: An iCal-formatted response with media type "text/calendar"
            containing all reservations within the specified date range.
            The response includes appropriate headers for file download
            and cache control.

    Raises:
        HTTPException: 404 error if the provided token is invalid or does
            not correspond to any user in the system.
        HTTPException: 404 error if there is an issue generating the iCal
            content (wrapped from ValueError).
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
    """Retrieve the calendar subscription URL for the authenticated user.

    This endpoint returns a URL that can be used to subscribe to the user's
    reservation calendar in any standard calendar application. If the user
    does not already have a calendar token, one will be automatically
    generated.

    The subscription URL uses token-based authentication embedded in the
    URL path, allowing calendar applications to access the feed without
    requiring interactive authentication.

    Args:
        request: The incoming FastAPI request object, used to determine
            the base URL for constructing the full subscription URL.
        db: Database session dependency injected by FastAPI.
        current_user: The authenticated user making the request, obtained
            via the authentication dependency.

    Returns:
        SubscriptionUrlResponse: Object containing:
            - url: The full subscription URL for calendar apps
            - token: The user's calendar token

    Raises:
        HTTPException: 401 error if the user is not authenticated
            (handled by the get_current_user dependency).
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
    """Regenerate the calendar token for the authenticated user.

    This endpoint creates a new calendar token, immediately invalidating
    the previous token. Any calendar applications using the old subscription
    URL will no longer be able to access the feed and must be updated with
    the new URL.

    Use this endpoint when:
        - The subscription URL may have been compromised
        - You want to revoke access from previously shared URLs
        - You need to rotate tokens as a security measure

    Args:
        request: The incoming FastAPI request object, used to determine
            the base URL for constructing the updated subscription URL.
        db: Database session dependency injected by FastAPI.
        current_user: The authenticated user making the request, obtained
            via the authentication dependency.

    Returns:
        TokenResponse: Object containing:
            - token: The newly generated calendar token
            - url: The updated subscription URL with the new token

    Raises:
        HTTPException: 401 error if the user is not authenticated
            (handled by the get_current_user dependency).
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
    """Export a single reservation as an iCal (.ics) file.

    This endpoint allows users to download a specific reservation as a
    standalone .ics file, which can be imported into any calendar
    application. Unlike the subscription feed, this creates a one-time
    download that will not automatically update.

    This is useful when:
        - A user wants to add a single event without subscribing
        - Sharing a specific reservation with others
        - Creating a backup of a particular reservation

    Args:
        reservation_id: The unique identifier of the reservation to export.
            Must be a positive integer corresponding to an existing
            reservation owned by the authenticated user.
        db: Database session dependency injected by FastAPI.
        current_user: The authenticated user making the request, obtained
            via the authentication dependency. The user must own the
            reservation to export it.

    Returns:
        Response: An iCal-formatted response with media type "text/calendar"
            containing the single reservation event. The filename in the
            Content-Disposition header includes the reservation ID.

    Raises:
        HTTPException: 401 error if the user is not authenticated
            (handled by the get_current_user dependency).
        HTTPException: 404 error if the reservation does not exist or
            does not belong to the authenticated user.
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
    """Retrieve iCal feed for the authenticated user.

    This endpoint provides an authenticated alternative to the token-based
    feed endpoint. It is useful for direct API access when the client can
    provide authentication headers, such as when downloading the calendar
    via a script or API client.

    Unlike the token-based endpoint (/feed/{token}.ics), this endpoint
    requires standard authentication and cannot be used with calendar
    applications that only support static URLs.

    Args:
        days_back: Number of days of historical reservations to include
            in the feed. Must be between 0 and 365. Defaults to 30.
        days_ahead: Number of days of future reservations to include
            in the feed. Must be between 1 and 365. Defaults to 90.
        db: Database session dependency injected by FastAPI.
        current_user: The authenticated user making the request, obtained
            via the authentication dependency.

    Returns:
        Response: An iCal-formatted response with media type "text/calendar"
            containing all reservations within the specified date range.
            The response includes a Content-Disposition header for file
            download.

    Raises:
        HTTPException: 401 error if the user is not authenticated
            (handled by the get_current_user dependency).
        HTTPException: 404 error if there is an issue generating the iCal
            content (wrapped from ValueError).
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
