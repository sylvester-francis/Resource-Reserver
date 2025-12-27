# Quick start

## Docker Compose (fastest to try)

```bash
docker compose up -d --build
```

Open:

- http://localhost:3000
- http://localhost:8000/docs

To stop:

```bash
docker compose down
```

Optional Postgres:

```bash
docker compose --profile postgres up -d
```

## Local development (no Docker)

```bash
mise run dev
```

This starts:

- Backend: http://localhost:8000
- Frontend: http://localhost:3000

If you want separate terminals:

```bash
mise run backend-dev
mise run frontend-dev
```
