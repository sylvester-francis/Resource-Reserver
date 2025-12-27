# Installation

This section covers the recommended ways to install the project locally.

## Prerequisites

- Git
- Python 3.11
- Node.js 20 (npm) or Bun
- Docker Desktop (optional, for containerized runs)

## Option A: Use mise (recommended)

mise installs tool versions and runs a full setup.

```bash
mise install
mise run setup
```

## Option B: Manual setup

### Backend

```bash
python -m venv venv
source venv/bin/activate
pip install -r apps/backend/requirements.txt
```

### Frontend

```bash
cd apps/frontend
npm ci
```

If you prefer Bun:

```bash
cd apps/frontend
bun install
```

### CLI (optional)

```bash
pip install -e apps/backend
```
