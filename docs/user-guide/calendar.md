# Calendar

Resource Reserver provides iCal feeds so you can see reservations in your calendar app.

## Subscribe to your calendar

1. Get your subscription URL in the UI or via the API
1. Add the URL in your calendar app

API endpoint:

- `GET /api/v1/calendar/subscription-url`

The subscription URL points to:

- `GET /api/v1/calendar/feed/{token}.ics`

## Regenerate the token

If your URL is shared or compromised, regenerate it:

- `POST /api/v1/calendar/regenerate-token`

## Export a single reservation

Download one reservation as an `.ics` file:

- `GET /api/v1/calendar/export/{reservation_id}.ics`
