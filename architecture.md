# System Architecture

## High-Level Architecture

```mermaid
graph TB
    subgraph "User Layer"
        U1[Business Users]
        U2[System Administrators]
        U3[External Systems]
    end
    
    subgraph "Client Layer"
        WEB[Web Browser<br/>HTML/CSS/JS]
        CLI[Command Line Interface<br/>Typer + Rich]
        API[External API Clients<br/>REST/HTTP]
    end
    
    subgraph "Application Layer"
        FASTAPI[FastAPI Application<br/>Single Container]
        STATIC[Static File Server<br/>Web Assets]
    end
    
    subgraph "Business Logic Layer"
        RS[ResourceService]
        ReS[ReservationService]  
        US[UserService]
        AUTH[Authentication Layer<br/>JWT + bcrypt]
    end
    
    subgraph "Data Layer"
        DB[(SQLite/PostgreSQL/MySQL<br/>SQLAlchemy ORM)]
        FS[File Storage<br/>CSV Import/Export]
    end
    
    subgraph "Background Tasks"
        CLEANUP[Cleanup Task<br/>Asyncio Background]
        HEALTH[Health Monitoring]
    end
    
    %% User connections
    U1 --> WEB
    U2 --> CLI
    U3 --> API
    
    %% Client to application
    WEB --> FASTAPI
    WEB --> STATIC
    CLI --> FASTAPI
    API --> FASTAPI
    
    %% Application to services
    FASTAPI --> RS
    FASTAPI --> ReS
    FASTAPI --> US
    FASTAPI --> AUTH
    
    %% Services to data
    RS --> DB
    ReS --> DB
    US --> DB
    AUTH --> DB
    
    RS --> FS
    ReS --> FS
    
    %% Background tasks
    CLEANUP --> DB
    HEALTH --> FASTAPI
    
    %% Styling
    classDef userClass fill:#2E86AB,stroke:#fff,stroke-width:2px,color:#fff
    classDef clientClass fill:#A23B72,stroke:#fff,stroke-width:2px,color:#fff
    classDef appClass fill:#F18F01,stroke:#fff,stroke-width:2px,color:#fff
    classDef serviceClass fill:#4CAF50,stroke:#fff,stroke-width:2px,color:#fff
    classDef dataClass fill:#C73E1D,stroke:#fff,stroke-width:2px,color:#fff
    classDef bgClass fill:#FFE082,stroke:#333,stroke-width:2px
    
    class U1,U2,U3 userClass
    class WEB,CLI,API clientClass
    class FASTAPI,STATIC appClass
    class RS,ReS,US,AUTH serviceClass
    class DB,FS dataClass
    class CLEANUP,HEALTH bgClass
```

## Component Details

### Client Layer
- **Web Browser**: Vanilla JavaScript interface with HTML/CSS frontend served as static files
- **CLI Interface**: Typer-based command-line tool with Rich formatting and interactive features
- **API Clients**: External systems integrating via REST API with JWT authentication

### Application Layer
- **FastAPI Application**: Single Python web service handling all API endpoints and web serving
- **Static File Server**: Integrated static file serving for web interface assets (HTML/CSS/JS)
- **CORS Middleware**: Cross-origin resource sharing for web client integration

### Business Logic Layer
- **ResourceService**: CRUD operations, availability checking, CSV import/export
- **ReservationService**: Booking logic with conflict detection and history tracking  
- **UserService**: User account creation and management
- **Authentication Layer**: JWT token generation/validation with bcrypt password hashing

### Data Layer
- **Database**: SQLAlchemy ORM with support for SQLite (dev), PostgreSQL/MySQL (prod)
- **File Storage**: Local filesystem for CSV import/export and application logs
- **Models**: SQLAlchemy models with proper relationships and timezone-aware datetime handling

### Background Tasks
- **Cleanup Task**: Asyncio background task for automatic expired reservation cleanup
- **Health Monitoring**: Built-in health check endpoints for container orchestration

## Data Flow Architecture

