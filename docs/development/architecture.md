# Architecture

## Overview

```
┌─────────────────────────────────────────────────────┐
│                    Frontend                          │
│                  (Next.js 14)                        │
└──────────────────────┬──────────────────────────────┘
                       │ REST API / WebSocket
┌──────────────────────▼──────────────────────────────┐
│                    Backend                           │
│                   (FastAPI)                          │
├─────────────────────────────────────────────────────┤
│  Routes  │  Services  │  Models  │  Core Utilities  │
└──────────┬─────────────────────────┬────────────────┘
           │                         │
    ┌──────▼──────┐           ┌──────▼──────┐
    │  PostgreSQL │           │    Redis    │
    │  (Database) │           │   (Cache)   │
    └─────────────┘           └─────────────┘
```

## Backend Structure

```
app/
├── main.py           # Application entry point
├── config.py         # Configuration
├── database.py       # Database connection
├── models.py         # SQLAlchemy models
├── schemas.py        # Pydantic schemas
├── services.py       # Business logic
├── auth.py           # Authentication
├── rbac.py           # Role-based access
├── routers/          # API endpoints
└── core/             # Utilities (cache, i18n, etc.)
```

## Frontend Structure

```
frontend-next/
├── src/
│   ├── app/          # Next.js app router
│   ├── components/   # React components
│   ├── contexts/     # React contexts
│   ├── lib/          # Utilities
│   └── i18n.ts       # Internationalization
└── e2e/              # Playwright tests
```
