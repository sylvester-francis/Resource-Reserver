# Resource Reserver

Modern resource scheduling with conflict prevention, strong security, and a professional CLI for automation and operations.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/) [![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/) [![Next.js](https://img.shields.io/badge/Next.js-000000?style=flat&logo=next.js&logoColor=white)](https://nextjs.org/) [![Docker](https://img.shields.io/badge/Docker-2496ED?style=flat&logo=docker&logoColor=white)](https://www.docker.com/) [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

______________________________________________________________________

## Contents

- [Overview](#overview)
- [Highlights](#highlights)
- [Quick Start](#quick-start)
- [CLI Quick Tour](#cli-quick-tour)
- [Architecture](#architecture)
- [Features](#features)
- [Configuration](#configuration)
- [API Reference](#api-reference)
- [Development](#development)
- [Testing](#testing)
- [Deployment](#deployment)
- [Documentation](#documentation)
- [Contributing](#contributing)
- [License](#license)

______________________________________________________________________

## Overview

Resource Reserver coordinates shared assets—rooms, equipment, labs, desks—without collisions. It offers a fast FastAPI backend, a Next.js frontend, and a polished Typer-based CLI with consistent, professional output.

### Use Cases

- Corporate: meeting rooms, parking, shared gear
- Education: classrooms, computer labs, instruments
- Healthcare: procedure rooms, medical devices
- Manufacturing: production/test stations

______________________________________________________________________

## Highlights

### Core Features

- **Conflict-aware reservations** with overlap prevention and recurring series
- **Waitlist lifecycle**: join, list/status, accept offers, leave with flexible timing
- **Resource controls**: enable/disable, maintenance with auto-reset, CSV upload
- **Security-first**: MFA (TOTP), RBAC roles, OAuth2 client management, JWT auth
- **Real-time**: WebSocket updates and notification feed
- **Professional CLI**: structured sections, tables, and consistent messaging

### Phase 1: Foundation

- **Redis Caching** - Performance boost with Redis cache layer for resources and stats
- **Email Notifications** - Reservation confirmations, reminders, waitlist updates
- **Business Hours** - Define operating hours, time slots, and blackout dates
- **Calendar Integration** - iCal feeds, subscription URLs, .ics export

### Phase 2: Enhanced Features

- **Analytics Dashboard** - Resource utilization, peak times, CSV export
- **Health Checks** - Kubernetes probes (/ready, /live) and Prometheus metrics
- **Database Migrations** - Alembic for versioned schema management
- **Rate Limiting & Quotas** - Per-user/tier rate limits with tracking

### Phase 3: Polish & Scale

- **Resource Groups** - Hierarchical organization (building/floor/room)
- **Webhook Support** - External integrations with HMAC signing & retry
- **API Versioning** - URL path versioning with deprecation headers
- **Dark Mode** - Smooth theme transitions with Light/Dark/System selector
- **PWA Support** - Offline mode, install prompts, push notifications
- **Internationalization** - English, Spanish, French with language selector
- **E2E Testing** - Playwright tests for critical user flows
- **Documentation Site** - MkDocs with Material theme

______________________________________________________________________

## Quick Start

### Prerequisites

- Docker + Docker Compose
- [mise](https://mise.jdx.dev/) (optional, recommended for tasks)

### One Command

```bash
git clone https://github.com/sylvester-francis/Resource-Reserver.git
cd Resource-Reserver
mise run up          # start backend, frontend, database, redis
# mise run down      # stop services
```

Alternative without mise:

```bash
docker compose up -d
# docker compose down
```

### Access

| Service            | URL                           |
| ------------------ | ----------------------------- |
| Web UI             | http://localhost:3000         |
| Backend API        | http://localhost:8000         |
| API Docs (OpenAPI) | http://localhost:8000/docs    |
| Documentation Site | http://localhost:8001         |
| Prometheus Metrics | http://localhost:8000/metrics |

### Create an Account

- Web: http://localhost:3000/register
- CLI: `resource-reserver-cli auth register`

______________________________________________________________________

## CLI Quick Tour

Install (editable for development):

```bash
pip install -e .
```

Authentication & tokens:

```bash
resource-reserver-cli auth register
resource-reserver-cli auth login
resource-reserver-cli auth status
resource-reserver-cli auth refresh
resource-reserver-cli auth logout
```

MFA and roles:

```bash
resource-reserver-cli mfa setup | enable | disable | backup-codes
resource-reserver-cli roles list | my-roles | assign <user> <role> | remove <user> <role>
```

Resources:

```bash
resource-reserver-cli resources list [--details|--all|--cursor CUR]
resource-reserver-cli resources search [--query Q --from TS --until TS --available-only/--all]
resource-reserver-cli resources availability <id>
resource-reserver-cli resources status <id>
resource-reserver-cli resources enable|disable|maintenance|reset <id> [options]
resource-reserver-cli resources create <name> [--tags t1,t2]
resource-reserver-cli resources upload <file.csv> [--preview]
```

Reservations:

```bash
resource-reserver-cli reservations create <resource_id> <start> [<end_or_duration>] [--recurrence daily|weekly|monthly ...]
resource-reserver-cli reservations list [--upcoming --include-cancelled --all]
resource-reserver-cli reservations cancel <id> [--reason]
resource-reserver-cli reservations history <id>
resource-reserver-cli reserve <resource_id> <start> <duration>   # shortcut
resource-reserver-cli upcoming                                   # shortcut
```

Waitlist:

```bash
resource-reserver-cli waitlist join --resource <id> --start TS --end TS [--flexible]
resource-reserver-cli waitlist list [--include-completed]
resource-reserver-cli waitlist status <id>
resource-reserver-cli waitlist accept <id>
resource-reserver-cli waitlist leave <id>
```

System utilities:

```bash
resource-reserver-cli system status      # health + auth + config snapshot
resource-reserver-cli system summary     # availability summary table
resource-reserver-cli system cleanup     # purge expired reservations
resource-reserver-cli system config      # show local CLI/API configuration
```

______________________________________________________________________

## Architecture

| Component   | Tech                                         |
| ----------- | -------------------------------------------- |
| Frontend    | Next.js 14, React 18, Tailwind CSS, Radix UI |
| Backend     | FastAPI, Python 3.11, SQLAlchemy             |
| AuthN/Z     | JWT, bcrypt, TOTP MFA, OAuth2, Casbin RBAC   |
| CLI         | Typer + Rich                                 |
| Cache       | Redis 7                                      |
| Data        | SQLite (dev), PostgreSQL (prod)              |
| Migrations  | Alembic                                      |
| Containers  | Docker, Docker Compose                       |
| Docs        | MkDocs with Material theme                   |
| E2E Testing | Playwright                                   |

Structure:

```
app/                    # FastAPI backend
├── core/               # Cache, metrics, i18n, rate limiting
├── routers/            # API endpoints (v1, v2)
├── services/           # Business logic
├── templates/email/    # Email templates
cli/                    # Typer CLI
frontend-next/          # Next.js frontend
├── e2e/                # Playwright E2E tests
├── messages/           # i18n translations
docs/                   # MkDocs documentation
migrations/             # Alembic migrations
tests/                  # Automated tests
```

______________________________________________________________________

## Features

### Email Notifications

Automated emails for reservation events:

- Confirmation on reservation creation
- Reminders before reservation (configurable: 1hr, 24hr)
- Waitlist position updates
- Resource availability alerts

Configure via environment variables:

```bash
EMAIL_ENABLED=true
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
```

### Business Hours & Time Slots

Define when resources are available:

- Per-resource or global business hours
- Configurable time slot durations (30min, 1hr)
- Blackout dates for holidays/maintenance
- Available slots API for UI integration

```bash
# Get available slots for a date
GET /api/v1/resources/{id}/available-slots?date=2025-01-15

# Set business hours
PUT /api/v1/resources/{id}/business-hours
```

### Calendar Integration

Subscribe to reservations from any calendar app:

- iCal feed subscription URL per user
- Single event .ics download
- Compatible with Google Calendar, Outlook, Apple Calendar
- Secure token-based feed URLs

```bash
# Get subscription URL
GET /api/v1/calendar/subscription-url

# Export single reservation
GET /api/v1/calendar/export/{reservation_id}.ics
```

### Analytics Dashboard

Insights into resource utilization:

- Resource utilization metrics (% time booked)
- Popular resources ranking
- Peak usage times (hourly/daily analysis)
- User booking patterns
- CSV export for reports

```bash
GET /api/v1/analytics/dashboard
GET /api/v1/analytics/export/utilization.csv
```

### Webhook Integrations

Notify external systems of events:

- 13 event types (reservation, resource, user events)
- HMAC-SHA256 payload signing
- Automatic retry with exponential backoff
- Delivery history and manual retry

```bash
# Register webhook
POST /api/v1/webhooks/
{
  "url": "https://your-app.com/webhook",
  "events": ["reservation.created", "reservation.cancelled"]
}
```

### Resource Groups

Organize resources hierarchically:

- Groups with parent-child nesting
- Location-based organization (building/floor/room)
- Resource parent-child relationships
- Tree view API

```bash
GET /api/v1/resource-groups/tree
POST /api/v1/resource-groups/{id}/resources
```

### Internationalization (i18n)

Multi-language support:

- Frontend: English, Spanish, French
- Backend: Localized API messages
- Accept-Language header parsing
- Language selector in UI

### Progressive Web App (PWA)

Mobile-first experience:

- Install to home screen
- Offline support with service worker
- Push notifications
- App shortcuts for quick actions

______________________________________________________________________

## Configuration

Key environment variables:

| Variable             | Description                | Default                            |
| -------------------- | -------------------------- | ---------------------------------- |
| `DATABASE_URL`       | Database connection string | `sqlite:///./resource_reserver.db` |
| `SECRET_KEY`         | JWT signing key            | _required in production_           |
| `REDIS_URL`          | Redis connection string    | `redis://localhost:6379/0`         |
| `CACHE_ENABLED`      | Enable Redis caching       | `true`                             |
| `EMAIL_ENABLED`      | Enable email notifications | `false`                            |
| `SMTP_HOST`          | SMTP server hostname       | `localhost`                        |
| `RATE_LIMIT_ENABLED` | Enable rate limiting       | `true`                             |
| `API_BASE_URL`       | Backend API URL            | `http://localhost:8000`            |

PostgreSQL via Compose:

```bash
docker compose --profile postgres up -d
```

______________________________________________________________________

## API Reference

Live docs: http://localhost:8000/docs

### Versioning

The API supports versioning:

```bash
# URL path (recommended)
GET /api/v1/resources
GET /api/v2/resources

# Header
curl -H "X-API-Version: 1" /api/resources
```

### Rate Limits

| Tier          | Requests/Minute |
| ------------- | --------------- |
| Anonymous     | 20              |
| Authenticated | 100             |
| Premium       | 500             |
| Admin         | 1000            |

Headers: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`

### Key Endpoints

| Endpoint                              | Description              |
| ------------------------------------- | ------------------------ |
| `POST /token`                         | Obtain access token      |
| `GET /resources`                      | List resources           |
| `GET /resources/{id}/available-slots` | Get available time slots |
| `GET /reservations`                   | List reservations        |
| `GET /analytics/dashboard`            | Analytics summary        |
| `GET /calendar/feed/{token}.ics`      | iCal subscription feed   |
| `GET /health`                         | Health check             |
| `GET /ready`                          | Kubernetes readiness     |
| `GET /live`                           | Kubernetes liveness      |
| `GET /metrics`                        | Prometheus metrics       |

______________________________________________________________________

## Development

```bash
curl https://mise.run | sh    # install mise (optional)
git clone https://github.com/sylvester-francis/Resource-Reserver.git
cd Resource-Reserver
mise run setup                # install deps, pre-commit hooks (auto-heals)
mise run dev                  # run dev stack with hot reload
```

### Mise Commands

All mise tasks are self-healing and auto-install missing dependencies:

| Command               | Description                 |
| --------------------- | --------------------------- |
| `mise run up`         | Start all services (Docker) |
| `mise run down`       | Stop services               |
| `mise run dev`        | Dev stack with hot reload   |
| `mise run test`       | Run all tests               |
| `mise run test-cov`   | Run tests with coverage     |
| `mise run lint`       | Lint (ruff, eslint)         |
| `mise run format`     | Format (ruff, prettier)     |
| `mise run build`      | Build frontend              |
| `mise run docs`       | Serve documentation site    |
| `mise run db-migrate` | Run database migrations     |
| `mise run status`     | Environment health check    |
| `mise run help`       | List all available commands |
| `mise run clean`      | Clean caches/temp           |

Pre-commit:

```bash
mise run setup-hooks
pre-commit run --all-files
```

______________________________________________________________________

## Testing

### Unit & Integration Tests

```bash
mise run test                    # full suite (~500 tests)
pytest tests/ -v                 # backend only
cd frontend-next && bun run test # frontend only
pytest tests/ --cov=app --cov=cli --cov-report=html
```

### E2E Tests (Playwright)

```bash
cd frontend-next
npm run test:e2e              # run all E2E tests
npm run test:e2e:ui           # with Playwright UI
npm run test:e2e:headed       # in headed browser mode
npm run test:e2e:report       # view test report
```

E2E test suites:

- `auth.spec.ts` - Login, logout, session persistence
- `resources.spec.ts` - Resource browsing and filtering
- `reservations.spec.ts` - Making and cancelling reservations
- `waitlist.spec.ts` - Waitlist workflow

______________________________________________________________________

## Deployment

```bash
docker compose up -d                              # standard
docker compose --profile postgres up -d           # with Postgres
docker compose -f docker-compose.registry.yml up -d  # pre-built images
```

Production `.env` example:

```bash
SECRET_KEY=your-secure-secret-key
DATABASE_URL=postgresql://user:password@postgres:5432/resource_reserver
REDIS_URL=redis://redis:6379/0
ENVIRONMENT=production
EMAIL_ENABLED=true
SMTP_HOST=smtp.yourprovider.com
```

### Database Migrations

```bash
# Apply all migrations
alembic upgrade head

# Generate new migration
alembic revision --autogenerate -m "description"

# Mark existing database as current
alembic stamp head
```

See `docs/development/deployment.md` for Kubernetes/ECS/GCP examples.

______________________________________________________________________

## Documentation

The project includes a comprehensive documentation site built with MkDocs:

```bash
mise run docs    # Serve docs at http://localhost:8001
mkdocs build     # Build static site
```

Documentation sections:

- **Getting Started** - Installation, quickstart, configuration
- **User Guide** - Dashboard, resources, reservations, waitlist, calendar
- **API Reference** - Authentication, endpoints, webhooks
- **Admin Guide** - User management, roles, business hours, analytics
- **Development** - Contributing, architecture, testing, deployment

______________________________________________________________________

## Contributing

1. Fork and branch (`git checkout -b feature/xyz`)
1. Add tests and docs for changes
1. Run `mise run lint && mise run test`
1. Open a PR with a clear summary

______________________________________________________________________

## Contributors

- Sylvester Francis (`sylvester-francis`)
- Dan Caugherty (`@dcaugher`, `dcaugher`)

______________________________________________________________________

## License

MIT License. See [LICENSE](LICENSE).
