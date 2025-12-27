# Deployment

## Docker Compose (local or single host)

```bash
docker compose up -d --build
```

This starts:

- Backend API on port 8000
- Frontend UI on port 3000
- Redis cache

Optional Postgres service:

```bash
docker compose --profile postgres up -d
```

## Registry images

If you want to run prebuilt images, use:

```bash
docker compose -f docker-compose.registry.yml up -d
```

## Environment configuration

Set these at minimum for production:

- `SECRET_KEY`
- `DATABASE_URL`
- `REDIS_URL`
- `NEXT_PUBLIC_API_URL`

## Frontend

The frontend is built with `output: 'standalone'` in `apps/frontend/next.config.mjs`, which is supported by `Dockerfile.frontend`.
