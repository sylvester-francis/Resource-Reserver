# System Architecture

## High-Level Architecture

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
            EJS[EJS Templates]
            ALPINE[Alpine.js Components]
            STATIC[Static Assets<br/>CSS/JS]
        end
        
        subgraph "Backend Container"
            API[FastAPI Server<br/>Port 8000]
            AUTH[JWT Authentication<br/>Cookie-based]
            ROUTES[API Routes]
            BG[Background Tasks]
        end
        
        CLI[Command Line Interface<br/>Typer + Rich]
    end
    
    subgraph "Business Logic Layer"
        RS[ResourceService]
        ReS[ReservationService]  
        US[UserService]
    end
    
    subgraph "Data Layer"
        DB[(SQLite/PostgreSQL<br/>SQLAlchemy ORM)]
        FS[File Storage<br/>CSV/Uploads/Logs]
    end
    
    %% User connections
    U1 --> WEB
    U2 --> CLI
    U3 --> API
    
    %% Frontend architecture
    WEB --> EJS
    WEB --> ALPINE
    WEB --> STATIC
    EJS --> ALPINE
    
    %% Frontend to Backend communication
    WEB -.->|API Proxy<br/>HTTP Calls| API
    ALPINE -.->|AJAX Requests<br/>Session Validation| API
    CLI --> API
    
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
    
    %% Background tasks
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
    classDef cliClass fill:#FFE082,stroke:#333,stroke-width:2px
    
    class U1,U2,U3 userClass
    class WEB,EJS,ALPINE,STATIC containerClass
    class API,AUTH,ROUTES,BG backendClass
    class RS,ReS,US serviceClass
    class DB,FS dataClass
    class CLI cliClass
```

## Component Details

### Frontend Container (Express.js + Alpine.js)
- **Express.js Server**: Server-side rendering with EJS templates and API proxy functionality
- **Alpine.js Components**: Lightweight reactive client-side interactions without build complexity
- **EJS Templates**: Clean, maintainable HTML generation with server-side data injection
- **Static Assets**: Direct serving of CSS and JavaScript files without compilation

### Backend Container (FastAPI)
- **FastAPI Application**: REST API service with automatic OpenAPI documentation
- **Cookie-based Authentication**: Secure session management with JWT tokens stored in HTTP-only cookies
- **API Routes**: Comprehensive endpoints for resources, reservations, and user management

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

### Frontend & User Interface
- **Express.js**: Fast, minimalist web framework for Node.js with server-side rendering
- **EJS**: Embedded JavaScript templating for clean HTML generation  
- **Alpine.js**: Lightweight reactive framework for client-side interactions
- **Typer**: Modern CLI framework built on Click
- **Rich**: Enhanced terminal output with colors and formatting

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
├── app/                          # FastAPI backend service
│   ├── main.py                   # Application entry point & API routes
│   ├── auth.py                   # JWT authentication logic
│   ├── database.py               # Database configuration & connection
│   ├── models.py                 # SQLAlchemy data models
│   ├── schemas.py                # Pydantic API schemas
│   └── services.py               # Business logic layer
├── frontend/                     # Express.js frontend service
│   ├── server.js                 # Express server with API proxy
│   ├── package.json              # Node.js dependencies
│   ├── views/                    # EJS templates
│   │   ├── dashboard.ejs         # Main application dashboard
│   │   ├── login.ejs             # Authentication pages
│   │   └── partials/             # Reusable template components
│   │       └── modals.ejs        # Modal dialogs
│   ├── public/                   # Static assets (served directly)
│   │   ├── css/                  # Stylesheets
│   │   │   └── styles.css        # Main application styles
│   │   └── js/                   # Client-side JavaScript
│   │       └── app.js            # Alpine.js application logic
│   └── uploads/                  # File upload storage
├── cli/                          # Command-line interface
│   ├── main.py                   # CLI entry point with Typer commands
│   ├── client.py                 # API client for CLI operations
│   ├── config.py                 # CLI configuration management
│   └── utils.py                  # Utility functions for CLI
├── tests/                        # Comprehensive test suite
│   ├── test_api/                 # API endpoint tests
│   ├── test_cli/                 # CLI command tests
│   └── test_services/            # Business logic tests
├── .github/workflows/            # CI/CD pipeline configuration
│   └── ci.yml                    # GitHub Actions workflow
├── Dockerfile.backend            # Backend container configuration
├── Dockerfile.frontend           # Frontend container configuration
├── docker-compose.yml            # Multi-service orchestration
├── requirements.txt              # Python dependencies
├── pyproject.toml                # Python project configuration
└── README.md                     # Complete documentation
```

## Deployment Options

### Docker Compose (Recommended)
```bash
# Production deployment (both services)
docker compose up -d backend frontend

# Development with hot reload  
docker compose --profile dev up -d

# Individual services
docker compose up -d backend  # FastAPI only
docker compose up -d frontend # Express.js only
```

### Manual Installation
```bash
# Backend setup
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend setup (separate terminal)
cd frontend
npm install
npm start
```

### Environment Configuration
- **DATABASE_URL**: Database connection string
- **ENVIRONMENT**: Application environment (development/production)
- **CLI_CONFIG_DIR**: CLI configuration directory
- **PORT**: Application server port (default: 8000)