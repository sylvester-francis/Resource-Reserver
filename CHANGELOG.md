# Changelog

All notable changes to Resource-Reserver will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.1] - 2025-12-13

### Fixed

- **Safari Login Issue**: Fixed authentication cookie handling for Safari browser on macOS Sequoia (15.x) with Apple Silicon (M1/M2/M3/M4) chips

  - Added `sameSite: 'Lax'` attribute to both `auth_token` and `username` cookies in `frontend/server.js`
  - Safari requires explicit `sameSite` attribute for cookies, especially on localhost
  - Chromium-based browsers (Chrome, Brave, Edge) worked without this attribute but it's best practice to include it
  - Issue reported when using Podman for Apple Silicon but applies to all container runtimes
  - Affects macOS Sequoia 15.5+ with Safari 18+
  - **Files changed**: `frontend/server.js` (lines 118-126)
  - **Verification**: Clear Safari cookies (Settings > Privacy > Manage Website Data) and restart browser after update

- **Frontend Register Route**: Fixed `/register` route error by redirecting to `/login` page (which contains both login and register forms)

### Added - Developer Experience

- **One-Command Setup**: New `./dev` script provides truly automated setup and start

  - Auto-installs mise if missing
  - Auto-detects and configures shell (bash/zsh)
  - Auto-starts Docker on macOS
  - Installs all dependencies automatically
  - Zero manual configuration required

- **mise Integration**: Tool version manager for consistent development environments

  - Automatic installation of Python 3.11, Node 24, and Tilt
  - Environment variable management via `.mise.toml`
  - Task shortcuts: `mise run dev`, `mise run test`, `mise run format`, etc.

- **Tilt Integration**: Modern development workflow with live reload

  - Docker Compose integration via `Tiltfile`
  - Live reload for backend and frontend (< 1 second)
  - Visual dashboard at http://localhost:10350
  - Unified logging for all services
  - Manual quality check tasks (lint, test, format)

- **Makefile**: Simple command interface for all development tasks

  - `make dev` - Start development environment
  - `make test` - Run all tests
  - `make format` - Auto-format code
  - `make lint` - Run linters
  - `make help` - View all commands

- **Git Hooks**: Comprehensive pre-commit and post-commit automation

  - Pre-commit: 40+ quality checks (ruff, mypy, bandit, safety, hadolint, yamllint, shellcheck, mdformat)
  - Post-commit: CI/CD verification on changed files
  - Auto-fixes formatting issues
  - Ensures commits always pass CI/CD

- **Enhanced Setup Script**: Fully automated `scripts/setup-dev.sh`

  - Shell auto-detection and configuration
  - Docker auto-start capability (macOS)
  - Silent/fast installation
  - Progress indicators

### Documentation

- Added comprehensive troubleshooting guide for Safari cookie issues in `docs/troubleshooting.md`
- Added `docs/development.md` - Complete developer guide (500+ lines)
- Added `docs/one-command-setup.md` - One-command experience documentation
- Updated README.md with modern development setup as primary option
- Removed all emojis from documentation for professional tone
- All documentation now credits Sylvester Francis

## [2.0.0] - Current

### Added

- Complete frontend rewrite using Express.js + Alpine.js
- Production Docker containers on GitHub Container Registry
- Enhanced CLI with Rich terminal output
- Zero build process for direct development and deployment
- Server-side rendering with client-side reactivity
- Better performance and user experience

### Changed

- Replaced Vite/TypeScript frontend with Express.js/EJS for simplicity
- Improved Docker compose configuration with dev/prod separation
- Enhanced health check endpoints with detailed status
- Auto-reset functionality for unavailable resources
- Background cleanup task for expired reservations

### Technical

- FastAPI backend with timezone-aware datetime handling
- SQLAlchemy ORM with SQLite (dev) and PostgreSQL (prod) support
- JWT authentication with cookie-based sessions
- Comprehensive test suite with 95%+ coverage
- CI/CD pipeline with GitHub Actions

## [1.0.0] - Foundation

### Added

- Core reservation and resource management system
- TypeScript frontend with Vite build system
- FastAPI backend with comprehensive REST API
- Typer-based CLI for automation and administration
- Complete test suite and documentation
- Docker containerization
- User authentication with JWT
- Conflict detection for reservations
- CSV import/export for bulk operations
- Audit trail with reservation history

______________________________________________________________________

## Version Numbering

- **MAJOR**: Incompatible API changes or major architectural changes
- **MINOR**: New features, backwards-compatible
- **PATCH**: Bug fixes, backwards-compatible

## Upgrade Guide

### From 2.0.0 to 2.0.1

No breaking changes. Simply pull the latest code and restart services:

```bash
git pull origin main
docker-compose down
docker-compose up -d
```

If you experience Safari login issues:

1. Restart the frontend service: `docker-compose restart frontend`
1. Clear Safari cookies: Safari > Settings > Privacy > Manage Website Data
1. Remove all localhost entries
1. Restart Safari and log in again

### From 1.0.0 to 2.0.0

**Breaking Changes:**

- Frontend has been completely rewritten
- Build process eliminated (no more Vite compilation)
- Environment variables may need updating

**Migration Steps:**

1. Backup your data directory
1. Update docker-compose.yml to latest version
1. Pull new images or rebuild containers
1. Your database will be preserved (SQLite file or PostgreSQL data)
1. No data migration required - schema is compatible

______________________________________________________________________

## Reporting Issues

If you encounter any problems:

1. Check the [Troubleshooting Guide](docs/troubleshooting.md)
1. Search existing [GitHub Issues](https://github.com/sylvester-francis/Resource-Reserver/issues)
1. Open a new issue with:
   - Your platform (OS, browser, Docker version)
   - Steps to reproduce
   - Expected vs actual behavior
   - Relevant logs

## Contributing

See our contribution guidelines for information on how to contribute bug fixes and features.
