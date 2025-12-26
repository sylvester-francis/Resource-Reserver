# Configuration

Resource Reserver is configured through environment variables.

## Environment Variables

### Core Settings

| Variable                      | Description                | Default                            |
| ----------------------------- | -------------------------- | ---------------------------------- |
| `DATABASE_URL`                | Database connection string | `sqlite:///./resource_reserver.db` |
| `SECRET_KEY`                  | JWT signing key            | Required                           |
| `ALGORITHM`                   | JWT algorithm              | `HS256`                            |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Token expiration           | `30`                               |

### Redis Cache

| Variable              | Description                  | Default                    |
| --------------------- | ---------------------------- | -------------------------- |
| `REDIS_URL`           | Redis connection string      | `redis://localhost:6379/0` |
| `CACHE_ENABLED`       | Enable/disable caching       | `true`                     |
| `CACHE_TTL_RESOURCES` | Resource cache TTL (seconds) | `30`                       |
| `CACHE_TTL_STATS`     | Statistics cache TTL         | `60`                       |

### Email Settings

| Variable        | Description                | Default                           |
| --------------- | -------------------------- | --------------------------------- |
| `SMTP_HOST`     | SMTP server hostname       | `localhost`                       |
| `SMTP_PORT`     | SMTP server port           | `587`                             |
| `SMTP_USER`     | SMTP username              | -                                 |
| `SMTP_PASSWORD` | SMTP password              | -                                 |
| `SMTP_FROM`     | From email address         | `noreply@resource-reserver.local` |
| `SMTP_TLS`      | Use TLS                    | `true`                            |
| `EMAIL_ENABLED` | Enable email notifications | `false`                           |

### Rate Limiting

| Variable              | Description          | Default |
| --------------------- | -------------------- | ------- |
| `RATE_LIMIT_ENABLED`  | Enable rate limiting | `true`  |
| `RATE_LIMIT_REQUESTS` | Requests per window  | `100`   |
| `RATE_LIMIT_WINDOW`   | Window in seconds    | `60`    |

## Example Configuration

```bash
# .env file
DATABASE_URL=postgresql://user:pass@localhost:5432/resource_reserver
SECRET_KEY=your-super-secret-key-here
REDIS_URL=redis://localhost:6379/0

# Email
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM=reservations@yourcompany.com
EMAIL_ENABLED=true

# Frontend
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Docker Configuration

When using Docker Compose, configure via `docker-compose.yml`:

```yaml
services:
  backend:
    environment:
      - DATABASE_URL=postgresql://postgres:postgres@db:5432/resource_reserver
      - REDIS_URL=redis://redis:6379/0
      - SECRET_KEY=${SECRET_KEY}
```

## Production Recommendations

!!! warning "Security" - Always use a strong, unique `SECRET_KEY` in production - Use HTTPS for all connections - Store secrets in a vault or secrets manager

!!! tip "Performance" - Enable Redis caching for better performance - Use PostgreSQL instead of SQLite - Configure appropriate rate limits
