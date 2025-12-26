# Contributing

We welcome contributions! Here's how to get started.

## Development Setup

```bash
# Clone the repo
git clone https://github.com/sylvester-francis/Resource-Reserver.git
cd Resource-Reserver

# Set up backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Set up frontend
cd frontend-next
npm install
```

## Code Style

- Python: Follow PEP 8, use ruff for linting
- TypeScript: ESLint with project config
- Commits: Conventional commit messages

## Pull Requests

1. Create a feature branch
1. Make your changes
1. Write/update tests
1. Submit PR with description

## Testing

```bash
# Backend tests
pytest

# Frontend tests
npm run test
npm run test:e2e
```
