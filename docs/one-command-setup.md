# One-Command Developer Experience

## Super User-Friendly Setup

### The Ultimate One-Command Experience

```bash
./dev
```

That's it! Everything else is automatic.

## What Happens Automatically

1. Checks if mise is installed (installs if needed)
1. Auto-detects your shell (bash/zsh) and configures it
1. Installs Python 3.11, Node 24, and Tilt
1. Checks if Docker is running (starts it if needed on macOS)
1. Installs all Python and Node dependencies
1. Configures git hooks (pre-commit and post-commit)
1. Builds Docker images in background
1. Starts Tilt development environment
1. Opens Tilt UI at http://localhost:10350

## Simple Commands (via Makefile)

```bash
make help      # View all commands
make setup     # One-time setup (if ./dev doesn't exist)
make dev       # Start development
make stop      # Stop all services
make test      # Run tests
make lint      # Run linters
make format    # Auto-format code
make logs      # View logs
make clean     # Clean caches
```

## No Manual Steps Required

Everything is automated:

- No need to manually install Python/Node
- No need to manually start Docker
- No need to manually install dependencies
- No need to manually configure git hooks
- No need to manually build Docker images

## First-Time Setup

```bash
git clone https://github.com/sylvester-francis/Resource-Reserver.git
cd Resource-Reserver
./dev
```

## Subsequent Runs

```bash
cd Resource-Reserver
make dev
# or
./dev
```

## Access Points

After running `./dev` or `make dev`:

- Tilt Dashboard: http://localhost:10350
- Frontend Web: http://localhost:3000
- Backend API: http://localhost:8000
- API Documentation: http://localhost:8000/docs

## Features

### Auto-Restart on Code Changes

- Edit Python files → Backend reloads in < 1 second
- Edit JavaScript/EJS files → Frontend reloads in < 1 second

### Quality Checks

- Pre-commit hook runs before each commit
- Post-commit hook verifies CI will pass
- All checks run automatically

### Visual Dashboard

- Tilt UI shows all services
- Color-coded health status
- Unified logs
- Manual quality check buttons

## Platform Support

- macOS: Full automation including Docker auto-start
- Linux: Full automation (requires Docker to be running)
- Windows: Manual Docker start required

## Troubleshooting

### Docker not starting on macOS

```bash
# Install Docker Desktop if not installed
brew install --cask docker

# Then run again
./dev
```

### Need to reset

```bash
rm .setup-complete
./dev  # Will run full setup again
```

### Prefer traditional approach

```bash
docker compose up -d  # Still works!
```

## Why This is Better

**Before (traditional):**

1. Install Python 3.11 manually
1. Install Node 24 manually
1. Create virtual environment
1. Install pip dependencies
1. Install npm dependencies
1. Start Docker Desktop
1. Build images
1. Start backend in terminal 1
1. Start frontend in terminal 2
1. Configure git hooks
1. Hope everything works

**After (one command):**

1. `./dev`
1. Start coding!

## Summary

This is the simplest possible developer experience:

- Clone repository
- Run `./dev`
- Everything else happens automatically
- No manual steps
- No configuration required
- Just works
