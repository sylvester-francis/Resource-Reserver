# Testing

## Backend Tests

Run with pytest:

```bash
# All tests
pytest

# With coverage
pytest --cov=app

# Specific test file
pytest tests/test_api/test_resources.py
```

## Frontend Tests

### Unit Tests (Vitest)

```bash
npm run test
npm run test:watch
```

### E2E Tests (Playwright)

```bash
npm run test:e2e
npm run test:e2e:ui      # Interactive mode
npm run test:e2e:headed  # With browser
```

## Test Structure

```
tests/
├── conftest.py           # Shared fixtures
├── test_api/             # API endpoint tests
├── test_services/        # Service layer tests
└── test_cli/             # CLI tests

frontend-next/
├── __tests__/            # Unit tests
└── e2e/                  # Playwright tests
```
