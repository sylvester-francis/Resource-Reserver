# Resource Reserver

**Enterprise Resource Management and Booking System**

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/) [![Typer](https://img.shields.io/badge/CLI-Typer-0277bd?style=flat&logo=python&logoColor=white)](https://typer.tiangolo.com/) [![JavaScript](https://img.shields.io/badge/JavaScript-F7DF1E?style=flat&logo=javascript&logoColor=black)](https://developer.mozilla.org/en-US/docs/Web/JavaScript) [![GitHub Actions](https://img.shields.io/badge/CI%2FCD-GitHub%20Actions-2088FF?style=flat&logo=github-actions&logoColor=white)](https://github.com/features/actions) [![Ruff](https://img.shields.io/badge/Linter-Ruff-D7FF64?style=flat&logo=ruff&logoColor=black)](https://docs.astral.sh/ruff/) [![Mermaid](https://img.shields.io/badge/Diagrams-Mermaid-FF3670?style=flat&logo=mermaid&logoColor=white)](https://mermaid.js.org/) [![Swagger](https://img.shields.io/badge/API%20Docs-Swagger-85EA2D?style=flat&logo=swagger&logoColor=black)](http://localhost:8000/docs) [![Docker](https://img.shields.io/badge/Container-Docker-2496ED?style=flat&logo=docker&logoColor=white)](https://www.docker.com/)

## Overview

Resource Reserver is a comprehensive resource management platform designed for organizations that need to efficiently schedule and manage shared assets. The system provides conflict-free booking, real-time availability tracking, and comprehensive audit trails through multiple user interfaces including web application, command-line tools, and REST API.

### Business Value

**Cost Reduction**: Eliminates scheduling conflicts and reduces administrative overhead through automated resource management.

**Operational Efficiency**: Provides real-time visibility into resource utilization with comprehensive reporting and analytics capabilities.

**Compliance**: Maintains complete audit trails for governance requirements and operational accountability.

**Scalability**: Supports enterprise-level deployments with horizontal scaling and high-availability configurations.

---

## Table of Contents

- [Architecture](#architecture)
- [Features](#features)
- [Use Cases](#use-cases)
- [System Requirements](#system-requirements)
- [Installation](#installation)
- [Docker Deployment](#docker-deployment)
- [Configuration](#configuration)
- [API Documentation](#api-documentation)
- [User Interfaces](#user-interfaces)
- [Development](#development)
- [Testing](#testing)
- [CI/CD Pipeline](#cicd-pipeline)
- [Contributing](#contributing)
- [Support](#support)

---

## Architecture

Resource Reserver follows a modern, scalable microservices architecture designed for enterprise deployment.

### System Overview

```mermaid
graph TB
    subgraph "User Layer"
        U1[Business Users]
        U2[System Administrators]
        U3[External Systems]
    end
    
    subgraph "Client Layer"
        WEB[Web Browser]
        CLI[Command Line Interface]
        API[External API Clients]
    end
    
    
    subgraph "Application Layer"
        APP1[FastAPI Application<br/>Container 1]
        APP2[FastAPI Application<br/>Container 2]
        APP3[FastAPI Application<br/>Container N]
    end
    
    subgraph "Business Logic"
        RS[Resource Service]
        ReS[Reservation Service]
        US[User Service]
        AS[Auth Service]
    end
    
    subgraph "Data Layer"
        DB[(Database<br/>PostgreSQL/MySQL)]
        FS[File Storage<br/>CSV/Logs]
        CACHE[Cache<br/>Redis]
    end
    
    subgraph "Background Services"
        CLEANUP[Cleanup Service]
        MONITOR[Health Monitor]
        AUDIT[Audit Logger]
    end
    
    %% User connections
    U1 --> WEB
    U2 --> CLI
    U3 --> API
    
    %% Client to applications
    WEB --> APP1
    CLI --> APP1
    API --> APP1
    
    %% Applications to services
    APP1 --> RS
    APP1 --> ReS
    APP1 --> US
    APP1 --> AS
    
    %% Services to data
    RS --> DB
    ReS --> DB
    US --> DB
    AS --> DB
    
    RS --> FS
    ReS --> FS
    
    %% Background services
    CLEANUP --> DB
    MONITOR --> DB
    AUDIT --> FS
    
    %% Styling
    classDef userClass fill:#2E86AB,stroke:#fff,stroke-width:2px,color:#fff
    classDef clientClass fill:#A23B72,stroke:#fff,stroke-width:2px,color:#fff
    classDef appClass fill:#F18F01,stroke:#fff,stroke-width:2px,color:#fff
    classDef serviceClass fill:#4CAF50,stroke:#fff,stroke-width:2px,color:#fff
    classDef dataClass fill:#C73E1D,stroke:#fff,stroke-width:2px,color:#fff
    classDef bgClass fill:#FFE082,stroke:#333,stroke-width:2px
    
    class U1,U2,U3 userClass
    class WEB,CLI,API clientClass
    class APP1,APP2,APP3 appClass
    class RS,ReS,US,AS serviceClass
    class DB,FS,CACHE dataClass
    class CLEANUP,MONITOR,AUDIT bgClass
```

### Architecture Principles

**Scalability**: Horizontal scaling through containerized application instances.

**Reliability**: Multi-tier architecture with redundancy and health monitoring.

**Security**: Defense in depth with authentication, authorization, and input validation at multiple layers.

**Maintainability**: Clean separation of concerns with distinct service layers and standardized interfaces.

**Performance**: Caching strategies and optimized database queries for sub-200ms response times.

### Component Responsibilities

| Layer | Components | Responsibility |
|-------|------------|----------------|
| **Client** | Web, CLI, API | User interface and external integrations |
| **Application** | FastAPI instances | Request handling, routing, and API endpoints |
| **Business Logic** | Service classes | Domain logic, validation, and business rules |
| **Data** | Database, Cache, Storage | Data persistence, caching, and file management |
| **Background** | Cleanup, Monitor, Audit | Automated tasks and system maintenance |

For detailed architecture documentation, see [architecture.md](architecture.md).

---

## Features

### Core Functionality

- **Resource Management**: Create, categorize, and manage organizational resources with flexible attribute systems
- **Reservation System**: Time-based booking with automatic conflict detection and prevention
- **User Authentication**: Secure JWT-based authentication with password encryption
- **Availability Engine**: Real-time availability checking across configurable time periods
- **Audit System**: Complete activity logging for compliance and operational transparency
- **Bulk Operations**: CSV import/export capabilities for large-scale resource management

### Technical Features

- **Multi-Interface Access**: Web application, command-line interface, and REST API
- **Database Abstraction**: Support for SQLite (development) and PostgreSQL/MySQL (production)
- **Background Processing**: Automated cleanup and maintenance tasks
- **Health Monitoring**: System status endpoints and performance metrics
- **Security**: Input validation, SQL injection prevention, and secure session management
- **Containerization**: Docker-ready deployment with orchestration support

---

## Use Cases

### Target Organizations

- **Corporate Environments**: Meeting rooms, equipment checkout, shared facilities
- **Educational Institutions**: Classrooms, laboratories, research equipment
- **Healthcare Facilities**: Medical equipment, procedure rooms, specialized tools
- **Manufacturing**: Production equipment, quality assurance tools, maintenance scheduling
- **Co-working Spaces**: Desk reservations, conference rooms, amenities

### Implementation Scenarios

- **Facility Management**: Centralized booking for conference rooms and meeting spaces
- **Equipment Tracking**: IT asset checkout and return management
- **Laboratory Scheduling**: Research equipment and facility time allocation
- **Maintenance Coordination**: Service window scheduling and resource allocation
- **Event Management**: Multi-resource coordination for complex events

---

## System Requirements

### Functional Requirements

#### Core System Capabilities

- Resource registration and categorization with custom attributes
- Real-time availability verification and conflict prevention
- User authentication and session management
- Advanced search and filtering capabilities
- Comprehensive audit trail and activity logging
- Bulk data operations with validation and error handling

#### User Interface Requirements

- Responsive web interface supporting modern browsers
- Command-line interface for automation and power users
- REST API for system integrations
- Mobile-responsive design for tablet and smartphone access

#### Data Management Requirements

- Reliable data persistence with backup capabilities
- Time zone handling for global deployments
- CSV import/export for legacy system integration
- Data validation and integrity enforcement

### Non-Functional Requirements

#### Performance Standards

- API response times under 200ms for 95th percentile
- Support for 1,000+ concurrent users
- Database query optimization with proper indexing
- Horizontal scaling capabilities

#### Security Requirements

- JWT-based authentication with secure token management
- bcrypt password hashing with configurable salt rounds
- SQL injection prevention through parameterized queries
- Input validation and sanitization
- Secure session management

#### Reliability Standards

- 99.9% uptime capability with proper configuration
- ACID-compliant database transactions
- Graceful error handling and recovery
- Automated backup and restore procedures

#### Compliance and Audit

- Complete activity logging for all user actions
- Configurable data retention policies
- Export capabilities for compliance reporting
- User access tracking and session monitoring

---

## Installation

### Prerequisites

- Python 3.11 or higher
- pip package manager
- Git version control system

### Local Development Setup

```bash
# Clone repository
git clone https://github.com/sylvester-francis/Resource-Reserver.git
cd resource-reserver

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Initialize database
mkdir -p data

# Start development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Production Installation

For production deployments, use the Docker containerization method described in the next section.

---

## Docker Deployment

### Quick Start

```bash
# Clone and start services
git clone https://github.com/sylvester-francis/Resource-Reserver.git
cd resource-reserver
docker compose up -d

# Verify deployment
curl http://localhost:8000/health
```

### Service Architecture

| Component | Port | Purpose |
|-----------|------|---------|
| API Server | 8000 | FastAPI backend with database and web interface |

### Development Environment

```bash
# Start development services with hot reload
docker compose --profile dev up -d

# Access development server
curl http://localhost:8001/health
```

### Production Configuration

#### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `sqlite:///./data/resource_reserver.db` | Database connection string |
| `ENVIRONMENT` | `development` | Application environment mode |
| `CLI_CONFIG_DIR` | `~/.reservation-cli` | CLI configuration directory |
| `PORT` | `8000` | Application server port |

#### Database Setup

For production deployments, configure an external database:

```yaml
# docker-compose.override.yml
services:
  api:
    environment:
      - DATABASE_URL=postgresql://username:password@db:5432/resource_reserver
      - ENVIRONMENT=production
  
  db:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: resource_reserver
      POSTGRES_USER: username
      POSTGRES_PASSWORD: password
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

#### SSL/TLS Configuration

Configure SSL termination through your reverse proxy or load balancer. The application supports standard HTTP headers for SSL offloading.

---

## Configuration

### Application Settings

The application uses environment-based configuration. Create a `.env` file for local development:

```bash
DATABASE_URL=sqlite:///./data/resource_reserver.db
ENVIRONMENT=development
SECRET_KEY=your-secret-key-here
CORS_ORIGINS=http://localhost:3000,http://localhost:8080
```

### Database Configuration

#### SQLite (Development)

```bash
DATABASE_URL=sqlite:///./data/resource_reserver.db
```

#### PostgreSQL (Production)

```bash
DATABASE_URL=postgresql://user:password@host:5432/database
```

#### MySQL (Production)

```bash
DATABASE_URL=mysql+pymysql://user:password@host:3306/database
```

---

## API Documentation

### Interactive Documentation

Access the auto-generated API documentation:

- **OpenAPI/Swagger**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`
- **OpenAPI Schema**: `http://localhost:8000/openapi.json`

### Authentication

The API uses JWT bearer token authentication:

```bash
# Register new user
curl -X POST "http://localhost:8000/register" \
  -H "Content-Type: application/json" \
  -d '{"username": "user", "password": "password"}'

# Authenticate and receive token
curl -X POST "http://localhost:8000/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=user&password=password"

# Use token for authenticated requests
curl -X GET "http://localhost:8000/resources/" \
  -H "Authorization: Bearer {jwt_token}"
```

### Core Endpoints

| Method | Endpoint | Description | Authentication |
|--------|----------|-------------|----------------|
| `POST` | `/register` | User registration | No |
| `POST` | `/token` | User authentication | No |
| `GET` | `/resources/` | List resources | No |
| `POST` | `/resources/` | Create resource | Yes |
| `GET` | `/resources/search` | Search resources | No |
| `POST` | `/reservations/` | Create reservation | Yes |
| `GET` | `/reservations/my` | User reservations | Yes |
| `DELETE` | `/reservations/{id}/cancel` | Cancel reservation | Yes |
| `GET` | `/health` | System health check | No |

---

## User Interfaces

### Web Application

The web interface provides a complete user experience for resource management:

1. **User Registration and Authentication**: Secure account creation and login
2. **Resource Discovery**: Browse and search available resources
3. **Reservation Management**: Create, view, and cancel bookings
4. **Dashboard**: Personal reservation overview and system status

Access the web application at `http://localhost:8000` when using Docker deployment.

#### Web Interface Screenshots

**Authentication**

- **Login**: Secure user authentication with modern interface
  
  ![Login Interface](screenshots/Web%20Interface/login-web.png)

- **Registration**: New user account creation
  
  ![Registration Interface](screenshots/Web%20Interface/register-web.png)

**Resource Management**

- **Resource List**: Browse and filter available resources with real-time availability
  
  ![Resource List](screenshots/Web%20Interface/resourcelist-web.png)

- **Create Resource**: Add new resources with tags and availability settings
  
  ![Create Resource](screenshots/Web%20Interface/createresource-web.png)

- **Upload Resources**: Bulk import via CSV with format validation
  
  ![Upload Resources](screenshots/Web%20Interface/uploadresource-web.png)

**Reservation Management**

- **Create Reservation**: Schedule resource bookings with conflict detection
  
  ![Create Reservation](screenshots/Web%20Interface/createreservation-web.png)

- **My Reservations**: View and manage personal bookings
  
  ![My Reservations](screenshots/Web%20Interface/myreservations-web.png)

- **Reservation History**: Complete audit trail for reservations
  
  ![Reservation History](screenshots/Web%20Interface/resourcehistory-web.png)

**System Management**

- **System Status**: Real-time system health and resource summary
  
  ![System Status](screenshots/Web%20Interface/systemstatus-web.png)

### Command Line Interface

The CLI provides comprehensive functionality for automation and power users:

```bash
# Authentication
python -m cli.main auth register
python -m cli.main auth login

# Resource management
python -m cli.main resources list
python -m cli.main resources create "Conference Room A" --tags "meeting,projector"
python -m cli.main resources search --query "laptop"

# Reservation operations
python -m cli.main reservations create 1 "2024-12-10 14:00" "2h"
python -m cli.main reservations list --upcoming
python -m cli.main reservations cancel 1

# Administrative functions
python -m cli.main system status
python -m cli.main system cleanup
python -m cli.main resources upload resources.csv
```

#### CLI Interface Screenshots

**Main Commands**

- **CLI Help**: Overview of all available commands and options
  
  ![CLI Main Help](screenshots/CLI%20Interface/cli-main.png)

**Authentication Commands**

- **Auth Commands**: User registration, login, logout, and status checking
  
  ![CLI Authentication](screenshots/CLI%20Interface/cli-auth.png)

**Resource Management**

- **Resource Commands**: List, create, search, and manage resources
  
  ![CLI Resources](screenshots/CLI%20Interface/cli-resources.png)

**Reservation Management**

- **Reservation Commands**: Create, list, cancel, and view reservation history
  
  ![CLI Reservations](screenshots/CLI%20Interface/cli-reservation.png)

**System Administration**

- **System Commands**: Status monitoring, cleanup, and configuration
  
  ![CLI System](screenshots/CLI%20Interface/cli-system.png)

### CSV Import Format

For bulk operations, use the following CSV structure:

```csv
name,tags,available
"Conference Room A","meeting,projector,whiteboard",true
"Laptop Dell XPS","portable,development,laptop",true
"Parking Space 101","parking,covered,accessible",true
```

---

## Development

### Development Environment Setup

```bash
# Install development dependencies
pip install ruff black isort mypy flake8 bandit safety pytest-cov

# Run development server with auto-reload
uvicorn app.main:app --reload
```

### Code Quality Standards

The project maintains high code quality through automated tooling:

```bash
# Code formatting and linting
ruff format .                    # Format code
ruff check .                     # Lint code
pytest                           # Run tests
bandit -r app/ cli/              # Security checks
```

### Project Architecture

```
resource-reserver/
├── app/                    # FastAPI backend
│   ├── main.py            # Application entry point
│   ├── auth.py            # Authentication logic
│   ├── database.py        # Database configuration
│   ├── models.py          # Data models
│   ├── schemas.py         # API schemas
│   └── services.py        # Business logic
├── cli/                   # Command-line interface
│   ├── main.py           # CLI entry point
│   ├── client.py         # API client
│   ├── config.py         # Configuration management
│   └── utils.py          # Utility functions
├── web/                  # Web interface
│   ├── index.html        # Application shell
│   ├── css/styles.css    # Styling
│   └── js/script.js      # Client-side logic
├── tests/                # Test suite
│   ├── test_api/         # API tests
│   ├── test_cli/         # CLI tests
│   └── test_services/    # Business logic tests
└── .github/workflows/    # CI/CD pipeline
```

### Development Workflow

1. Create feature branch from `main`
2. Implement changes with corresponding tests
3. Run quality checks: `ruff check . && pytest`
4. Submit pull request with descriptive commit messages
5. Address review feedback and ensure CI passes

---

## Testing

### Test Execution

```bash
# Run complete test suite
pytest

# Run with coverage reporting
pytest --cov=app --cov=cli --cov-report=html

# Run specific test categories
pytest tests/test_api/      # API tests
pytest tests/test_cli/      # CLI tests
pytest tests/test_services/ # Business logic tests
```

### Test Coverage Metrics

- **Overall Coverage**: 95%+
- **API Endpoints**: 100%
- **Business Logic**: 98%+
- **CLI Interface**: 95%+

### Test Categories

- **Unit Tests**: Individual component functionality
- **Integration Tests**: Component interaction testing
- **API Tests**: HTTP endpoint validation
- **CLI Tests**: Command-line interface verification
- **Security Tests**: Authentication and authorization

---

## CI/CD Pipeline

The project includes a comprehensive GitHub Actions CI/CD pipeline that ensures code quality and deployment readiness.

### Pipeline Overview

The CI/CD pipeline consists of three main stages:

1. **Code Quality & Linting**: Code formatting, linting, and style checks
2. **Testing**: Comprehensive test suite with coverage reporting
3. **Docker Build & Integration**: Container build, testing, and integration validation

### Pipeline Stages

#### 1. Code Quality & Linting

- **Ruff**: Fast Python linter with comprehensive rule set
- **Ruff Format**: Code formatting validation
- **Flake8**: Additional linting for specific error patterns

#### 2. Testing

- **Pytest**: Complete test suite execution
- **Coverage**: Code coverage reporting with XML and terminal output
- **Codecov**: Coverage upload for tracking and badges
- **Multiple test categories**: API, CLI, and service layer tests

#### 3. Docker Build & Integration

- **Multi-stage builds**: Optimized container images
- **Integration testing**: End-to-end API and CLI testing
- **Health checks**: Container health validation
- **Build caching**: GitHub Actions cache optimization

### Running the Pipeline Locally

```bash
# Install development dependencies
pip install -r requirements.txt
pip install ruff flake8 black isort mypy pytest-cov

# Run linting and formatting
ruff check .
ruff format --check .
flake8 .

# Run tests with coverage
pytest --cov=app --cov=cli --cov-report=xml --cov-report=term-missing

# Build and test Docker image
docker build -t resource-reserver:test .
docker run -d --name test-container -p 8000:8000 resource-reserver:test
curl -f http://localhost:8000/health
docker stop test-container && docker rm test-container
```

### Pipeline Configuration

The pipeline is configured in `.github/workflows/ci.yml` and includes:

- **Parallel execution**: Multiple jobs run concurrently for faster feedback
- **Dependency caching**: pip and Docker layer caching for performance
- **Build-only strategy**: Docker images are built and tested but not pushed to registries
- **Comprehensive error handling**: Detailed error reporting and debugging
- **Integration with external services**: Codecov for coverage tracking

### Quality Gates

All pull requests must pass:

- ✅ All linting and formatting checks
- ✅ Test suite with >95% coverage
- ✅ Docker build and integration tests
- ✅ No breaking changes to API contracts

### Branch Protection

- **Main branch**: Protected with required status checks
- **Pull requests**: Required for all changes to main
- **Review requirements**: Code review by maintainers
- **Automatic merging**: Available after all checks pass

### CI/CD Workflow

The pipeline follows this workflow:

1. **Trigger**: On push to `main`/`develop` branches or pull requests to `main`
2. **Linting**: Code quality checks run first for fast feedback
3. **Testing**: Comprehensive test suite with coverage reporting
4. **Docker Build**: Container build and integration testing
5. **Reporting**: Results aggregated and reported to pull requests

---

## Contributing

### Getting Started

1. Fork the repository on GitHub
2. Clone your fork locally
3. Create a feature branch
4. Make changes with appropriate tests
5. Submit a pull request

### Code Standards

- Follow PEP 8 Python style guidelines
- Maintain test coverage above 95%
- Include documentation for new features
- Use conventional commit message format

### Review Process

All contributions require:

- Code review by project maintainers
- Passing CI/CD pipeline checks
- Maintained test coverage
- Updated documentation where applicable

### Development Setup

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/Resource-Reserver.git
cd resource-reserver

# Set up development environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Install pre-commit hooks (optional but recommended)
pip install pre-commit
pre-commit install

# Create feature branch
git checkout -b feature/your-feature-name

# Make changes and commit
git add .
git commit -m "feat: your feature description"

# Push and create pull request
git push origin feature/your-feature-name
```

---

## Support

### Documentation

- **API Documentation**: Available at `/docs` endpoint
- **User Guide**: See Usage section above
- **Developer Guide**: See Development section above
- **Architecture**: See [architecture.md](architecture.md)

### Getting Help

- **Issues**: Report bugs and request features on GitHub Issues
- **Discussions**: Community support and questions on GitHub Discussions
- **Documentation**: Comprehensive documentation in the repository

### Reporting Issues

When reporting issues, please include:

- **Environment details**: OS, Python version, Docker version
- **Steps to reproduce**: Detailed reproduction steps
- **Expected behavior**: What you expected to happen
- **Actual behavior**: What actually happened
- **Logs**: Relevant error messages and logs

---

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

---

## Acknowledgments

Built with:

- [FastAPI](https://fastapi.tiangolo.com/) - Modern Python web framework
- [SQLAlchemy](https://www.sqlalchemy.org/) - Database toolkit
- [Typer](https://typer.tiangolo.com/) - CLI framework
- [pytest](https://pytest.org/) - Testing framework
- [Ruff](https://docs.astral.sh/ruff/) - Fast Python linter
- [Docker](https://www.docker.com/) - Containerization platform
- [GitHub Actions](https://github.com/features/actions) - CI/CD automation

---

## Changelog

### Recent Updates

- **CI/CD Pipeline**: Comprehensive GitHub Actions workflow with quality gates
- **Docker Improvements**: Enhanced containerization with multi-environment support
- **Security Enhancements**: Proper exception chaining and security scanning
- **Code Quality**: Automated formatting and linting with Ruff
- **Configuration Management**: Environment-based configuration with Docker Compose
- **Testing**: Expanded test coverage across API, CLI, and service layers

### Version 1.0.0

- Initial release with core reservation functionality
- Web interface and CLI tools
- Comprehensive API with OpenAPI documentation
- Docker deployment support
- Complete test suite with high coverage
