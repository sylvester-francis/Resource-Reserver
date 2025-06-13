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
- **Docker Images**: Available on GitHub Container Registry (`ghcr.io/sylvester-francis/resource-reserver-backend`, `ghcr.io/sylvester-francis/resource-reserver-frontend`)
- **Multi-Service Architecture**: Separate containers for frontend, backend, and database
- **Development Profiles**: Hot reload support for rapid development
- **Health Monitoring**: Built-in health checks and service status endpoints

**🖥️ Professional Command Line Interface**
- **Typer Framework**: Modern, type-safe CLI with Rich terminal output
- **Full Feature Parity**: All web features available via command line
- **Automation Ready**: Scriptable commands for system administration
- **Cross-Platform**: Consistent experience on Windows, macOS, and Linux

**⚡ Developer Experience Improvements**
- **Instant Development**: `npm start` + `uvicorn` - no build steps required
- **Modern CI/CD**: GitHub Actions with automated testing and Docker publishing
- **Comprehensive Documentation**: Updated architecture diagrams and deployment guides
- **Quality Assurance**: Automated linting, testing, and code quality checks

### 🛠️ Migration Benefits

| Aspect | Version 1.0 | Version 2.0 |
|--------|-------------|-------------|
| **Frontend** | Static HTML/JS | Express.js + EJS + Alpine.js |
| **Interfaces** | Web only | Web + Professional CLI |
| **Development** | Complex build process | Zero compilation required |
| **Deployment** | Manual setup | Docker Compose orchestration |
| **Architecture** | Monolithic | Clean separation of concerns |
| **Performance** | Client-side only | Server-side rendering + client reactivity |
| **Automation** | Limited | Full CLI scripting support |
| **Maintenance** | Build dependencies | Direct code editing |

### 📦 Docker Images

Resource Reserver provides pre-built Docker images published to GitHub Container Registry for easy deployment:

```bash
# Pull latest images directly
docker pull ghcr.io/sylvester-francis/resource-reserver-backend:latest
docker pull ghcr.io/sylvester-francis/resource-reserver-frontend:latest

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

---

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
  - [Web Interface](#-web-interface)
  - [Command Line Interface (CLI)](#-command-line-interface-cli)
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
        U1[Business Users<br/>🌐 Web Interface]
        U2[System Administrators<br/>🖥️ CLI + Web]
        U3[External Systems<br/>📡 Direct API]
        U4[Power Users<br/>⚡ CLI Interface]
    end
    
    subgraph "Interface Layer"
        subgraph "Web Frontend Container"
            WEB[Express.js Server<br/>Port 3000]
            EJS[EJS Templates<br/>views/]
            ALPINE[Alpine.js<br/>public/js/]
            CSS[Static CSS<br/>public/css/]
        end
        
        subgraph "CLI Interface"
            CLI[Typer CLI Framework<br/>resource-reserver-cli]
            RICH[Rich Terminal Output<br/>Colored/Interactive]
            CLIENT[HTTP Client<br/>cli/client.py]
            CONFIG[Config Management<br/>~/.reservation-cli/]
        end
    end
    
    subgraph "Docker Infrastructure"
        subgraph "Backend Container"
            API[FastAPI Server<br/>Port 8000]
            AUTH[JWT Authentication<br/>Token + Cookie]
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
    U2 --> CLI
    U3 --> API
    U4 --> CLI
    
    %% Web Frontend architecture
    WEB --> EJS
    WEB --> ALPINE
    WEB --> CSS
    EJS --> ALPINE
    
    %% CLI architecture
    CLI --> RICH
    CLI --> CLIENT
    CLI --> CONFIG
    
    %% Interface to Backend communication
    WEB -.->|API Proxy<br/>HTTP Calls| API
    ALPINE -.->|AJAX Requests<br/>Session Validation| API
    CLIENT -.->|HTTP Requests<br/>JWT Authentication| API
    
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
    CONFIG -.->|JWT Token<br/>Persistence| AUTH
    
    %% Styling
    classDef userClass fill:#2E86AB,stroke:#fff,stroke-width:2px,color:#fff
    classDef interfaceClass fill:#9B59B6,stroke:#fff,stroke-width:2px,color:#fff
    classDef containerClass fill:#A23B72,stroke:#fff,stroke-width:2px,color:#fff
    classDef backendClass fill:#F18F01,stroke:#fff,stroke-width:2px,color:#fff
    classDef serviceClass fill:#4CAF50,stroke:#fff,stroke-width:2px,color:#fff
    classDef dataClass fill:#C73E1D,stroke:#fff,stroke-width:2px,color:#fff
    
    class U1,U2,U3,U4 userClass
    class CLI,RICH,CLIENT,CONFIG interfaceClass
    class WEB,EJS,ALPINE,CSS containerClass
    class API,AUTH,ROUTES,BG backendClass
    class RS,ReS,US serviceClass
    class DB,FS dataClass
```

