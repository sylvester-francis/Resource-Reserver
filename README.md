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
- [Configuration](#configuration)
- [API Reference](#api-reference)
- [Development](#development)
- [Testing](#testing)
- [Deployment](#deployment)
- [Contributing](#contributing)
- [License](#license)

______________________________________________________________________

## Overview

Resource Reserver coordinates shared assets—rooms, equipment, labs, desks—without collisions. It offers a fast FastAPI backend, a Next.js frontend, and a newly polished Typer-based CLI with consistent, professional output (sections, tables, and clear errors).

### Use Cases

- Corporate: meeting rooms, parking, shared gear
- Education: classrooms, computer labs, instruments
- Healthcare: procedure rooms, medical devices
- Manufacturing: production/test stations

______________________________________________________________________

## Highlights

- **Conflict-aware reservations** with overlap prevention and recurring series.
- **Waitlist lifecycle**: join, list/status, accept offers, leave; flexible timing supported.
- **Resource controls**: enable/disable, maintenance with auto-reset, full status, availability windows, CSV upload with preview.
- **System health**: CLI commands for status, availability summary, and manual cleanup of expired reservations.
- **Security-first**: MFA (setup/enable/backup/regenerate), RBAC roles, OAuth2 client management, JWT auth.
- **Real-time**: WebSocket updates and notification feed.
- **Professional CLI UX**: structured sections, tables, and consistent messaging across auth, resources, reservations, waitlist, and system utilities.

______________________________________________________________________

## Quick Start

### Prerequisites

- Docker + Docker Compose
- [mise](https://mise.jdx.dev/) (optional, recommended for tasks)

### One Command

```bash
git clone https://github.com/sylvester-francis/Resource-Reserver.git
cd Resource-Reserver
mise run up          # start backend, frontend, database
# mise run down      # stop services
```

Alternative without mise:

```bash
docker compose up -d
# docker compose down
```

### Access

| Service            | URL                        |
| ------------------ | -------------------------- |
| Web UI             | http://localhost:3000      |
| Backend API        | http://localhost:8000      |
| API Docs (OpenAPI) | http://localhost:8000/docs |

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

Notes:

- CLI output now uses consistent sections, tables, and concise warnings/errors.
- Authentication automatically refreshes tokens when possible; failures are surfaced clearly.

______________________________________________________________________

## Architecture

| Component  | Tech                                         |
| ---------- | -------------------------------------------- |
| Frontend   | Next.js 14, React 18, Tailwind CSS, Radix UI |
| Backend    | FastAPI, Python 3.11, SQLAlchemy             |
| AuthN/Z    | JWT, bcrypt, TOTP MFA, OAuth2, Casbin RBAC   |
| CLI        | Typer + Rich                                 |
| Data       | SQLite (dev), PostgreSQL (prod)              |
| Containers | Docker, Docker Compose                       |

Structure (partial):

```
app/             # FastAPI backend
cli/             # Typer CLI (auth, resources, reservations, waitlist, system)
frontend-next/   # Next.js frontend
tests/           # Automated tests (API, CLI, services)
docs/            # Additional docs
```

______________________________________________________________________

## Configuration

Key environment variables:

| Variable       | Description                | Default                                 |
| -------------- | -------------------------- | --------------------------------------- |
| `DATABASE_URL` | Database connection string | `sqlite:///./data/resource_reserver.db` |
| `SECRET_KEY`   | JWT signing key            | _required in production_                |
| `ENVIRONMENT`  | Runtime environment        | `development`                           |
| `API_BASE_URL` | Backend API URL            | `http://localhost:8000`                 |

PostgreSQL via Compose:

```bash
docker compose --profile postgres up -d
```

______________________________________________________________________

## API Reference

Live docs: http://localhost:8000/docs

Key endpoints (prefix `/api/v1`):

- Auth: `POST /register`, `POST /token`, `POST /token/refresh`
- Resources: `GET /resources`, `POST /resources`, `GET /resources/search`, `GET /resources/{id}/status`
- Reservations: `POST /reservations`, `POST /reservations/recurring`, `GET /reservations/my`, `POST /reservations/{id}/cancel`
- Waitlist: `POST /waitlist`, `GET /waitlist`, `POST /waitlist/{id}/accept`, `DELETE /waitlist/{id}`
- Notifications: `GET /notifications`
- WebSocket: `/ws` for real-time updates

Auth header example:

```bash
curl -H "Authorization: Bearer <token>" http://localhost:8000/api/v1/resources
```

______________________________________________________________________

## Development

```bash
curl https://mise.run | sh    # install mise (optional)
git clone https://github.com/sylvester-francis/Resource-Reserver.git
cd Resource-Reserver
mise install
mise run setup                # install backend/frontend deps, pre-commit hooks
mise run dev                  # run dev stack with hot reload
```

Common tasks:

| Command           | Description                 |
| ----------------- | --------------------------- |
| `mise run up`     | Start all services (Docker) |
| `mise run down`   | Stop services               |
| `mise run dev`    | Dev stack with Tilt UI      |
| `mise run test`   | Run all tests               |
| `mise run lint`   | Lint (ruff, eslint)         |
| `mise run format` | Format (ruff)               |
| `mise run build`  | Build frontend              |
| `mise run clean`  | Clean caches/temp           |

Pre-commit:

```bash
mise run setup-hooks
pre-commit run --all-files
```

______________________________________________________________________

## Testing

```bash
mise run test                    # full suite
pytest tests/ -v                 # backend
cd frontend-next && bun run test # frontend
pytest tests/ --cov=app --cov=cli --cov-report=html
```

______________________________________________________________________

## Deployment

```bash
docker compose up -d                              # standard
docker compose --profile postgres up -d           # with Postgres
docker compose -f docker-compose.registry.yml up -d  # use pre-built images
```

Production `.env` example:

```bash
SECRET_KEY=your-secure-secret-key
DATABASE_URL=postgresql://user:password@postgres:5432/resource_reserver
ENVIRONMENT=production
```

See `docs/deployment.md` for Kubernetes/ECS/GCP examples.

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
