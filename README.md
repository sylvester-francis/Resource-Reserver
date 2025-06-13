# Resource Reserver

**Enterprise Resource Management and Booking System**

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/) [![Express.js](https://img.shields.io/badge/Express.js-404D59?style=flat&logo=express&logoColor=white)](https://expressjs.com/) [![Alpine.js](https://img.shields.io/badge/Alpine.js-8BC34A?style=flat&logo=alpine.js&logoColor=white)](https://alpinejs.dev/) [![EJS](https://img.shields.io/badge/EJS-B4CA65?style=flat&logo=ejs&logoColor=black)](https://ejs.co/) [![Docker](https://img.shields.io/badge/Container-Docker-2496ED?style=flat&logo=docker&logoColor=white)](https://www.docker.com/)

## Overview

Resource Reserver is a comprehensive resource management platform designed for organizations that need to efficiently schedule and manage shared assets. The system provides conflict-free booking, real-time availability tracking, and comprehensive audit trails through a modern web interface and REST API.

**✨ Version 2.0** features a completely rewritten architecture with **Express.js + Alpine.js frontend** and **FastAPI backend**, delivering superior performance, maintainability, and user experience.

---

## 🎉 Version 2.0 Release Notes

**Resource Reserver v2.0** represents a complete architectural transformation with modern technologies and enhanced developer experience.

### 🔥 What's New in Version 2.0

**🏗️ Complete Architecture Overhaul**
- **Express.js + Alpine.js Frontend**: Modern server-side rendering with reactive components
- **Zero Build Process**: Direct development and deployment without compilation complexity
- **Clean Separation**: Independent frontend and backend services with Docker orchestration
- **Enhanced Performance**: Server-side rendering for better SEO and faster initial page loads

**🐳 Production-Ready Containerization**
- **Docker Images**: Available on GitHub Container Registry (`ghcr.io/sylvester-francis/resource-reserver`)
- **Multi-Service Architecture**: Separate containers for frontend, backend, and database
- **Development Profiles**: Hot reload support for rapid development
- **Health Monitoring**: Built-in health checks and service status endpoints

**⚡ Developer Experience Improvements**
- **Instant Development**: `npm start` + `uvicorn` - no build steps required
- **Modern CI/CD**: GitHub Actions with automated testing and Docker publishing
- **Comprehensive Documentation**: Updated architecture diagrams and deployment guides
- **Quality Assurance**: Automated linting, testing, and code quality checks

### 🛠️ Migration Benefits

| Aspect | Version 1.0 | Version 2.0 |
|--------|-------------|-------------|
| **Frontend** | Static HTML/JS | Express.js + EJS + Alpine.js |
| **Development** | Complex build process | Zero compilation required |
| **Deployment** | Manual setup | Docker Compose orchestration |
| **Architecture** | Monolithic | Clean separation of concerns |
| **Performance** | Client-side only | Server-side rendering + client reactivity |
| **Maintenance** | Build dependencies | Direct code editing |

### 📦 Docker Images

Resource Reserver provides pre-built Docker images published to GitHub Container Registry for easy deployment:

```bash
# Pull latest images directly
docker pull ghcr.io/sylvester-francis/resource-reserver/backend:latest
docker pull ghcr.io/sylvester-francis/resource-reserver/frontend:latest

# Use pre-built images with Docker Compose (Recommended)
wget https://raw.githubusercontent.com/sylvester-francis/Resource-Reserver/main/docker-compose.registry.yml
docker compose -f docker-compose.registry.yml up -d

# Or clone and use registry images
git clone https://github.com/sylvester-francis/Resource-Reserver.git
cd Resource-Reserver
docker compose -f docker-compose.registry.yml up -d
```

**Available Image Tags:**
- `latest` - Latest stable release from main branch
- `feature-refactor-frontend` - Latest development from feature branch
- `<branch>-<sha>` - Specific commit builds

### 🚀 Quick Start Version 2.0

```bash
# Using Docker (Recommended)
git clone https://github.com/sylvester-francis/Resource-Reserver.git
cd Resource-Reserver
docker compose up -d

# Access application
# Frontend: http://localhost:3000
# Backend API: http://localhost:8000/docs
```

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
- [Installation](#installation)
- [Configuration](#configuration)
- [API Documentation](#api-documentation)
- [User Interface](#user-interface)
- [Development](#development)
- [Testing](#testing)
- [Contributing](#contributing)
- [Support](#support)

---

## Architecture

Resource Reserver follows a modern, clean architecture with separated frontend and backend services.

### System Overview

```mermaid
graph TB
    subgraph "User Layer"
        U1[Business Users]
        U2[System Administrators]
        U3[External Systems]
    end
    
    subgraph "Docker Infrastructure"
        subgraph "Frontend Container"
            WEB[Express.js Server<br/>Port 3000]
            EJS[EJS Templates<br/>views/]
            ALPINE[Alpine.js<br/>public/js/]
            CSS[Static CSS<br/>public/css/]
        end
        
        subgraph "Backend Container"
            API[FastAPI Server<br/>Port 8000]
            AUTH[JWT Authentication<br/>Cookie-based]
            ROUTES[API Routes<br/>app/main.py]
            BG[Background Tasks<br/>Cleanup]
        end
        
        subgraph "Business Logic Layer"
            RS[Resource Service<br/>app/services.py]
            ReS[Reservation Service<br/>app/services.py]
            US[User Service<br/>app/services.py]
        end
        
        subgraph "Data Layer"
            DB[(Database<br/>SQLite/PostgreSQL<br/>data/)]
            FS[File Storage<br/>CSV/Logs<br/>uploads/]
        end
    end
    
    %% User connections
    U1 --> WEB
    U2 --> WEB
    U3 --> API
    
    %% Frontend architecture
    WEB --> EJS
    WEB --> ALPINE
    WEB --> CSS
    EJS --> ALPINE
    
    %% Frontend to Backend communication
    WEB -.->|API Proxy<br/>HTTP Calls| API
    ALPINE -.->|AJAX Requests<br/>Session Validation| API
    
    %% Backend internal
    API --> AUTH
    API --> ROUTES
    API --> BG
    ROUTES --> RS
    ROUTES --> ReS
    ROUTES --> US
    
    %% Services to data
    RS --> DB
    ReS --> DB
    US --> DB
    
    RS --> FS
    ReS --> FS
    
    %% Background services
    BG --> DB
    BG --> FS
    
    %% Session management
    WEB -.->|Cookie Storage<br/>Session Management| AUTH
    
    %% Styling
    classDef userClass fill:#2E86AB,stroke:#fff,stroke-width:2px,color:#fff
    classDef containerClass fill:#A23B72,stroke:#fff,stroke-width:2px,color:#fff
    classDef backendClass fill:#F18F01,stroke:#fff,stroke-width:2px,color:#fff
    classDef serviceClass fill:#4CAF50,stroke:#fff,stroke-width:2px,color:#fff
    classDef dataClass fill:#C73E1D,stroke:#fff,stroke-width:2px,color:#fff
    
    class U1,U2,U3 userClass
    class WEB,EJS,ALPINE,CSS containerClass
    class API,AUTH,ROUTES,BG backendClass
    class RS,ReS,US serviceClass
    class DB,FS dataClass
```

### Architecture Components

| Layer | Technology | Responsibility |
|-------|------------|----------------|
| **Frontend** | Express.js + EJS + Alpine.js | Server-side rendering, user interface, client-side reactivity |
| **Backend** | FastAPI + Python | REST API, business logic, authentication |
| **Database** | SQLite/PostgreSQL | Data persistence and integrity |
| **Background** | AsyncIO Tasks | Automated cleanup and maintenance |

### Key Architectural Decisions

**Frontend**: 
- **Express.js** for server-side rendering and session management
- **EJS templating** for clean, maintainable HTML generation
- **Alpine.js** for reactive client-side interactions without build complexity
- **No build process** - direct development and deployment

**Backend**:
- **FastAPI** for high-performance API with automatic documentation
- **SQLAlchemy** for database abstraction and migrations
- **JWT authentication** with secure token management
- **Background tasks** for automated system maintenance

---

## Features

### ✅ Verified Core Functionality

- **Resource Management**: Create, categorize, and manage organizational resources with flexible attribute systems
- **Advanced Search**: Backend-powered search with query parameters and real-time filtering
- **Reservation System**: Time-based booking with automatic conflict detection and prevention
- **Interactive Calendar**: 7-day availability schedule with visual time slot management
- **User Authentication**: Secure JWT-based authentication with cookie session management
- **Availability Engine**: Real-time availability checking across configurable time periods
- **Audit System**: Complete activity logging for compliance and operational transparency
- **CSV Upload**: Bulk resource creation with validation, error reporting, and success feedback
- **Real-time Updates**: Immediate UI updates without page refreshes
- **Session Management**: Enhanced session validation with automatic login redirects on token expiration

### ✅ Verified Technical Features

- **Modern Web Interface**: Server-side rendered EJS templates with Alpine.js reactive components
- **REST API**: Complete OpenAPI documentation with interactive testing at `/docs`
- **Database Abstraction**: Support for SQLite (development) and PostgreSQL (production)
- **Background Processing**: Automated cleanup and maintenance tasks
- **Health Monitoring**: System status endpoints and performance metrics
- **Security**: Input validation, SQL injection prevention, and secure session management
- **Docker Ready**: Complete containerization with production and development profiles
- **No Build Process**: Direct development and deployment without compilation steps

---

## Use Cases

### Target Organizations

- **Corporate Environments**: Meeting rooms, equipment checkout, shared facilities
- **Educational Institutions**: Classrooms, laboratories, research equipment
- **Healthcare Facilities**: Medical equipment, procedure rooms, specialized tools
- **Manufacturing**: Production equipment, quality assurance tools, maintenance scheduling
- **Co-working Spaces**: Desk reservations, conference rooms, amenities

---

## Installation

### Prerequisites

- **Python 3.11+**
- **Node.js 18+**
- **npm package manager**
- **Git version control system**

### Quick Start

```bash
# Clone repository
git clone https://github.com/sylvester-francis/Resource-Reserver.git
cd Resource-Reserver

# Start Backend (Terminal 1)
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Start Frontend (Terminal 2)
cd frontend
npm install
npm start

# Access the application
# Frontend: http://localhost:3000
# Backend API: http://localhost:8000/docs
```

### ✅ Verified Application Status

The application is **fully functional** with all features tested and working:

- ✅ **User Registration & Login**: Complete authentication flow
- ✅ **Resource Management**: Create, edit, search, and filter resources
- ✅ **Reservation System**: Book resources with conflict detection
- ✅ **CSV Upload**: Bulk import with validation and feedback
- ✅ **Advanced Search**: Real-time filtering with backend integration
- ✅ **Availability Calendar**: 7-day schedule visualization
- ✅ **Real-time Updates**: Immediate UI feedback without page reloads
- ✅ **Session Management**: Secure cookie-based authentication
- ✅ **API Integration**: All frontend-backend communication working

### Docker Deployment

#### Production Deployment

The production deployment uses separate containers for frontend and backend services with Docker Compose orchestration.

**Option 1: Using Pre-built Registry Images (Recommended)**

```bash
# Download registry compose file
wget https://raw.githubusercontent.com/sylvester-francis/Resource-Reserver/main/docker-compose.registry.yml

# Set environment variables
echo "SECRET_KEY=your-secure-secret-key" > .env
echo "POSTGRES_PASSWORD=your-postgres-password" >> .env

# Start production services with registry images
docker compose -f docker-compose.registry.yml up -d

# Check service status
docker compose -f docker-compose.registry.yml ps
```

**Option 2: Building from Source**

```bash
# Clone and navigate to project
git clone https://github.com/sylvester-francis/Resource-Reserver.git
cd Resource-Reserver

# Set environment variables
echo "SECRET_KEY=your-secure-secret-key" > .env
echo "POSTGRES_PASSWORD=your-postgres-password" >> .env

# Start production services (builds locally)
docker compose up -d

# Or start specific services
docker compose up -d backend frontend

# Check service status
docker compose ps
```

#### Development with Docker

Run both frontend and backend services in development mode with hot reload.

```bash
# Start all development services
docker compose --profile dev up -d

# Or manually start each service
docker compose up -d backend
docker compose up -d frontend

# Monitor logs
docker compose logs -f frontend backend
```

#### Docker Services

**Production Services:**
- **backend**: FastAPI application (Port 8000)
- **frontend**: Express.js application (Port 3000)
- **postgres**: PostgreSQL database (Port 5432, optional)

**Development Services:**
- **backend**: FastAPI with uvicorn reload (Port 8000)
- **frontend**: Express.js with nodemon auto-restart (Port 3000)

#### Docker Images

The project includes multiple Docker configurations:

1. **Dockerfile.backend** - FastAPI backend service
2. **Dockerfile.frontend** - Express.js frontend service  
3. **Dockerfile.dev** - Development environment with hot reload
4. **docker-compose.yml** - Multi-service orchestration

#### Service Configuration

**Production Services Configuration:**

```yaml
services:
  # FastAPI Backend Service
  backend:
    build:
      context: .
      dockerfile: Dockerfile.backend
    ports:
      - "8000:8000"
    environment:
      - ENVIRONMENT=production
      - DATABASE_URL=sqlite:///./data/resource_reserver.db
    volumes:
      - ./data:/app/data
    restart: unless-stopped

  # Express.js Frontend Service
  frontend:
    build:
      context: .
      dockerfile: Dockerfile.frontend
    ports:
      - "3000:3000"
    environment:
      - NODE_ENV=production
      - API_BASE_URL=http://backend:8000
    depends_on:
      - backend
    restart: unless-stopped
```

#### Environment Variables

**Development Environment:**

```bash
# Backend configuration (.env in root)
ENVIRONMENT=development
DATABASE_URL=sqlite:///./data/resource_reserver_dev.db
SECRET_KEY=dev-secret-key

# Frontend configuration (frontend/.env)
NODE_ENV=development
PORT=3000
API_BASE_URL=http://localhost:8000
```

**Production Environment:**

```bash
# Backend configuration
ENVIRONMENT=production
DATABASE_URL=postgresql://user:password@host:5432/database
SECRET_KEY=your-secure-secret-key-here

# Frontend configuration
NODE_ENV=production
PORT=3000
API_BASE_URL=http://backend:8000
```

#### Troubleshooting

**Frontend Service Issues:**
```bash
# Check frontend dependencies
cd frontend
npm install

# Restart frontend service
docker compose restart frontend

# Check frontend logs
docker compose logs frontend
```

**Backend Service Issues:**
```bash
# Check backend dependencies
pip install -r requirements.txt

# Restart backend service
docker compose restart backend

# Check backend logs
docker compose logs backend
```

**Service Communication Issues:**
```bash
# Check all services
docker compose ps

# Test backend from frontend container
docker compose exec frontend curl http://backend:8000/health

# Check network connectivity
docker network ls
docker network inspect resource-reserver_default
```

#### Health Checks

**Container Health:**
```bash
# Check container health
docker ps
docker logs <container-id>

# Test health endpoint
curl -f http://localhost:8000/health
```

**Frontend Assets:**
```bash
# Verify frontend service is running
curl -f http://localhost:3000/
curl -f http://localhost:3000/login

# Check static assets
curl -f http://localhost:3000/css/styles.css
curl -f http://localhost:3000/js/app.js
```

---

## Configuration

### Environment Variables

#### Backend (.env in root directory)
```bash
DATABASE_URL=sqlite:///./data/resource_reserver.db
ENVIRONMENT=development
SECRET_KEY=your-secret-key-here
```

#### Frontend (.env in frontend directory)
```bash
PORT=3000
API_BASE_URL=http://localhost:8000
NODE_ENV=development
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

### ✅ Verified Core Endpoints

| Method | Endpoint | Description | Authentication | Status |
|--------|----------|-------------|----------------|---------|
| `POST` | `/register` | User registration | No | ✅ Working |
| `POST` | `/token` | User authentication | No | ✅ Working |
| `GET` | `/resources/` | List resources | No | ✅ Working |
| `POST` | `/resources/` | Create resource | Yes | ✅ Working |
| `GET` | `/resources/search` | Advanced search | No | ✅ Working |
| `POST` | `/resources/upload` | CSV bulk upload | Yes | ✅ Working |
| `GET` | `/resources/{id}/availability` | Resource schedule | No | ✅ Working |
| `GET` | `/resources/availability/summary` | System statistics | No | ✅ Working |
| `POST` | `/reservations/` | Create reservation | Yes | ✅ Working |
| `GET` | `/reservations/my` | User reservations | Yes | ✅ Working |
| `DELETE` | `/reservations/{id}/cancel` | Cancel reservation | Yes | ✅ Working |
| `GET` | `/reservations/{id}/history` | Reservation audit | Yes | ✅ Working |
| `GET` | `/health` | System health check | No | ✅ Working |

---

## User Interface

### Web Application

The web interface provides a complete user experience built with modern technologies:

**Access URL**: `http://localhost:3000`

#### ✅ Verified Key Features

1. **User Registration and Authentication**: Secure account creation and login with session management
2. **Resource Discovery**: Browse and search available resources with real-time filtering
3. **Reservation Management**: Create, view, and cancel bookings with immediate UI updates
4. **Interactive Calendar**: 7-day availability schedule with visual time slots
5. **Dashboard**: Personal reservation overview and system statistics
6. **CSV Import**: Bulk resource creation with validation, error reporting, and success feedback
7. **Advanced Search**: Backend-powered search with query parameters and filtering
8. **Real-time Updates**: All actions provide immediate feedback without page refreshes

#### Technology Stack

- **Express.js**: Server-side rendering and API proxy
- **EJS Templates**: Clean, maintainable HTML generation
- **Alpine.js**: Reactive client-side interactions
- **Modern CSS**: Responsive design with animations and transitions

#### User Flow

1. **Login/Register** → Secure authentication with cookie-based sessions
2. **Dashboard** → Overview of resources and personal reservations
3. **Resource Management** → Browse, search, filter, and create resources
4. **Reservation System** → Book resources with conflict detection
5. **Profile Management** → View and cancel personal reservations

---

## Development

### Development Environment Setup

#### Backend Development
```bash
# Install Python dependencies
pip install -r requirements.txt

# Run development server with auto-reload
uvicorn app.main:app --reload --port 8000
```

#### Frontend Development
```bash
# Install Node.js dependencies
npm install

# Start development server
npm run dev  # Uses nodemon for auto-restart

# Or start normally
npm start
```

### Project Structure

```
resource-reserver/
├── app/                          # FastAPI backend service
│   ├── main.py                  # Application entry point & API routes
│   ├── auth.py                  # JWT authentication logic
│   ├── database.py              # Database configuration & connection
│   ├── models.py                # SQLAlchemy data models
│   ├── schemas.py               # Pydantic API schemas
│   └── services.py              # Business logic layer
├── frontend/                     # Express.js frontend service
│   ├── server.js               # Express server with API proxy
│   ├── package.json            # Node.js dependencies
│   ├── views/                  # EJS templates
│   │   ├── dashboard.ejs       # Main application dashboard
│   │   ├── login.ejs           # Authentication pages
│   │   └── partials/           # Reusable template components
│   │       └── modals.ejs      # Modal dialogs
│   ├── public/                 # Static assets (served directly)
│   │   ├── css/                # Stylesheets
│   │   │   └── styles.css      # Main application styles
│   │   └── js/                 # Client-side JavaScript
│   │       └── app.js          # Alpine.js application logic
│   └── uploads/                # File upload storage
├── cli/                         # Command-line interface
│   ├── main.py                 # CLI entry point
│   ├── client.py               # API client
│   ├── config.py               # Configuration management
│   └── utils.py                # Utility functions
├── tests/                       # Comprehensive test suite
│   ├── test_api/               # API endpoint tests
│   ├── test_cli/               # CLI interface tests
│   └── test_services/          # Business logic tests
├── .github/workflows/          # CI/CD pipeline
│   └── ci.yml                  # GitHub Actions workflow
├── Dockerfile.backend          # Backend container configuration
├── Dockerfile.frontend         # Frontend container configuration
├── docker-compose.yml          # Multi-service orchestration
├── requirements.txt            # Python dependencies
├── pyproject.toml             # Python project configuration
└── README.md                  # Complete documentation
```

### Development Workflow

1. Create feature branch from `main`
2. Make changes with corresponding tests
3. Test both frontend and backend
4. Submit pull request with descriptive commit messages
5. Address review feedback and ensure CI passes

### Code Quality Standards

#### Backend Quality Checks
```bash
# Code formatting and linting
ruff format .
ruff check .
pytest
```

#### Frontend Quality Checks
```bash
# ESLint (if configured)
npm run lint

# Manual testing
npm start
```

---

## Testing

### Test Execution

```bash
# Run backend tests
pytest

# Run with coverage reporting
pytest --cov=app --cov=cli --cov-report=html

# Run specific test categories
pytest tests/test_api/      # API tests
pytest tests/test_cli/      # CLI tests
pytest tests/test_services/ # Business logic tests
```

### Frontend Testing

Frontend testing is done through:
- **Manual browser testing**
- **API endpoint validation**
- **User interaction verification**

### Test Categories

- **Unit Tests**: Individual component functionality
- **Integration Tests**: Component interaction testing
- **API Tests**: HTTP endpoint validation
- **End-to-End Tests**: Complete user workflow validation

---

## Contributing

### Getting Started

1. Fork the repository on GitHub
2. Clone your fork locally
3. Create a feature branch
4. Make changes with appropriate tests
5. Submit a pull request

### Code Standards

- Follow PEP 8 Python style guidelines for backend
- Use consistent JavaScript patterns for frontend
- Maintain test coverage above 95%
- Include documentation for new features
- Use conventional commit message format

### Development Setup

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/Resource-Reserver.git
cd Resource-Reserver

# Set up backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Set up frontend
cd frontend
npm install

# Create feature branch
git checkout -b feature/your-feature-name

# Make changes and test
# Backend: uvicorn app.main:app --reload --port 8000
# Frontend: npm start

# Commit and push
git add .
git commit -m "feat: your feature description"
git push origin feature/your-feature-name
```

---

## Support

### Documentation

- **User Guide**: See User Interface section above
- **Developer Guide**: See Development section above
- **API Documentation**: Available at `/docs` endpoint

### Getting Help

- **Issues**: Report bugs and request features on GitHub Issues
- **Discussions**: Community support and questions on GitHub Discussions
- **Documentation**: Comprehensive documentation in the repository

### Reporting Issues

When reporting issues, please include:

- **Environment details**: OS, Python version, Node.js version
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
- [Express.js](https://expressjs.com/) - Fast, minimalist web framework for Node.js
- [Alpine.js](https://alpinejs.dev/) - Lightweight reactive framework
- [EJS](https://ejs.co/) - Effective JavaScript templating
- [SQLAlchemy](https://www.sqlalchemy.org/) - Database toolkit
- [pytest](https://pytest.org/) - Testing framework
- [Ruff](https://docs.astral.sh/ruff/) - Fast Python linter
- [Docker](https://www.docker.com/) - Containerization platform

---

## Changelog

### Version 2.0.0 - Clean Architecture (Current)

**Major Release**: Complete architecture overhaul with clean separation of concerns

#### 🚀 Major Changes

**Clean Architecture Implementation**
- **Separated Frontend/Backend**: Express.js frontend + FastAPI backend
- **Server-Side Rendering**: EJS templates for better performance and SEO
- **Alpine.js Integration**: Reactive UI without build complexity
- **No Build Process**: Direct development and deployment
- **Session Management**: Secure cookie-based authentication
- **Docker-Ready**: Complete containerization with production and development profiles

**Migration Success**
- **From**: TypeScript + Vite + Complex Build Process + Component Issues
- **To**: Express.js + EJS + Alpine.js + Simple Development
- **Result**: A clean, maintainable, fully-functional application with modern features and excellent developer experience

**Improved Developer Experience**
- **Instant Development**: No compilation or build steps required
- **Clear Separation**: Frontend and backend concerns completely separated
- **Modern Stack**: Latest versions of all technologies
- **Simple Deployment**: Easy to understand and deploy with Docker

**Enhanced Features**
- **Real-time UI Updates**: Immediate feedback without page refreshes
- **Advanced Search**: Backend-powered search with filtering capabilities
- **Resource Scheduling**: Interactive 7-day availability calendar
- **Better Error Handling**: User-friendly error messages and validation
- **Improved Performance**: Server-side rendering and optimized assets
- **Mobile Responsive**: Works perfectly on all device sizes

#### 📊 Technical Improvements

**Architecture**
- Frontend: Express.js + EJS + Alpine.js
- Backend: FastAPI + SQLAlchemy + JWT
- Database: SQLite (dev) / PostgreSQL (prod)
- Containerization: Docker + Docker Compose
- No build tools or complex configurations required

**Developer Experience**
- Simple `npm start` for frontend
- Simple `uvicorn` command for backend
- Docker development environment with hot reload
- Clear project structure and comprehensive documentation

**✅ Verified Functionality Enhancements**
- ✅ **UI Refresh Problem**: Fixed reservations showing immediately after creation
- ✅ **Modal Functionality**: All modals (create resource, reservations, CSV upload, availability) working
- ✅ **Real-time Updates**: UI updates immediately without page reloads
- ✅ **Error Handling**: Enhanced error messages, validation, and user feedback
- ✅ **API Endpoints**: All 13 endpoints tested and verified working
- ✅ **Advanced Search**: Backend search with query parameters and real-time filtering
- ✅ **Resource Scheduling**: Interactive 7-day availability calendar with time slots
- ✅ **Session Management**: Secure cookie-based authentication with proper token handling
- ✅ **CSV Upload**: Enhanced bulk upload with validation, error reporting, and success feedback
- ✅ **Authentication Flow**: Complete registration, login, and session management working
- ✅ **Docker Integration**: Full containerization with production and development profiles
- ✅ **Performance**: Zero build process with instant development and deployment

### Version 1.0.0 - Initial Release

- Initial release with core reservation functionality
- Monolithic JavaScript frontend
- FastAPI backend with comprehensive API
- Complete test suite and documentation