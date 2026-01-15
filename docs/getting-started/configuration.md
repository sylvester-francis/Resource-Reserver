# Configuration

The backend reads environment variables from `.env` by default. The frontend reads variables from `.env.local` in `apps/frontend`.

## Backend (.env)

```env
# Application
ENVIRONMENT=development
DEBUG=false
API_URL=http://localhost:8000
DEFAULT_CSV_PATH=data/csv/resources.csv

# Database
DATABASE_URL=sqlite:///./data/db/resource_reserver_dev.db

# Authentication
SECRET_KEY=your-secret-key-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Rate limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_TESTING_MODE=false
RATE_LIMIT_ANONYMOUS=60/minute
RATE_LIMIT_AUTHENTICATED=200/minute
RATE_LIMIT_ADMIN=500/minute
RATE_LIMIT_AUTH=30/minute
RATE_LIMIT_HEAVY=20/minute

# Redis cache
REDIS_URL=redis://localhost:6379/0
CACHE_ENABLED=true
CACHE_TTL_RESOURCES=30
CACHE_TTL_STATS=60
CACHE_TTL_USER_SESSION=300

# Email
EMAIL_ENABLED=false
SMTP_HOST=localhost
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
SMTP_FROM=noreply@resource-reserver.local
SMTP_FROM_NAME=Resource Reserver
SMTP_TLS=true
SMTP_SSL=false
EMAIL_TEMPLATES_DIR=app/templates/email
```

Notes:

- `API_URL` is used when generating calendar subscription URLs.
- CORS origins default to localhost ports in `apps/backend/app/config.py`. Update that file to allow additional origins.

## Frontend Configuration

### API Proxy Mode (Recommended for Docker/Enterprise)

For Docker deployments or networks with corporate proxies, leave `NEXT_PUBLIC_API_URL` empty. The frontend will proxy all API requests through Next.js rewrites:

```env
# .env (Docker deployment)
NEXT_PUBLIC_API_URL=
INTERNAL_API_URL=http://backend:8000
```

This mode:

- Uses relative URLs in the browser (`/api/v1/...`)
- Proxies requests through the frontend to the backend
- Avoids CORS and corporate proxy issues

### Direct Mode (Local Development)

For local development without Docker:

```env
# apps/frontend/.env.local
NEXT_PUBLIC_API_URL=http://localhost:8000
```

This mode:

- Browser connects directly to the backend API
- Requires backend to be accessible from the browser
