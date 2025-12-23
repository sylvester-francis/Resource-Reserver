# Resource Reserver

A comprehensive resource reservation system with intelligent scheduling, conflict prevention, and enterprise-grade security.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/) [![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/) [![Next.js](https://img.shields.io/badge/Next.js-000000?style=flat&logo=next.js&logoColor=white)](https://nextjs.org/) [![Docker](https://img.shields.io/badge/Docker-2496ED?style=flat&logo=docker&logoColor=white)](https://www.docker.com/) [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

______________________________________________________________________

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Quick Start](#quick-start)
- [Architecture](#architecture)
- [Configuration](#configuration)
- [API Reference](#api-reference)
- [CLI Reference](#cli-reference)
- [Security](#security)
- [Development](#development)
- [Testing](#testing)
- [Deployment](#deployment)
- [Contributing](#contributing)
- [Contributors](#contributors)
- [License](#license)

______________________________________________________________________

## Overview

Resource Reserver solves the common problem of resource scheduling conflicts in organizations. Whether managing meeting rooms, equipment, laboratory instruments, or shared workspaces, this system provides:

- **Conflict-free booking** with automatic overlap detection
- **Real-time availability** visibility across all resources
- **Complete audit trail** for compliance and accountability
- **Flexible access** via web interface, REST API, or command-line tool

### Use Cases

| Sector        | Resources                                      |
| ------------- | ---------------------------------------------- |
| Corporate     | Meeting rooms, parking spots, shared equipment |
| Education     | Classrooms, computer labs, research equipment  |
| Healthcare    | Medical equipment, procedure rooms             |
| Manufacturing | Production equipment, testing stations         |

______________________________________________________________________

## Features

### Core Functionality

- **Resource Management**: Create, update, and organize resources with tags and categories
- **Reservation System**: Book resources with automatic conflict detection
- **Availability Tracking**: Real-time status updates and availability calendar
- **Bulk Operations**: CSV import for adding multiple resources at once
- **Search and Filter**: Find resources by name, tags, or availability window

### Security and Access Control

- **Multi-Factor Authentication (MFA)**: TOTP-based 2FA with backup codes
- **Role-Based Access Control (RBAC)**: Configurable roles (Admin, User, Guest)
- **OAuth2 Authorization Server**: Built-in support for third-party integrations
- **JWT Authentication**: Secure token-based API access
- **Audit Logging**: Complete history of all actions

### Interfaces

- **Web Application**: Modern Next.js frontend with responsive design
- **REST API**: Full-featured API with OpenAPI documentation
- **Command-Line Interface**: Typer-based CLI for automation and administration

______________________________________________________________________

## Quick Start

### Prerequisites

- [Docker](https://www.docker.com/get-started) and Docker Compose
- [mise](https://mise.jdx.dev/) (optional, for development)

### One-Command Start

```bash
# Clone the repository
git clone https://github.com/sylvester-francis/Resource-Reserver.git
cd Resource-Reserver

# Start all services
mise run up

# Stop all services
mise run down
```

### Access Points

| Service           | URL                        |
| ----------------- | -------------------------- |
| Web Interface     | http://localhost:3000      |
| Backend API       | http://localhost:8000      |
| API Documentation | http://localhost:8000/docs |

### Alternative: Docker Compose Only

```bash
# Start services
docker compose up -d

# Stop services
docker compose down
```

### Default Credentials

Create a new account through the web interface at http://localhost:3000/register or use the CLI:

```bash
resource-reserver-cli auth register
```

______________________________________________________________________

## Architecture

### Technology Stack

| Component      | Technology                                    |
| -------------- | --------------------------------------------- |
| Frontend       | Next.js 14, React 18, Tailwind CSS, Radix UI  |
| Backend        | FastAPI, Python 3.11, SQLAlchemy              |
| Database       | SQLite (development), PostgreSQL (production) |
| CLI            | Typer, Rich                                   |
| Authentication | JWT, bcrypt, TOTP                             |
| Authorization  | Casbin RBAC                                   |
| Container      | Docker, Docker Compose                        |

### Project Structure

```
Resource-Reserver/
├── app/                    # FastAPI backend application
│   ├── main.py            # Application entry point
│   ├── models.py          # SQLAlchemy models
│   ├── schemas.py         # Pydantic schemas
│   ├── auth_routes.py     # Authentication endpoints
│   ├── oauth2.py          # OAuth2 server implementation
│   ├── rbac.py            # Role-based access control
│   └── mfa.py             # Multi-factor authentication
├── cli/                    # Command-line interface
│   ├── main.py            # CLI entry point
│   ├── client.py          # API client
│   └── auth_commands.py   # Authentication commands
├── frontend-next/          # Next.js frontend application
│   ├── src/
│   │   ├── app/           # Next.js app router pages
│   │   ├── components/    # React components
│   │   ├── hooks/         # Custom React hooks
│   │   └── lib/           # Utilities and API client
│   └── package.json
├── tests/                  # Test suite
├── docs/                   # Documentation
├── docker-compose.yml      # Docker Compose configuration
├── Dockerfile.backend      # Backend container
├── Dockerfile.frontend     # Frontend container
├── .mise.toml             # mise task runner configuration
└── pyproject.toml         # Python project configuration
```

______________________________________________________________________

## Configuration

### Environment Variables

| Variable       | Description                | Default                                 |
| -------------- | -------------------------- | --------------------------------------- |
| `DATABASE_URL` | Database connection string | `sqlite:///./data/resource_reserver.db` |
| `SECRET_KEY`   | JWT signing key            | Required in production                  |
| `ENVIRONMENT`  | Runtime environment        | `development`                           |
| `API_BASE_URL` | Backend API URL            | `http://localhost:8000`                 |

### Database Options

**SQLite (Development)**

```bash
DATABASE_URL=sqlite:///./data/resource_reserver.db
```

**PostgreSQL (Production)**

```bash
DATABASE_URL=postgresql://user:password@host:5432/resource_reserver
```

To enable PostgreSQL with Docker Compose:

```bash
docker compose --profile postgres up -d
```

______________________________________________________________________

## API Reference

The API documentation is available at http://localhost:8000/docs when the backend is running.

### Key Endpoints

| Method | Endpoint                       | Description                 |
| ------ | ------------------------------ | --------------------------- |
| POST   | `/auth/register`               | Create new user account     |
| POST   | `/auth/login`                  | Authenticate user           |
| GET    | `/resources`                   | List all resources          |
| POST   | `/resources`                   | Create new resource         |
| GET    | `/resources/{id}/availability` | Check resource availability |
| POST   | `/reservations`                | Create reservation          |
| GET    | `/reservations`                | List user reservations      |
| DELETE | `/reservations/{id}`           | Cancel reservation          |

### Authentication

All protected endpoints require a JWT token in the Authorization header:

```bash
curl -H "Authorization: Bearer <token>" http://localhost:8000/resources
```

For detailed API documentation, see [docs/api-reference.md](docs/api-reference.md).

______________________________________________________________________

## CLI Reference

Install the CLI tool:

```bash
pip install -e .
```

### Authentication Commands

```bash
resource-reserver-cli auth register     # Create new account
resource-reserver-cli auth login        # Login to account
resource-reserver-cli auth logout       # Logout
resource-reserver-cli auth status       # Check login status
```

### MFA Commands

```bash
resource-reserver-cli mfa setup         # Setup MFA with QR code
resource-reserver-cli mfa enable        # Enable MFA
resource-reserver-cli mfa disable       # Disable MFA
resource-reserver-cli mfa backup-codes  # Regenerate backup codes
```

### Resource Commands

```bash
resource-reserver-cli resources list              # List all resources
resource-reserver-cli resources search            # Search resources
resource-reserver-cli resources create <name>     # Create resource
resource-reserver-cli resources availability <id> # Check availability
```

### Reservation Commands

```bash
resource-reserver-cli reservations list           # List your reservations
resource-reserver-cli reservations create         # Create reservation
resource-reserver-cli reservations cancel <id>    # Cancel reservation
resource-reserver-cli reservations upcoming       # Show upcoming reservations
```

### Role Management (Admin)

```bash
resource-reserver-cli roles list                  # List all roles
resource-reserver-cli roles my-roles              # Show your roles
resource-reserver-cli roles assign <user> <role>  # Assign role
resource-reserver-cli roles remove <user> <role>  # Remove role
```

### OAuth2 Client Management

```bash
resource-reserver-cli oauth create <name> <uri>   # Create OAuth2 client
resource-reserver-cli oauth list                  # List your clients
resource-reserver-cli oauth delete <client_id>    # Delete client
```

______________________________________________________________________

## Security

### Authentication Methods

1. **Username/Password**: Standard credential-based authentication
1. **Multi-Factor Authentication**: TOTP-based 2FA compatible with authenticator apps
1. **OAuth2**: Authorization code and client credentials flows

### Role-Based Access Control

| Role  | Resources    | Reservations      | Users        | OAuth2             |
| ----- | ------------ | ----------------- | ------------ | ------------------ |
| Admin | Full control | Full control      | Full control | Full control       |
| User  | Read only    | Create/manage own | Read only    | Manage own clients |
| Guest | Read only    | None              | None         | None               |

### OAuth2 Scopes

- `read`: View resources and reservations
- `write`: Create and modify resources and reservations
- `delete`: Remove resources and reservations
- `admin`: Administrative access
- `user:profile`: Access user profile information

For complete security documentation, see [docs/auth-guide.md](docs/auth-guide.md).

______________________________________________________________________

## Development

### Setup Development Environment

```bash
# Install mise (if not already installed)
curl https://mise.run | sh

# Clone and setup
git clone https://github.com/sylvester-francis/Resource-Reserver.git
cd Resource-Reserver

# Install dependencies
mise install
mise run setup

# Start development environment with hot reload
mise run dev
```

### Available Commands

| Command           | Description                                |
| ----------------- | ------------------------------------------ |
| `mise run up`     | Start all services with Docker Compose     |
| `mise run down`   | Stop all services                          |
| `mise run dev`    | Start development environment with Tilt UI |
| `mise run test`   | Run all tests                              |
| `mise run lint`   | Run linters (ruff, eslint)                 |
| `mise run format` | Format code (ruff)                         |
| `mise run build`  | Build frontend for production              |
| `mise run logs`   | View service logs                          |
| `mise run clean`  | Clean caches and temporary files           |

### Code Quality

The project uses pre-commit hooks for code quality:

```bash
# Install hooks
mise run setup-hooks

# Run manually
pre-commit run --all-files
```

Linting and formatting tools:

- **Python**: ruff (linting and formatting)
- **TypeScript**: ESLint
- **Dockerfiles**: hadolint
- **Shell scripts**: shellcheck
- **YAML**: yamllint

______________________________________________________________________

## Testing

### Run All Tests

```bash
mise run test
```

### Run Specific Tests

```bash
# Backend tests only
pytest tests/ -v

# Frontend tests only
cd frontend-next && bun run test

# With coverage
pytest tests/ --cov=app --cov=cli --cov-report=html
```

### Test Structure

```
tests/
├── test_auth_endpoints.py    # Authentication API tests
├── test_auth_features.py     # MFA and RBAC tests
├── test_reservations.py      # Reservation logic tests
└── conftest.py               # Pytest fixtures
```

______________________________________________________________________

## Deployment

### Docker Compose (Recommended)

```bash
# Production deployment
docker compose up -d

# With PostgreSQL
docker compose --profile postgres up -d
```

### Pre-built Images

```bash
# Download compose file
curl -O https://raw.githubusercontent.com/sylvester-francis/Resource-Reserver/main/docker-compose.registry.yml

# Start with pre-built images
docker compose -f docker-compose.registry.yml up -d
```

### Environment Configuration

Create a `.env` file for production:

```bash
SECRET_KEY=your-secure-secret-key
DATABASE_URL=postgresql://user:password@postgres:5432/resource_reserver
ENVIRONMENT=production
```

For detailed deployment instructions, see [docs/deployment.md](docs/deployment.md).

______________________________________________________________________

## System Requirements

### Minimum

- CPU: 1 core
- RAM: 1 GB
- Disk: 5 GB
- Users: Up to 50 concurrent

### Recommended

- CPU: 4 cores
- RAM: 8 GB
- Disk: 50 GB
- Users: 500+ concurrent

### Supported Platforms

- Linux (Ubuntu, CentOS, RHEL)
- macOS (Intel and Apple Silicon)
- Windows (with Docker Desktop)

______________________________________________________________________

## Contributing

1. Fork the repository
1. Create a feature branch (`git checkout -b feature/new-feature`)
1. Make changes and add tests
1. Run linting and tests (`mise run lint && mise run test`)
1. Commit changes (`git commit -m "Add new feature"`)
1. Push to branch (`git push origin feature/new-feature`)
1. Open a Pull Request

### Development Guidelines

- Follow existing code style (enforced by pre-commit hooks)
- Add tests for new functionality
- Update documentation as needed
- Keep commits focused and atomic

______________________________________________________________________

## Contributors

- Sylvester Francis

______________________________________________________________________

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.

______________________________________________________________________

## Documentation

- [API Reference](docs/api-reference.md)
- [Authentication Guide](docs/auth-guide.md)
- [Deployment Guide](docs/deployment.md)
- [Development Guide](docs/development.md)
- [Troubleshooting](docs/troubleshooting.md)

______________________________________________________________________

## Support

- **Issues**: [GitHub Issues](https://github.com/sylvester-francis/Resource-Reserver/issues)
- **Discussions**: [GitHub Discussions](https://github.com/sylvester-francis/Resource-Reserver/discussions)
