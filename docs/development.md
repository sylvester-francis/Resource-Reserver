# Development Guide

## Table of Contents

- [Setup](#setup)
- [Development Workflow](#development-workflow)
- [Git Hooks](#git-hooks)
- [Testing](#testing)
- [Code Quality](#code-quality)
- [Troubleshooting](#troubleshooting)

---

## Setup

### Quick Setup (Recommended)

Run the automated setup script:

```bash
./scripts/setup-dev.sh
```

This will:
- Install mise (if not already installed)
- Install all required tools (Python 3.11, Node 24, Tilt)
- Install Python and Node dependencies
- Configure git hooks
- Create necessary directories

### Manual Setup

If you prefer manual setup:

```bash
# 1. Install mise
curl https://mise.run | sh

# 2. Activate mise in your shell
echo 'eval "$(~/.local/bin/mise activate zsh)"' >> ~/.zshrc  # or ~/.bashrc
source ~/.zshrc  # or ~/.bashrc

# 3. Install tools
mise install

# 4. Install dependencies
pip install -r requirements.txt
cd frontend && npm install && cd ..

# 5. Install git hooks
mise run setup-hooks
```

### Verify Installation

```bash
# Check tool versions
mise current

# Should show:
# python   3.11.x
# node     24.x.x
# tilt     0.x.x

# Test Tilt
tilt version
```

---

## Development Workflow

### Option 1: Tilt (Recommended)

Tilt provides live reload, unified logging, and a visual dashboard.

```bash
# Start all services
tilt up

# Or use mise task
mise run dev
```

**Features:**
- Live reload for both backend and frontend
- Tilt UI at http://localhost:10350
- Unified logs for all services
- Visual service health status
- Manual quality check tasks

**Services:**
- Backend API: http://localhost:8000
- Frontend Web: http://localhost:3000
- API Docs: http://localhost:8000/docs

**Manual Tasks** (click in Tilt UI):
- `lint-backend`: Run ruff on Python code
- `test-backend`: Run pytest test suite
- `format-code`: Format all code

**Stop services:**
```bash
tilt down

# Or use mise task
mise run down
```

### Option 2: Docker Compose

Traditional Docker Compose workflow still works:

```bash
# Start services
docker compose up -d

# Or use mise task
mise run docker

# Stop services
docker compose down

# Or use mise task
mise run docker-down
```

### Option 3: Local Development

Run services locally without containers:

```bash
# Terminal 1: Backend
uvicorn app.main:app --reload --port 8000

# Terminal 2: Frontend
cd frontend && npm run dev

# Terminal 3: Tests (optional)
pytest tests/ --watch
```

---

## Git Hooks

Git hooks automatically run quality checks to ensure code standards before commits reach CI/CD.

### Pre-commit Hooks

Runs **before** each commit:

**Checks:**
- Ruff linting (auto-fixes issues)
- Ruff formatting
- MyPy type checking
- Bandit security scanning
- Safety dependency scanning
- File validations (no large files, no merge conflicts, etc.)
- Hadolint (Dockerfile linting)
- YAML linting
- Markdown formatting

**Example output:**
```
ruff linter (Python)..................Passed
ruff formatter (Python)...............Passed
Check for large files.................Passed
mypy (Python type checking)...........Passed
bandit (Python security)..............Passed
```

**If checks fail:**
```bash
# Auto-fix formatting issues
mise run format

# View specific issues
ruff check .

# Fix and retry commit
git add .
git commit -m "your message"
```

### Post-commit Hooks

Runs **after** each commit to verify it will pass CI/CD:

**Checks:**
- Ruff linting (on changed files)
- Code formatting verification
- MyPy type checking (on changed files)
- Quick test suite (on changed tests)
- Security scan (on changed files)

**Example output:**
```
Running post-commit checks...

1. Running ruff linter...
✓ Ruff linting passed

2. Checking code formatting...
✓ Code formatting is correct

3. Running mypy type checking...
✓ Type checking passed

4. Running quick test suite...
✓ Tests passed

5. Running security scan...
✓ Security scan passed

==========================================
All post-commit checks passed!
This commit should pass CI/CD.
==========================================
```

**If checks fail:**

The commit is still saved, but you'll see warnings:

```bash
# Fix issues
mise run format
mise run lint
mise run test

# Amend the commit
git add .
git commit --amend --no-edit
```

### Bypass Hooks (Emergency Only)

**Not recommended**, but if needed:

```bash
# Skip pre-commit hooks
git commit --no-verify -m "emergency fix"

# Skip specific hook
SKIP=ruff git commit -m "commit message"
```

### Update Hooks

```bash
# Update pre-commit hooks to latest versions
pre-commit autoupdate

# Re-run hooks on all files
pre-commit run --all-files
```

---

## Testing

### Run All Tests

```bash
# Using mise
mise run test

# Or directly
pytest tests/
```

### Run Specific Tests

```bash
# Backend tests only
mise run test-backend
# Or: pytest tests/test_api/ tests/test_services/

# CLI tests only
mise run test-cli
# Or: pytest tests/test_cli/

# Single test file
pytest tests/test_api/test_resources.py

# Single test function
pytest tests/test_api/test_resources.py::test_create_resource
```

### Test with Coverage

```bash
# Generate coverage report
pytest --cov=app --cov=cli --cov-report=html

# View coverage report
open htmlcov/index.html
```

### Watch Mode

```bash
# Automatically re-run tests on file changes
pytest-watch tests/
```

---

## Code Quality

### Linting

```bash
# Run all linters
mise run lint

# Or individually:
ruff check .                    # Fast Python linter
flake8 .                        # Traditional Python linter
mypy app/ cli/                  # Type checking
bandit -r app/ cli/             # Security scanning
hadolint Dockerfile.*           # Dockerfile linting
yamllint .                      # YAML linting
```

### Formatting

```bash
# Format all code
mise run format

# Or individually:
ruff format .                   # Python formatting
black .                         # Alternative Python formatter
mdformat docs/                  # Markdown formatting
```

### View All Quality Issues

```bash
# Comprehensive quality check
ruff check . --output-format=github
mypy app/ cli/ --pretty
```

---

## Available Tasks

View all available tasks:

```bash
mise tasks
```

Output:
```
dev          Start development environment with Tilt
down         Stop Tilt development environment
docker       Start services with Docker Compose
docker-down  Stop Docker Compose services
format       Format all code
install      Install all project dependencies
lint         Run all linters
setup-hooks  Install git hooks
test         Run all tests
test-backend Run backend tests only
test-cli     Run CLI tests only
```

---

## Troubleshooting

### mise Issues

**Problem**: `mise: command not found`

**Solution**:
```bash
# Reinstall mise
curl https://mise.run | sh

# Activate in shell
echo 'eval "$(~/.local/bin/mise activate zsh)"' >> ~/.zshrc
source ~/.zshrc
```

**Problem**: Wrong tool versions

**Solution**:
```bash
# Reinstall tools
mise install --force

# Verify versions
mise current
```

---

### Tilt Issues

**Problem**: `tilt: command not found`

**Solution**:
```bash
# Install via mise
mise install

# Or install manually
brew install tilt  # macOS
```

**Problem**: Services won't start

**Solution**:
```bash
# Check Tilt logs
tilt logs

# Restart Tilt
tilt down
tilt up

# Check Docker is running
docker info
```

**Problem**: Port conflicts

**Solution**:
```bash
# Stop Tilt
tilt down

# Check what's using ports
lsof -i :3000
lsof -i :8000
lsof -i :10350

# Kill conflicting processes
kill -9 <PID>

# Restart Tilt
tilt up
```

---

### Git Hooks Issues

**Problem**: Pre-commit hooks fail

**Solution**:
```bash
# Update hooks
pre-commit autoupdate

# Clean and reinstall
pre-commit clean
pre-commit install

# Run manually to debug
pre-commit run --all-files --verbose
```

**Problem**: Hooks are slow

**Solution**:
```bash
# Skip expensive checks in pre-commit
SKIP=mypy,bandit,pytest-check git commit -m "message"

# Or temporarily disable
git commit --no-verify -m "message"
```

**Problem**: Post-commit hook doesn't run

**Solution**:
```bash
# Verify hook is installed
ls -la .git/hooks/post-commit

# Reinstall
ln -sf ../../.githooks/post-commit .git/hooks/post-commit
chmod +x .git/hooks/post-commit
```

---

### Test Issues

**Problem**: Tests fail  locally but pass in CI

**Solution**:
```bash
# Clean test cache
rm -rf .pytest_cache

# Use same Python version as CI
mise install python@3.11

# Run with same flags as CI
pytest --maxfail=1 --tb=short
```

**Problem**: Database errors in tests

**Solution**:
```bash
# Create test database directory
mkdir -p data

# Clean test database
rm -f *.db

# Restart tests
pytest tests/
```

---

### Performance Issues

**Problem**: Slow live reload

**Solution**:
```bash
# Check Tilt resource usage
tilt logs

# Reduce watched files
# Edit Tiltfile to exclude unnecessary directories

# Restart Tilt
tilt down && tilt up
```

**Problem**: High CPU usage

**Solution**:
```bash
# Check Docker stats
docker stats

# Limit container resources
# Add to docker-compose.override.yml
```

---

## Best Practices

**Development Workflow:**
1. Start with `mise run dev` (Tilt)
2. Make code changes
3. Verify in Tilt UI (auto-reload)
4. Commit changes (pre-commit runs automatically)
5. Verify post-commit check output
6. Push to remote

**Before Committing:**
- Run `mise run format` to auto-format code
- Run `mise run lint` to check for issues
- Run `mise run test` to verify tests pass
- Let pre-commit hooks catch remaining issues

**Quality Standards:**
- All code must pass ruff linting
- All code must be formatted with ruff format
- Type hints required for public APIs
- Tests required for new features
- Security scanning must pass

**Git Hooks:**
- Pre-commit: Fast checks, auto-fixes when possible
- Post-commit: Verifies commit will pass CI/CD
- Never bypass hooks except emergencies
- Amend commit if post-commit warnings appear

**Debugging:**
- Use Tilt UI logs instead of `docker logs`
- Check `mise tasks` for available helpers
- Run quality checks manually before committing
- Test locally before pushing to CI/CD

---

## Additional Resources

**Documentation:**
- mise: https://mise.jdx.dev
- Tilt: https://docs.tilt.dev
- pre-commit: https://pre-commit.com
- ruff: https://docs.astral.sh/ruff

**Project Documentation:**
- [README.md](../README.md) - Project overview
- [Architecture](../architecture.md) - System design
- [API Reference](api-reference.md) - API documentation
- [Troubleshooting](troubleshooting.md) - Common issues

**Quality Tools:**
- [Ruff Documentation](https://docs.astral.sh/ruff/)
- [MyPy Documentation](https://mypy.readthedocs.io/)
- [Pytest Documentation](https://docs.pytest.org/)
- [Bandit Documentation](https://bandit.readthedocs.io/)