### Architecture Components

| Layer | Technology | Responsibility |
|-------|------------|----------------|
| **Web Frontend** | Express.js + EJS + Alpine.js | Server-side rendering, user interface, client-side reactivity |
| **CLI Interface** | Typer + Rich + Python | Command-line automation, power user tools, scripting |
| **Backend API** | FastAPI + Python | REST API, business logic, authentication |
| **Database** | SQLite/PostgreSQL | Data persistence and integrity |
| **Background** | AsyncIO Tasks | Automated cleanup and maintenance |

### Key Architectural Decisions

**Dual Interface Strategy**: 
- **Web Interface** for general users with visual interaction and guided workflows
- **CLI Interface** for power users, automation, and system administration
- **Shared API** ensures feature parity and data consistency across interfaces

**Web Frontend**: 
- **Express.js** for server-side rendering and session management
- **EJS templating** for clean, maintainable HTML generation
- **Alpine.js** for reactive client-side interactions without build complexity
- **No build process** - direct development and deployment

**CLI Interface**:
- **Typer framework** for modern, type-safe command-line interface
- **Rich library** for enhanced terminal output with colors and formatting
- **JWT token persistence** for seamless authentication across sessions
- **Configuration management** with user-specific settings storage

**Backend API**:
- **FastAPI** for high-performance API with automatic documentation
- **SQLAlchemy** for database abstraction and migrations
- **JWT authentication** with secure token management (supports both cookie and header auth)
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
- **Command Line Interface**: Professional CLI built with Typer for automation and power users
- **Dual Interface Support**: Seamless integration between web and CLI interfaces

### ✅ Verified Technical Features

- **Modern Web Interface**: Server-side rendered EJS templates with Alpine.js reactive components
- **Professional CLI**: Typer-based command-line interface with Rich terminal output
- **REST API**: Complete OpenAPI documentation with interactive testing at `/docs`
- **Database Abstraction**: Support for SQLite (development) and PostgreSQL (production)
- **Background Processing**: Automated cleanup and maintenance tasks
- **Health Monitoring**: System status endpoints and performance metrics
- **Security**: Input validation, SQL injection prevention, and secure session management
- **Docker Ready**: Complete containerization with production and development profiles
- **No Build Process**: Direct development and deployment without compilation steps
- **Cross-Platform CLI**: Works on Windows, macOS, and Linux with consistent experience

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

# Install CLI (Terminal 3) - Optional
pip install -e .  # Installs CLI as 'resource-reserver-cli'

# Access the application
# Web Interface: http://localhost:3000
# CLI Interface: resource-reserver-cli --help
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

Resource Reserver provides **two powerful interfaces** for different user needs:

### 🌐 Web Interface

The web interface provides a complete user experience built with modern technologies:

**Access URL**: `http://localhost:3000`

![Login Screen](screenshots/Web%20Interface/login-web.png)
*Secure authentication with modern login interface*

![User Registration](screenshots/Web%20Interface/register-web.png)
*Streamlined user registration process*

#### ✅ Verified Key Features