```mermaid
sequenceDiagram
    participant User
    participant Client[Web/CLI Client]
    participant FastAPI
    participant Services[Business Services]
    participant Database
    participant BackgroundTask[Cleanup Task]
    
    User->>Client: Create Reservation Request
    Client->>FastAPI: HTTP POST /reservations + JWT
    FastAPI->>FastAPI: Validate JWT Token
    FastAPI->>Services: Call ReservationService.create()
    
    Services->>Database: Check Resource Availability
    Database-->>Services: Resource Status
    
    Services->>Database: Query Existing Reservations
    Database-->>Services: Time Conflict Check
    
    alt No Conflicts
        Services->>Database: Create Reservation Record
        Services->>Database: Create History Entry
        Database-->>Services: Reservation Created
        Services-->>FastAPI: Success Response
        FastAPI-->>Client: HTTP 201 + Reservation Data
        Client-->>User: Confirmation Display
    else Time Conflict
        Services-->>FastAPI: Conflict Error
        FastAPI-->>Client: HTTP 409 Conflict
        Client-->>User: Error Message
    end
    
    Note over BackgroundTask: Runs every 5 minutes
    BackgroundTask->>Database: Query Expired Reservations
    Database-->>BackgroundTask: Expired Records
    BackgroundTask->>Database: Update Status to 'expired'
    BackgroundTask->>Database: Create History Entries
```

## Deployment Architecture

```mermaid
graph TB
    subgraph "Development Environment"
        DEV[Docker Container<br/>:8001 with hot reload]
        DEVDB[(SQLite Dev DB)]
        DEV --> DEVDB
    end
    
    subgraph "Production Environment"
        subgraph "Container Layer"
            DOCKER[FastAPI Container<br/>:8000]
            HEALTH[Health Check<br/>curl /health]
        end
        
        subgraph "Data Layer"
            PRODDB[(PostgreSQL/MySQL<br/>Production DB)]
            VOLUME[Data Volume<br/>./data:/app/data]
        end
        
        subgraph "External Access"
            WEB[Web Interface<br/>Static Files]
            CLI[CLI Interface<br/>External Access]
            REST[REST API<br/>External Clients]
        end
    end
    
    subgraph "Scaling Options"
        LB[Load Balancer<br/>Optional]
        REPLICA[Container Replicas<br/>Horizontal Scaling]
        DBCLUSTER[(Database Cluster<br/>High Availability)]
    end
    
    %% Development connections
    DEV -.-> DEVDB
    
    %% Production connections
    DOCKER --> PRODDB
    DOCKER --> VOLUME
    HEALTH -.-> DOCKER
    
    WEB --> DOCKER
    CLI --> DOCKER
    REST --> DOCKER
    
    %% Scaling connections (optional)
    LB -.-> REPLICA
    REPLICA -.-> DBCLUSTER
    
    %% Styling
    classDef devClass fill:#81C784,stroke:#fff,stroke-width:2px,color:#fff
    classDef prodClass fill:#FFB74D,stroke:#fff,stroke-width:2px,color:#fff
    classDef dataClass fill:#F06292,stroke:#fff,stroke-width:2px,color:#fff
    classDef scaleClass fill:#9575CD,stroke:#fff,stroke-width:2px,color:#fff
    classDef clientClass fill:#64B5F6,stroke:#fff,stroke-width:2px,color:#fff
    
    class DEV,DEVDB devClass
    class DOCKER,HEALTH,VOLUME prodClass
    class PRODDB dataClass
    class LB,REPLICA,DBCLUSTER scaleClass
    class WEB,CLI,REST clientClass
```

## Security Architecture

