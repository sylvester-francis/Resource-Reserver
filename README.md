# Resource Reserver

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat&logo=python&logoColor=white)](https://www.python.org/) [![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/) [![Next.js](https://img.shields.io/badge/Next.js-15+-000000?style=flat&logo=next.js&logoColor=white)](https://nextjs.org/) [![TypeScript](https://img.shields.io/badge/TypeScript-5.0+-3178C6?style=flat&logo=typescript&logoColor=white)](https://www.typescriptlang.org/) [![SQLite](https://img.shields.io/badge/SQLite-003B57?style=flat&logo=sqlite&logoColor=white)](https://www.sqlite.org/) [![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?style=flat&logo=postgresql&logoColor=white)](https://www.postgresql.org/) [![Redis](https://img.shields.io/badge/Redis-DC382D?style=flat&logo=redis&logoColor=white)](https://redis.io/) [![Docker](https://img.shields.io/badge/Docker-2496ED?style=flat&logo=docker&logoColor=white)](https://www.docker.com/) [![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-06B6D4?style=flat&logo=tailwind-css&logoColor=white)](https://tailwindcss.com/) [![JWT](https://img.shields.io/badge/JWT-000000?style=flat&logo=json-web-tokens&logoColor=white)](https://jwt.io/) [![WebSocket](https://img.shields.io/badge/WebSocket-010101?style=flat&logo=websocket&logoColor=white)](https://developer.mozilla.org/en-US/docs/Web/API/WebSockets_API) [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Resource Reserver is a booking system that prevents double-booking of shared assets such as rooms, equipment, labs, or desks. It includes a web app for daily use, a CLI for automation, and a FastAPI backend for integrations.

This README is the single source of documentation for this repository. It is written for both non-technical and technical readers.

## Contents

- Overview
- Features
- Glossary
- Quick Start (No Technical Knowledge Required)
- Quick Start (Developers)
- Architecture
- Screenshots
- Web App Guide
- Admin and Operations Guide
- CLI Guide
- API Guide
- Configuration
- Data Import and Export
- Operations and Monitoring
- Testing
- Troubleshooting
- License

## Overview

Resource Reserver lets teams share resources without collisions. Users can check availability, reserve time, join waitlists when resources are busy, and subscribe to calendar feeds. Admins can manage access, approvals, quotas, and integrations.

## Features

- Resource catalog with tags, status, groups, and hierarchy.
- Availability rules: business hours, blackout dates, available slots, and next available.
- Reservations with conflict detection, recurring schedules, and approval workflow.
- Waitlist with offers and acceptance.
- Calendar integration (subscription URL, personal feed, per-reservation export).
- Notifications center, email reminders, and WebSocket live updates.
- Analytics dashboards and CSV exports.
- Audit logs with filters and export.
- Webhooks with HMAC signing, retries, and delivery history.
- Security: JWT auth, refresh tokens, MFA, password policy, RBAC roles, OAuth2 clients.
- Rate limiting, quotas, metrics, and health checks.
- PWA support (offline page and asset caching) and multi-language UI (en, es, fr).

## Glossary

- Resource: The item you can reserve (room, desk, equipment).
- Reservation: A confirmed time slot on a resource.
- Waitlist: A queue for a resource when your desired time is not available.
- Business hours: Allowed hours for reservations.
- Blackout date: A date when reservations are not allowed.
- Approval: A review step for resources that require approval before a reservation becomes active.
- Quota: Limits on API usage and rate limits per user or tier.

## Quick Start (No Technical Knowledge Required)

This option uses Docker to run everything.

1. Install Docker Desktop:

   - Mac/Windows: https://www.docker.com/products/docker-desktop
   - Linux: https://docs.docker.com/engine/install/

1. Get the project folder:

   - If you already have the folder, skip this step.
   - Option A (download): download the project ZIP, unzip it, and open the folder.
   - Option B (git): `git clone <repo-url>` then `cd Resource-Reserver`

1. Open a terminal and go to the project folder:

```bash
cd Resource-Reserver
```

4. Start the app:

```bash
docker compose up -d
```

5. Open the app:

- Web app: http://localhost:3000
- API docs: http://localhost:8000/docs

6. Create the first admin account:

- Visit http://localhost:3000/setup and follow the prompts.

7. Add resources and make a reservation.

To stop everything:

```bash
docker compose down
```

## Quick Start (Developers)

### Option A: Docker Compose (production-like)

```bash
docker compose up -d --build
```

Default ports:

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000

By default the backend uses SQLite. To use PostgreSQL instead:

1. Start the postgres profile:

```bash
docker compose --profile postgres up -d --build
```

2. Set `DATABASE_URL` for the backend:

- In Docker: `DATABASE_URL=postgresql://postgres:postgres@postgres:5432/resource_reserver`
- On your host: `DATABASE_URL=postgresql://postgres:postgres@localhost:5432/resource_reserver`

### Option B: Docker Compose dev profile (hot reload)

```bash
docker compose --profile dev up --build
```

Ports in dev profile:

- Backend (hot reload): http://localhost:8001
- Frontend (hot reload): http://localhost:3001

### Option C: Local development

Prerequisites:

- Python 3.11+
- Node 20+ and npm

Backend:

```bash
python -m venv venv
source venv/bin/activate
pip install -r apps/backend/requirements.txt
uvicorn --app-dir apps/backend app.main:app --reload --host 0.0.0.0 --port 8000
```

Frontend:

```bash
cd apps/frontend
npm ci
printf "NEXT_PUBLIC_API_URL=http://localhost:8000\n" > .env.local
npm run dev
```

CLI:

```bash
pip install -e apps/backend
resource-reserver-cli auth register
resource-reserver-cli auth login
```

### Optional: mise shortcuts

If you use `mise`, these tasks are already defined:

```bash
mise run up
mise run dev
mise run test
mise run lint
mise run format
mise run build
mise run help
```

### Optional: one-command dev script

```bash
./dev
```

The script installs mise if needed, sets up dependencies, and starts dev servers.

## Architecture

### System Overview

```mermaid
flowchart LR
    User[User Browser] --> Web[Next.js Web App]
    CLI[CLI User] --> API[FastAPI API]
    Web --> API
    API --> DB[(Database)]
    API --> Redis[(Redis Cache)]
    API --> WS[WebSocket /ws]
    API --> Email[SMTP Email]
    API --> Hooks[Webhook Targets]
```

### Reservation, Approval, and Waitlist Flow

```mermaid
sequenceDiagram
    participant User
    participant UI
    participant API
    participant DB
    participant Approver
    participant WS

    User->>UI: Request reservation
    UI->>API: POST /api/v1/reservations
    alt Resource requires approval
        API->>DB: Create reservation (pending_approval)
        API->>WS: approval_request
        Approver->>API: POST /api/v1/approvals/{id}/respond
        API->>DB: Update reservation status
        API->>WS: reservation_approved or reservation_rejected
    else Available
        API->>DB: Create reservation (active)
        API->>WS: reservation_created
    end

    opt Resource is busy
        UI->>API: POST /api/v1/waitlist
        API->>DB: Enqueue waitlist entry
        API->>WS: waitlist_offer (when a slot opens)
    end
```

### Deployment (Docker Compose)

```mermaid
flowchart TB
    Compose[docker compose] --> Backend[backend container :8000]
    Compose --> Frontend[frontend container :3000]
    Compose --> Redis[redis container :6379]
    Compose --> Postgres[postgres container :5432]
    Backend --> Data[(volumes)]
    Frontend --> Users[users]
```

### Data Model (Key Entities)

```mermaid
erDiagram
    USER ||--o{ RESERVATION : books
    USER ||--o{ WAITLIST : joins
    USER ||--o{ NOTIFICATION : receives
    USER ||--o{ WEBHOOK : owns
    RESOURCE_GROUP ||--o{ RESOURCE : contains
    RESOURCE ||--o{ RESERVATION : has
    RESOURCE ||--o{ WAITLIST : has
    RESOURCE ||--o{ BUSINESS_HOURS : defines
    RESOURCE ||--o{ BLACKOUT_DATE : has
    RESERVATION ||--o| APPROVAL_REQUEST : may_require
```

## Screenshots

### Web Interface

#### Authentication

|                        Login                        |                       Registration                        |
| :-------------------------------------------------: | :-------------------------------------------------------: |
| ![Login](screenshots/Web%20Interface/login-web.png) | ![Register](screenshots/Web%20Interface/register-web.png) |

#### Dashboard & System Status

|                        Dashboard                        |                           System Status                            |
| :-----------------------------------------------------: | :----------------------------------------------------------------: |
| ![Dashboard](screenshots/Web%20Interface/dashboard.png) | ![System Status](screenshots/Web%20Interface/systemstatus-web.png) |

#### Resource Management

|                           Resource List                            |                            Create Resource                             |
| :----------------------------------------------------------------: | :--------------------------------------------------------------------: |
| ![Resource List](screenshots/Web%20Interface/resourcelist-web.png) | ![Create Resource](screenshots/Web%20Interface/createresource-web.png) |

|                             Resource History                             |                            Upload Resources                             |
| :----------------------------------------------------------------------: | :---------------------------------------------------------------------: |
| ![Resource History](screenshots/Web%20Interface/resourcehistory-web.png) | ![Upload Resources](screenshots/Web%20Interface/uploadresource-web.png) |

|                            Resource Schedule                            |                               Business Hours                               |
| :---------------------------------------------------------------------: | :------------------------------------------------------------------------: |
| ![Resource Schedule](screenshots/Web%20Interface/resource-schedule.png) | ![Business Hours](screenshots/Web%20Interface/resource-business-hours.png) |

#### Reservations

|                              Create Reservation                              |                            My Reservations                             |
| :--------------------------------------------------------------------------: | :--------------------------------------------------------------------: |
| ![Create Reservation](screenshots/Web%20Interface/createreservation-web.png) | ![My Reservations](screenshots/Web%20Interface/myreservations-web.png) |

#### Waitlist

|                          Waitlist View                          |                          Join Waitlist                          |
| :-------------------------------------------------------------: | :-------------------------------------------------------------: |
| ![Waitlist View](screenshots/Web%20Interface/waitlist-view.png) | ![Join Waitlist](screenshots/Web%20Interface/waitlist-join.png) |

#### Analytics & Calendar

|                        Analytics                        |                 Calendar Integration                  |
| :-----------------------------------------------------: | :---------------------------------------------------: |
| ![Analytics](screenshots/Web%20Interface/analytics.png) | ![Calendar](screenshots/Web%20Interface/calendar.png) |

|                           Calendar Export                           |                              Calendar Subscription                              |
| :-----------------------------------------------------------------: | :-----------------------------------------------------------------------------: |
| ![Calendar Export](screenshots/Web%20Interface/calendar-export.png) | ![Calendar Subscription](screenshots/Web%20Interface/calendar-subscription.png) |

#### Notifications

|                             Notifications Panel                             |                             Notifications Empty                             |
| :-------------------------------------------------------------------------: | :-------------------------------------------------------------------------: |
| ![Notifications Panel](screenshots/Web%20Interface/notifications-panel.png) | ![Notifications Empty](screenshots/Web%20Interface/notifications-empty.png) |

#### Webhooks

|                          Webhooks List                          |                          Create Webhook                           |
| :-------------------------------------------------------------: | :---------------------------------------------------------------: |
| ![Webhooks List](screenshots/Web%20Interface/webhooks-list.png) | ![Create Webhook](screenshots/Web%20Interface/webhook-create.png) |

|                          Webhook Events                           |                           Webhook History                           |
| :---------------------------------------------------------------: | :-----------------------------------------------------------------: |
| ![Webhook Events](screenshots/Web%20Interface/webhook-events.png) | ![Webhook History](screenshots/Web%20Interface/webhook-history.png) |

#### Account & Security

|                           Account Settings                            |                        MFA Setup                        |
| :-------------------------------------------------------------------: | :-----------------------------------------------------: |
| ![Account Settings](screenshots/Web%20Interface/account-settings.png) | ![MFA Setup](screenshots/Web%20Interface/mfa-setup.png) |

#### Internationalization

|                            Language Selector                            |
| :---------------------------------------------------------------------: |
| ![Language Selector](screenshots/Web%20Interface/language-selector.png) |

#### Dark Theme

|                          Dark Dashboard                           |                          Dark Resources                           |
| :---------------------------------------------------------------: | :---------------------------------------------------------------: |
| ![Dark Dashboard](screenshots/Web%20Interface/dark-dashboard.png) | ![Dark Resources](screenshots/Web%20Interface/dark-resources.png) |

|                        Dark Login                         |                          Dark Register                          |
| :-------------------------------------------------------: | :-------------------------------------------------------------: |
| ![Dark Login](screenshots/Web%20Interface/dark-login.png) | ![Dark Register](screenshots/Web%20Interface/dark-register.png) |

|                            Dark Reservations                            |
| :---------------------------------------------------------------------: |
| ![Dark Reservations](screenshots/Web%20Interface/dark-reservations.png) |

______________________________________________________________________

### CLI Interface

|                         Overview                          |                         Authentication                          |
| :-------------------------------------------------------: | :-------------------------------------------------------------: |
| ![CLI Overview](screenshots/CLI%20Interface/cli-main.png) | ![CLI Authentication](screenshots/CLI%20Interface/cli-auth.png) |

|                            Resources                            |                             Reservations                             |
| :-------------------------------------------------------------: | :------------------------------------------------------------------: |
| ![CLI Resources](screenshots/CLI%20Interface/cli-resources.png) | ![CLI Reservations](screenshots/CLI%20Interface/cli-reservation.png) |

|                          System                           |
| :-------------------------------------------------------: |
| ![CLI System](screenshots/CLI%20Interface/cli-system.png) |

______________________________________________________________________

> 📸 **All screenshots** shown above are available in the [`screenshots`](screenshots/) directory.

## Web App Guide

### Setup and accounts

- First run: visit `/setup` to create the initial admin account.
- Register and log in from `/login` after setup is complete.
- Password rules: at least 8 characters with uppercase, lowercase, number, and special character; cannot include the username.
- Account lockout: 5 failed login attempts triggers a 15 minute lockout.
- MFA: enable or disable multi-factor authentication from the account dialog.
- Preferences: configure email notifications and reminder timing.
- Language selector: English, Spanish, and French.
- Offline support: the app registers a service worker for offline page and static asset caching.

### Dashboard and system status

- Summary cards show total resources, availability, active and upcoming reservations.
- Open the system status dialog to check health and service metrics.

### Resources

- Search, filter by status, and sort by name, status, or ID.
- Add resources with tags and availability status.
- Upload resources from CSV (see Data Import and Export).
- Reserve a resource, view its schedule, or set it to maintenance.
- Manage business hours and blackout dates for each resource.

### Reservations and calendar

- Create one-time or recurring reservations.
- View My Reservations and Upcoming reservations.
- Cancel reservations and view reservation history.
- Export calendar events as .ics or subscribe via a personal feed URL.

### Waitlist

- Join the waitlist from a resource when it is busy.
- Choose flexible time if you can accept nearby slots.
- Accept offers when a slot becomes available.

### Analytics

- View utilization, peak times, and popular resources.
- Export reservations and utilization reports as CSV.

### Webhooks

- Create and manage webhook subscriptions.
- Test webhooks and view delivery history.

### Notifications

- Open the notification center and mark items as read.

## Admin and Operations Guide

- Roles: default roles are admin, user, and guest. Manage roles at `/admin/roles`.
- Approvals: resources can require approval; manage settings via `/api/v1/approvals/resources/{resource_id}/settings`.
- Resource groups: build hierarchies and assign resources via `/api/v1/resource-groups`.
- Quotas and rate limits: view and manage via `/api/v1/quotas` (admin endpoints require admin role).
- Audit logs: view, filter, and export via `/api/v1/audit`.
- Setup reopen: set `SETUP_REOPEN_TOKEN` and call `/setup/unlock` with header `X-Setup-Token`.

Some admin operations are API-only and are not surfaced in the UI yet.

## CLI Guide

Install the CLI:

```bash
pip install -e apps/backend
```

Configuration:

- API base URL uses `API_URL` (default: http://localhost:8000)
- Tokens are stored in `~/.reservation-cli` (override with `CLI_CONFIG_DIR`)

Common commands:

```bash
resource-reserver-cli commands
resource-reserver-cli auth register
resource-reserver-cli auth login
resource-reserver-cli auth logout
resource-reserver-cli resources list --details
resource-reserver-cli reservations create 12 "2025-01-10 09:00" "2025-01-10 10:00"
resource-reserver-cli waitlist join --resource 12 --start "2025-01-10 09:00" --end "2025-01-10 10:00"
resource-reserver-cli mfa setup
resource-reserver-cli mfa enable
resource-reserver-cli roles list
resource-reserver-cli oauth list
```

## API Guide

Base URL: `http://localhost:8000/api/v1`

Authentication:

- Register: `POST /api/v1/register`
- Login (form data): `POST /api/v1/token`
- Refresh: `POST /api/v1/token/refresh`
- Logout: `POST /api/v1/logout`
- Current user: `GET /api/v1/users/me`
- Preferences: `PATCH /api/v1/users/me/preferences`

Example login:

```bash
curl -X POST http://localhost:8000/api/v1/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=user1&password=password"
```

Time formats:

- Use ISO-8601 with timezone (example: `2025-01-10T09:00:00Z`).

WebSocket:

- Connect to `ws://localhost:8000/ws?token=<JWT>`.
- Event types: `resource_status_changed`, `reservation_created`, `reservation_cancelled`, `waitlist_offer`, `approval_request`, `reservation_approved`, `reservation_rejected`.

Webhook events (examples):

- `reservation.created`, `reservation.cancelled`, `reservation.updated`, `reservation.expired`
- `resource.created`, `resource.updated`, `resource.deleted`, `resource.unavailable`, `resource.available`
- `user.created`, `waitlist.offer`, `waitlist.accepted`, `waitlist.expired`

Endpoint map (key groups and examples):

- System: `/health`, `/ready`, `/live`, `/metrics`, `/api/versions`, `/api/v1/metrics/summary`
- Resources: `/api/v1/resources`, `/api/v1/resources/search`, `/api/v1/resources/upload`
- Reservations: `/api/v1/reservations`, `/api/v1/reservations/recurring`, `/api/v1/reservations/my`
- Availability: `/api/v1/resources/{id}/business-hours`, `/api/v1/resources/{id}/available-slots`, `/api/v1/resources/{id}/blackout-dates`
- Waitlist: `/api/v1/waitlist`, `/api/v1/waitlist/{id}`, `/api/v1/waitlist/{id}/accept`
- Calendar: `/api/v1/calendar/subscription-url`, `/api/v1/calendar/feed/{token}.ics`, `/api/v1/calendar/export/{id}.ics`
- Notifications: `/api/v1/notifications`, `/api/v1/notifications/{id}/read`
- Analytics: `/api/v1/analytics/dashboard`, `/api/v1/analytics/utilization`, `/api/v1/analytics/export/utilization.csv`
- Approvals: `/api/v1/approvals/pending`, `/api/v1/approvals/{id}/respond`
- Resource groups: `/api/v1/resource-groups`, `/api/v1/resource-groups/tree`
- Search: `/api/v1/search/resources`, `/api/v1/search/reservations`, `/api/v1/search/saved`
- Bulk ops: `/api/v1/bulk/reservations`, `/api/v1/bulk/reservations/import`, `/api/v1/bulk/reservations/export`
- Webhooks: `/api/v1/webhooks`, `/api/v1/webhooks/events`, `/api/v1/webhooks/{id}/deliveries`
- Audit: `/api/v1/audit/logs`, `/api/v1/audit/export/csv`, `/api/v1/audit/filters`
- Quotas: `/api/v1/quotas/config`, `/api/v1/quotas/my-usage`, `/api/v1/quotas/users`

Full OpenAPI docs are available at:

- http://localhost:8000/docs
- http://localhost:8000/redoc

## Configuration

### Backend (.env)

Create `.env` in the repo root. Example:

```env
DATABASE_URL=sqlite:///./data/db/resource_reserver_dev.db
SECRET_KEY=your-secret-key-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
API_URL=http://localhost:8000
DEFAULT_CSV_PATH=data/csv/resources.csv
DEBUG=false
ENVIRONMENT=development

RATE_LIMIT_ENABLED=true
RATE_LIMIT_ANONYMOUS=20/minute
RATE_LIMIT_AUTHENTICATED=100/minute
RATE_LIMIT_ADMIN=500/minute
RATE_LIMIT_AUTH=5/minute
RATE_LIMIT_HEAVY=10/minute

REDIS_URL=redis://localhost:6379/0
CACHE_ENABLED=true
CACHE_TTL_RESOURCES=30
CACHE_TTL_STATS=60
CACHE_TTL_USER_SESSION=300

EMAIL_ENABLED=false
SMTP_HOST=localhost
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
SMTP_FROM=noreply@resource-reserver.local
SMTP_FROM_NAME=Resource Reserver
SMTP_TLS=true
SMTP_SSL=false
EMAIL_TEMPLATES_DIR=apps/backend/app/templates/email

SETUP_REOPEN_TOKEN=
```

Notes:

- `DATABASE_URL` defaults to SQLite if unset; set it explicitly for consistency.
- CORS origins are defined in `apps/backend/app/config.py` (defaults allow localhost ports 3000, 8080, 8000).
- `API_URL` is used for calendar subscription URLs.

### Frontend (.env.local)

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### CLI

Environment variables:

- `API_URL` sets the CLI base URL.
- `CLI_CONFIG_DIR` sets the token/config directory (default: `~/.reservation-cli`).

## Data Import and Export

- Upload resources from CSV in the Resources tab or via `POST /api/v1/resources/upload`.
- Sample CSV files are available in `data/csv/resources.csv` and `data/csv/demo-resources.csv`.
- Bulk reservation import/export:
  - `POST /api/v1/bulk/reservations/import`
  - `GET /api/v1/bulk/reservations/export`
- Analytics exports:
  - `GET /api/v1/analytics/export/utilization.csv`
  - `GET /api/v1/analytics/export/reservations.csv`
- Audit exports:
  - `GET /api/v1/audit/export/csv`
  - `GET /api/v1/audit/export/json`

## Operations and Monitoring

- Health endpoints: `/health`, `/ready`, `/live`.
- Metrics: `/metrics` (Prometheus format), `/api/v1/metrics/summary` (JSON).
- Background tasks:
  - Expired reservation cleanup runs continuously.
  - Email reminders are sent every 15 minutes for upcoming reservations.
- Cache behavior:
  - If Redis is unavailable, the app runs without cache and logs a warning.
- Rate limiting:
  - Per-endpoint limits are configured via `RATE_LIMIT_*` variables.
  - Tiered quotas are available in `/api/v1/quotas/config`.

## Testing

Backend:

```bash
cd apps/backend
pytest tests/ -v
```

Frontend:

```bash
cd apps/frontend
npm run lint
npm run test
npm run test:e2e
```

## Troubleshooting

- 401 Unauthorized: log in again or refresh the token.
- 403 Forbidden: you may not have the required role or permission.
- Setup already complete: `/setup` redirects. Use `SETUP_REOPEN_TOKEN` and `/setup/unlock` to reopen.
- CORS errors: make sure the frontend points to the correct API URL and CORS allows your origin.
- 429 Too Many Requests: wait for the rate limit window to reset.

## License

MIT License. See `LICENSE`.