1. **User Registration and Authentication**: Secure account creation and login with session management
2. **Resource Discovery**: Browse and search available resources with real-time filtering
3. **Reservation Management**: Create, view, and cancel bookings with immediate UI updates
4. **Interactive Calendar**: 7-day availability schedule with visual time slots
5. **Dashboard**: Personal reservation overview and system statistics
6. **CSV Import**: Bulk resource creation with validation, error reporting, and success feedback
7. **Advanced Search**: Backend-powered search with query parameters and filtering
8. **Real-time Updates**: All actions provide immediate feedback without page refreshes

![Resource List](screenshots/Web%20Interface/resourcelist-web.png)
*Resource discovery with real-time filtering and search*

![Create Resource](screenshots/Web%20Interface/createresource-web.png)
*Resource creation with tag management*

![Create Reservation](screenshots/Web%20Interface/createreservation-web.png)
*Interactive reservation booking with datetime selection*

![My Reservations](screenshots/Web%20Interface/myreservations-web.png)
*Personal reservation management dashboard*

![Resource History](screenshots/Web%20Interface/resourcehistory-web.png)
*Comprehensive audit trail and reservation history*

![Upload Resources](screenshots/Web%20Interface/uploadresource-web.png)
*Bulk CSV upload with validation and feedback*

![System Status](screenshots/Web%20Interface/systemstatus-web.png)
*System health monitoring and statistics*

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

### 🖥️ Command Line Interface (CLI)

A comprehensive CLI built with **Typer** framework for power users, automation, and system administration.

![CLI Main Interface](screenshots/CLI%20Interface/cli-main.png)
*CLI main interface with available command groups*

![CLI Authentication](screenshots/CLI%20Interface/cli-auth.png)
*Secure CLI authentication and session management*

#### Installation

```bash
# Install CLI as part of the project
pip install -e .

# Access CLI
resource-reserver-cli --help

# Or run directly during development
python -m cli.main --help
```

#### Command Groups

**🔐 Authentication Commands**
```bash
cli auth register      # Register a new user account  
cli auth login         # Login to your account
cli auth logout        # Logout from your account
cli auth status        # Check authentication status
```

**📦 Resource Management Commands**
```bash
cli resources list                    # List all available resources
cli resources search                  # Advanced resource search with filtering
cli resources availability <id>       # Get availability schedule for a resource
cli resources enable <id>            # Enable a resource (maintenance mode)
cli resources disable <id>           # Disable a resource (maintenance mode)  
cli resources create <name>          # Create a new resource
cli resources upload <csv_file>      # Upload resources from CSV file
```

![CLI Resources](screenshots/CLI%20Interface/cli-resources.png)
*Resource management commands with rich terminal output*

**📅 Reservation Management Commands**
```bash
cli reservations create <resource_id> <start> <end>  # Create a new reservation
cli reservations list                                # List your reservations
cli reservations cancel <id>                        # Cancel a reservation
cli reservations history <id>                       # Show reservation history
```

![CLI Reservations](screenshots/CLI%20Interface/cli-reservation.png)
*Reservation management with interactive prompts*

**⚙️ System Commands**
```bash
cli system status       # Check system status and connectivity
cli system summary      # Get system-wide availability summary
cli system cleanup      # Manually trigger cleanup of expired reservations
cli system config       # Show current configuration
```

![CLI System](screenshots/CLI%20Interface/cli-system.png)
*System monitoring and administration commands*

**⚡ Quick Action Commands**
```bash
cli reserve <resource_id> <start> <duration>  # Quick reserve with duration
cli upcoming                                  # Show upcoming reservations
```

#### CLI Features

- **🎨 Rich Terminal Experience**: Colored output, interactive prompts, and structured data display
- **🔒 Secure Authentication**: JWT token management with automatic session handling
- **📊 Advanced Search**: Query-based search with time-based filtering
- **⏰ Flexible Time Input**: Multiple datetime formats and natural language durations
- **📁 File Operations**: CSV upload with validation and error reporting
- **🔄 Real-time Integration**: Changes sync immediately with web interface
- **⚙️ Configuration Management**: Stores settings in `~/.reservation-cli/`
- **🧪 Full Test Coverage**: Comprehensive test suite for all CLI functionality

