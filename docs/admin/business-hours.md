# Business Hours and Blackout Dates

Business hours and blackout dates control when resources are reservable.

## Resource business hours

- `GET /api/v1/resources/{resource_id}/business-hours`
- `PUT /api/v1/resources/{resource_id}/business-hours`

## Global business hours

- `GET /api/v1/business-hours/global`
- `PUT /api/v1/business-hours/global`

## Available slots

- `GET /api/v1/resources/{resource_id}/available-slots`
- `GET /api/v1/resources/{resource_id}/next-available`

## Blackout dates

- `GET /api/v1/resources/{resource_id}/blackout-dates`
- `POST /api/v1/resources/{resource_id}/blackout-dates`
- `GET /api/v1/blackout-dates`
- `POST /api/v1/blackout-dates`
- `DELETE /api/v1/blackout-dates/{blackout_id}`

Notes:

- Creating or updating hours and blackout dates requires admin permission
