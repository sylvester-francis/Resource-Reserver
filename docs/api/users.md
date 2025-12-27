# Users API

## User profile

- `GET /api/v1/users/me` - profile and settings
- `PATCH /api/v1/users/me/preferences` - notification preferences

## Notifications

- `GET /api/v1/notifications` - list notifications
- `POST /api/v1/notifications/{notification_id}/read` - mark one as read
- `POST /api/v1/notifications/mark-all-read` - mark all as read

## Saved searches

- `GET /api/v1/search/saved` - list saved searches
- `POST /api/v1/search/saved` - create a saved search
- `DELETE /api/v1/search/saved/{search_id}` - delete a saved search
- `POST /api/v1/search/saved/{search_id}/execute` - run a saved search