```mermaid
graph TD
    subgraph "Application Security"
        CORS[CORS Middleware<br/>Origin Validation]
        JWT[JWT Authentication<br/>Bearer Tokens]
        HASH[Password Hashing<br/>bcrypt]
        VALID[Input Validation<br/>Pydantic Schemas]
    end
    
    subgraph "Data Security"
        ORM[SQL Injection Prevention<br/>SQLAlchemy ORM]
        TZ[Timezone-aware Datetime<br/>UTC Handling]
        AUDIT[Audit Trail<br/>Reservation History]
    end
    
    subgraph "Container Security"
        USER[Non-root User<br/>appuser]
        HEALTH[Health Checks<br/>Container Monitoring]
        ENV[Environment Variables<br/>Configuration]
    end
    
    subgraph "Development Security"
        LINT[Code Linting<br/>Ruff + Flake8]
        TEST[Security Testing<br/>Bandit SAST]
        DEPS[Dependency Scanning<br/>Safety Checks]
    end
    
    %% Security flow
    CORS --> JWT
    JWT --> HASH
    HASH --> VALID
    VALID --> ORM
    
    %% Data protection
    ORM --> TZ
    TZ --> AUDIT
    
    %% Container protection
    USER --> HEALTH
    HEALTH --> ENV
    
    %% Development flow
    LINT --> TEST
    TEST --> DEPS
    
    classDef appSecClass fill:#E57373,stroke:#fff,stroke-width:2px,color:#fff
    classDef dataSecClass fill:#FFB74D,stroke:#fff,stroke-width:2px,color:#fff
    classDef containerSecClass fill:#81C784,stroke:#fff,stroke-width:2px,color:#fff
    classDef devSecClass fill:#9575CD,stroke:#fff,stroke-width:2px,color:#fff
    
    class CORS,JWT,HASH,VALID appSecClass
    class ORM,TZ,AUDIT dataSecClass
    class USER,HEALTH,ENV containerSecClass
    class LINT,TEST,DEPS devSecClass
```

## Technology Stack

### Core Framework
- **FastAPI**: Modern Python web framework with automatic OpenAPI documentation
- **SQLAlchemy**: Database ORM with support for multiple database backends
- **Pydantic**: Data validation and serialization with type hints

### Authentication & Security
- **JWT (JSON Web Tokens)**: Stateless authentication with python-jose
- **bcrypt**: Secure password hashing algorithm
- **CORS**: Cross-origin resource sharing middleware

### CLI & User Interface
- **Typer**: Modern CLI framework built on Click
- **Rich**: Enhanced terminal output with colors and formatting
- **Vanilla JavaScript**: Frontend web interface without frameworks

### Development & Testing
- **pytest**: Python testing framework with fixtures and plugins
- **Ruff**: Fast Python linter and formatter
- **Docker**: Containerization for consistent deployments
- **GitHub Actions**: CI/CD pipeline with automated testing

### Database Support
- **SQLite**: Development and testing database
- **PostgreSQL**: Recommended production database
- **MySQL**: Alternative production database option

## File Structure

```
resource-reserver/
├── app/                          # FastAPI backend application
│   ├── main.py                   # Application entry point and endpoints
│   ├── models.py                 # SQLAlchemy database models
│   ├── schemas.py                # Pydantic request/response schemas
│   ├── services.py               # Business logic layer
│   ├── auth.py                   # Authentication and JWT handling
│   └── database.py               # Database configuration and session
├── cli/                          # Command-line interface
│   ├── main.py                   # CLI entry point with Typer commands
│   ├── client.py                 # API client for CLI operations
│   ├── config.py                 # CLI configuration management
│   └── utils.py                  # Utility functions for CLI
├── web/                          # Web interface static files
│   ├── index.html                # Single-page application
│   ├── css/styles.css            # Stylesheet
│   └── js/script.js              # Client-side JavaScript
├── tests/                        # Comprehensive test suite
│   ├── test_api/                 # API endpoint tests
│   ├── test_cli/                 # CLI command tests
│   └── test_services/            # Business logic tests
├── .github/workflows/            # CI/CD pipeline configuration
│   └── ci.yml                    # GitHub Actions workflow
├── docker-compose.yml            # Container orchestration
├── Dockerfile                    # Container image definition
├── pyproject.toml               # Python project configuration
└── requirements.txt             # Python dependencies
```

## Deployment Options

### Docker Compose (Recommended)
```bash
# Production deployment
docker compose up -d api

# Development with hot reload  
docker compose --profile dev up -d api-dev
```

### Manual Installation
```bash
# Install dependencies
pip install -r requirements.txt

# Run application
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Environment Configuration
- **DATABASE_URL**: Database connection string
- **ENVIRONMENT**: Application environment (development/production)
- **CLI_CONFIG_DIR**: CLI configuration directory
- **PORT**: Application server port (default: 8000)