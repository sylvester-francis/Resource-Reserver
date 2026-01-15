# Deployment

## Quick Start (Docker Compose)

1. Copy the environment template:

   ```bash
   cp .env.docker .env
   ```

1. Edit `.env` and set at minimum:

   - `SECRET_KEY` - Generate with `openssl rand -hex 32`
   - `FRONTEND_PORT` - External port for web access (default: 8081)

1. Build and start:

   ```bash
   docker compose up -d --build
   ```

1. Access the application:

   - Web UI: `http://your-server:8081`
   - API Docs: `http://your-server:8000/docs`

## Enterprise Deployment (Behind Corporate Proxy)

For networks with HTTP proxies or firewalls that block direct browser-to-backend connections, the frontend includes a built-in API proxy mode.

### Configuration

In your `.env` file:

```env
# Leave NEXT_PUBLIC_API_URL empty to enable API proxy mode
NEXT_PUBLIC_API_URL=

# Set your proxy settings for build-time dependencies
HTTP_PROXY=http://proxy.corporate.com:8080
HTTPS_PROXY=http://proxy.corporate.com:8080
NO_PROXY=localhost,127.0.0.1,backend,redis,.local

# External port for users (choose an allowed port)
FRONTEND_PORT=8081
```

### How API Proxy Mode Works

When `NEXT_PUBLIC_API_URL` is empty:

1. The frontend is built with relative API URLs (`/api/v1/...`)
1. Next.js rewrites proxy all `/api/*` requests to the backend container
1. Users only need to reach the frontend server
1. No direct browser-to-backend connection required
1. WebSocket connections are also proxied through `/ws`

This eliminates issues with corporate proxies blocking API calls.

### Architecture Diagram

```
┌─────────────┐     ┌─────────────────────────────────────┐
│   Browser   │────▶│  Frontend (Next.js) :8081           │
│             │     │                                     │
│  /api/*  ───┼────▶│  rewrites ──▶ backend:8000/api/*   │
│  /ws     ───┼────▶│  rewrites ──▶ backend:8000/ws      │
└─────────────┘     └──────────────────┬──────────────────┘
                                       │ (internal network)
                    ┌──────────────────▼──────────────────┐
                    │  Backend (FastAPI) :8000            │
                    │  └── Redis :6379                    │
                    └─────────────────────────────────────┘
```

## Port Configuration

| Service  | Variable        | Default | Purpose                   |
| -------- | --------------- | ------- | ------------------------- |
| Frontend | `FRONTEND_PORT` | 8081    | User-facing web UI        |
| Backend  | `BACKEND_PORT`  | 8000    | API (optional if proxied) |
| Redis    | `REDIS_PORT`    | 6379    | Cache (internal only)     |

To disable external access to backend/redis, set their ports to empty:

```env
BACKEND_PORT=
REDIS_PORT=
```

## Production Checklist

- [ ] Generate a secure `SECRET_KEY`
- [ ] Configure `DATABASE_URL` for PostgreSQL (recommended)
- [ ] Set `RATE_LIMIT_ENABLED=true`
- [ ] Configure SMTP for email notifications
- [ ] Set up TLS/SSL termination (nginx, traefik, or load balancer)
- [ ] Configure backup for volumes

## Optional PostgreSQL Database

For production deployments, use PostgreSQL:

```bash
# Start with PostgreSQL profile
docker compose --profile postgres up -d

# Update .env
DATABASE_URL=postgresql://postgres:your-password@postgres:5432/resource_reserver
POSTGRES_PASSWORD=your-password
```

## Registry Images

To run prebuilt images instead of building locally:

```bash
docker compose -f docker-compose.registry.yml up -d
```

## Volumes

Data is persisted in Docker volumes:

- `backend_data` - Database and uploaded files
- `backend_logs` - Application logs
- `redis_data` - Cache data
- `postgres_data` - PostgreSQL data (if enabled)
