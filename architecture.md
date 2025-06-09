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
    
    subgraph "External Services"
        LDAP[LDAP/AD]
        SMTP[Email Service]
        BACKUP[Backup Service]
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
    
    APP2 --> RS
    APP2 --> ReS
    APP2 --> US
    APP2 --> AS
    
    APP3 --> RS
    APP3 --> ReS
    APP3 --> US
    APP3 --> AS
    
    %% Services to data
    RS --> DB
    ReS --> DB
    US --> DB
    AS --> DB
    
    RS --> FS
    ReS --> FS
    
    RS --> CACHE
    ReS --> CACHE
    
    %% Background services
    CLEANUP --> DB
    MONITOR --> DB
    AUDIT --> FS
    
    %% External integrations
    AS --> LDAP
    CLEANUP --> SMTP
    BACKUP --> DB
    BACKUP --> FS
    
    %% Styling
    classDef userClass fill:#2E86AB,stroke:#fff,stroke-width:2px,color:#fff
    classDef clientClass fill:#A23B72,stroke:#fff,stroke-width:2px,color:#fff
    classDef appClass fill:#F18F01,stroke:#fff,stroke-width:2px,color:#fff
    classDef serviceClass fill:#4CAF50,stroke:#fff,stroke-width:2px,color:#fff
    classDef dataClass fill:#C73E1D,stroke:#fff,stroke-width:2px,color:#fff
    classDef bgClass fill:#FFE082,stroke:#333,stroke-width:2px
    classDef extClass fill:#9E9E9E,stroke:#fff,stroke-width:2px,color:#fff
    
    class U1,U2,U3 userClass
    class WEB,CLI,API clientClass
    class LB appClass
    class APP1,APP2,APP3 appClass
    class RS,ReS,US,AS serviceClass
    class DB,FS,CACHE dataClass
    class CLEANUP,MONITOR,AUDIT bgClass
    class LDAP,SMTP,BACKUP extClass
```

## Component Details

### Client Layer
- **Web Browser**: React/Vue.js SPA or vanilla JavaScript interface
- **CLI Interface**: Typer-based command-line tool with rich output
- **API Clients**: External systems integrating via REST API

### Application Layer
- **FastAPI Applications**: Horizontally scalable Python web services
- **Load Balancer**: Nginx for SSL termination and request distribution
- **Auto-scaling**: Container orchestration with Docker/Kubernetes

### Business Logic
- **Resource Service**: CRUD operations for organizational resources
- **Reservation Service**: Booking logic with conflict detection
- **User Service**: Account management and authentication
- **Auth Service**: JWT token management and authorization

### Data Layer
- **Primary Database**: PostgreSQL/MySQL for transactional data
- **File Storage**: Local/cloud storage for CSV imports and logs
- **Cache**: Redis for session storage and performance optimization

### Background Services
- **Cleanup Service**: Automated removal of expired reservations
- **Health Monitor**: System status and performance metrics
- **Audit Logger**: Compliance and activity tracking

## Data Flow Architecture

```mermaid
sequenceDiagram
    participant User
    participant WebApp
    participant LoadBalancer
    participant FastAPI
    participant Services
    participant Database
    participant Cache
    
    User->>WebApp: Create Reservation Request
    WebApp->>LoadBalancer: HTTP POST /reservations
    LoadBalancer->>FastAPI: Route to Available Instance
    FastAPI->>Services: Validate & Process Request
    
    Services->>Cache: Check Resource Availability
    alt Cache Miss
        Services->>Database: Query Resource Status
        Database-->>Services: Resource Data
        Services->>Cache: Update Cache
    end
    
    Services->>Database: Check Time Conflicts
    Database-->>Services: Availability Confirmed
    
    Services->>Database: Create Reservation Record
    Database-->>Services: Reservation Created
    
    Services->>Cache: Invalidate Related Cache
    Services-->>FastAPI: Success Response
    FastAPI-->>LoadBalancer: HTTP 201 Created
    LoadBalancer-->>WebApp: Response
    WebApp-->>User: Confirmation Display
```

## Deployment Architecture

```mermaid
graph LR
    subgraph "Production Environment"
        subgraph "Load Balancer Tier"
            LB1[Nginx LB 1]
            LB2[Nginx LB 2]
        end
        
        subgraph "Application Tier"
            APP1[FastAPI Pod 1]
            APP2[FastAPI Pod 2]
            APP3[FastAPI Pod 3]
        end
        
        subgraph "Data Tier"
            DB1[(Primary DB)]
            DB2[(Replica DB)]
            REDIS[(Redis Cluster)]
        end
        
        subgraph "Storage Tier"
            S3[File Storage]
            BACKUP[Backup Storage]
        end
    end
    
    Internet --> LB1
    Internet --> LB2
    
    LB1 --> APP1
    LB1 --> APP2
    LB2 --> APP2
    LB2 --> APP3
    
    APP1 --> DB1
    APP2 --> DB1
    APP3 --> DB1
    
    DB1 --> DB2
    
    APP1 --> REDIS
    APP2 --> REDIS
    APP3 --> REDIS
    
    APP1 --> S3
    APP2 --> S3
    APP3 --> S3
    
    DB1 --> BACKUP
    S3 --> BACKUP
    
    classDef lbClass fill:#81C784,stroke:#fff,stroke-width:2px,color:#fff
    classDef appClass fill:#FFB74D,stroke:#fff,stroke-width:2px,color:#fff
    classDef dataClass fill:#F06292,stroke:#fff,stroke-width:2px,color:#fff
    classDef storageClass fill:#9575CD,stroke:#fff,stroke-width:2px,color:#fff
    
    class LB1,LB2 lbClass
    class APP1,APP2,APP3 appClass
    class DB1,DB2,REDIS dataClass
    class S3,BACKUP storageClass
```

## Security Architecture

```mermaid
graph TD
    subgraph "Security Layers"
        WAF[Web Application Firewall]
        SSL[SSL/TLS Termination]
        AUTH[JWT Authentication]
        AUTHZ[Authorization Layer]
        VALID[Input Validation]
        ENCRYPT[Data Encryption]
    end
    
    subgraph "Security Controls"
        RATE[Rate Limiting]
        AUDIT[Audit Logging]
        MONITOR[Security Monitoring]
        BACKUP[Secure Backup]
    end
    
    Internet --> WAF
    WAF --> SSL
    SSL --> AUTH
    AUTH --> AUTHZ
    AUTHZ --> VALID
    VALID --> ENCRYPT
    
    RATE -.-> WAF
    AUDIT -.-> AUTH
    MONITOR -.-> AUTHZ
    BACKUP -.-> ENCRYPT
    
    classDef secClass fill:#E57373,stroke:#fff,stroke-width:2px,color:#fff
    classDef controlClass fill:#81C784,stroke:#fff,stroke-width:2px,color:#fff
    
    class WAF,SSL,AUTH,AUTHZ,VALID,ENCRYPT secClass
    class RATE,AUDIT,MONITOR,BACKUP controlClass
```