#### CLI Configuration

```bash
# Configuration directory (customizable via CLI_CONFIG_DIR)
~/.reservation-cli/
├── auth.json          # JWT token storage
└── config.json        # CLI preferences

# Environment variables
API_URL=http://localhost:8000           # Backend API endpoint
CLI_CONFIG_DIR=~/.reservation-cli/      # Configuration directory
```

### Interface Comparison

| Feature | Web Interface | CLI Interface |
|---------|---------------|---------------|
| **Target Users** | General users, visual interaction | Power users, automation, admin |
| **Authentication** | Cookie-based sessions | JWT token management |
| **Resource Management** | ✅ Visual forms and modals | ✅ Command-driven with validation |
| **Search & Filtering** | ✅ Real-time UI filtering | ✅ Advanced query parameters |
| **Reservation Booking** | ✅ Interactive calendar | ✅ Flexible datetime formats |
| **Bulk Operations** | ✅ CSV upload modal | ✅ Scriptable CSV processing |
| **System Monitoring** | ✅ Dashboard widgets | ✅ Rich terminal output |
| **Automation** | ❌ Manual interaction only | ✅ Scriptable, automation-ready |
| **Mobile Support** | ✅ Responsive design | ❌ Terminal-based |
| **Learning Curve** | Low - intuitive UI | Medium - command syntax |
| **Speed (for experts)** | Medium - click navigation | High - direct commands |

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
├── cli/                         # Command-line interface (Typer framework)
│   ├── main.py                 # CLI entry point with command groups
│   ├── client.py               # HTTP API client with session management
│   ├── config.py               # Configuration and auth token storage
│   └── utils.py                # DateTime parsing and formatting utilities
├── tests/                       # Comprehensive test suite
│   ├── test_api/               # API endpoint tests (FastAPI routes)
│   ├── test_cli/               # CLI interface tests (Typer commands)
│   └── test_services/          # Business logic tests (service layer)
├── screenshots/                 # Application screenshots
│   ├── CLI Interface/          # CLI command examples and output
│   └── Web Interface/          # Web UI screenshots
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

**Backend & API:**
- [FastAPI](https://fastapi.tiangolo.com/) - Modern Python web framework
- [SQLAlchemy](https://www.sqlalchemy.org/) - Database toolkit
- [pytest](https://pytest.org/) - Testing framework

**Web Frontend:**
- [Express.js](https://expressjs.com/) - Fast, minimalist web framework for Node.js
- [Alpine.js](https://alpinejs.dev/) - Lightweight reactive framework
- [EJS](https://ejs.co/) - Effective JavaScript templating

**Command Line Interface:**
- [Typer](https://typer.tiangolo.com/) - Modern CLI framework for Python
- [Rich](https://rich.readthedocs.io/) - Rich text and beautiful formatting
- [Requests](https://requests.readthedocs.io/) - HTTP library for Python

**Development & Deployment:**
- [Ruff](https://docs.astral.sh/ruff/) - Fast Python linter and formatter
- [Docker](https://www.docker.com/) - Containerization platform
- [GitHub Actions](https://github.com/features/actions) - CI/CD automation

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
- **Dual Interface Support**: Professional CLI alongside modern web interface
- **Real-time UI Updates**: Immediate feedback without page refreshes
- **Advanced Search**: Backend-powered search with filtering capabilities
- **Resource Scheduling**: Interactive 7-day availability calendar
- **Better Error Handling**: User-friendly error messages and validation
- **Improved Performance**: Server-side rendering and optimized assets
- **Mobile Responsive**: Works perfectly on all device sizes
- **Automation Ready**: Scriptable CLI for power users and system automation

#### 📊 Technical Improvements

**Architecture**
- Web Frontend: Express.js + EJS + Alpine.js
- CLI Interface: Typer + Rich + Python
- Backend API: FastAPI + SQLAlchemy + JWT
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