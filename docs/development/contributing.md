# Contributing

I welcome contributions. Please fork the repository, make changes in your fork, and open a pull request against the original repo.

## Contribution workflow

1. Fork the repository on GitHub
1. Clone your fork locally
1. Create a feature branch
1. Make changes and commit
1. Push to your fork
1. Open a pull request to the original repository

Example commands:

```bash
git clone https://github.com/<your-username>/Resource-Reserver.git
cd Resource-Reserver
git checkout -b feat/your-change
git push -u origin feat/your-change
```

## Repository layout

- `apps/backend` - FastAPI backend and CLI
- `apps/frontend` - Next.js frontend
- `docs` - documentation

## Setup

Recommended:

```bash
mise install
mise run setup
```

## Development servers

```bash
mise run dev
```

## Code quality

```bash
mise run lint
mise run format
```

Pre-commit hooks run on commit and pre-push. You can run them manually:

```bash
pre-commit run --all-files
```
