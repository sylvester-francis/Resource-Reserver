# Testing

## Backend

```bash
cd apps/backend
pytest tests/ -v
```

## Frontend

```bash
cd apps/frontend
npm run lint
npm run test
```

## End-to-end (Playwright)

Playwright runs against a live backend. Start the backend first:

```bash
mise run backend-dev
```

In another terminal:

```bash
cd apps/frontend
npm run test:e2e
```

You can override the base URL:

```bash
PLAYWRIGHT_BASE_URL=http://localhost:3000 npm run test:e2e
```
