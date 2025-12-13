# Makefile for Resource-Reserver
# Provides simple one-command developer experience

.PHONY: help setup dev stop test lint format clean install-hooks docker logs

# Default target - show help
help:
	@echo "Resource-Reserver - One-Command Developer Experience"
	@echo ""
	@echo "Quick Start:"
	@echo "  make setup    - Complete automated setup (run once)"
	@echo "  make dev      - Start development environment"
	@echo "  make stop     - Stop all services"
	@echo ""
	@echo "Development Commands:"
	@echo "  make test     - Run all tests"
	@echo "  make lint     - Run linters"
	@echo "  make format   - Auto-format code"
	@echo "  make logs     - View service logs"
	@echo ""
	@echo "Maintenance:"
	@echo "  make clean    - Clean caches and temp files"
	@echo "  make docker   - Use Docker Compose instead of Tilt"
	@echo ""

# Complete automated setup - ONE command to rule them all
setup:
	@echo "=========================================="
	@echo "Resource-Reserver Automated Setup"
	@echo "=========================================="
	@./scripts/setup-dev.sh

# Start development environment with Tilt
dev:
	@echo "Starting development environment with Tilt..."
	@echo "Tilt UI will open at http://localhost:10350"
	@echo "Backend API: http://localhost:8000"
	@echo "Frontend: http://localhost:3000"
	@echo ""
	@if command -v mise > /dev/null 2>&1; then \
		mise run dev; \
	else \
		tilt up; \
	fi

# Stop all services
stop:
	@echo "Stopping all services..."
	@tilt down 2>/dev/null || docker compose down

# Run all tests
test:
	@if command -v mise > /dev/null 2>&1; then \
		mise run test; \
	else \
		pytest tests/; \
	fi

# Run linters
lint:
	@if command -v mise > /dev/null 2>&1; then \
		mise run lint; \
	else \
		ruff check . && echo "Linting passed!"; \
	fi

# Auto-format code
format:
	@if command -v mise > /dev/null 2>&1; then \
		mise run format; \
	else \
		black . && ruff check --fix .; \
	fi

# Install git hooks
install-hooks:
	@if command -v mise > /dev/null 2>&1; then \
		mise run setup-hooks; \
	else \
		pip install pre-commit && pre-commit install && pre-commit install --hook-type post-commit; \
	fi

# Use Docker Compose (alternative to Tilt)
docker:
	@echo "Starting services with Docker Compose..."
	@docker compose up -d
	@echo "Services started!"
	@echo "Backend API: http://localhost:8000"
	@echo "Frontend: http://localhost:3000"

# View logs
logs:
	@if docker compose ps | grep -q "Up"; then \
		docker compose logs -f; \
	else \
		echo "No services running. Start with 'make dev' or 'make docker'"; \
	fi

# Clean caches and temporary files
clean:
	@echo "Cleaning caches and temporary files..."
	@rm -rf __pycache__ .pytest_cache .ruff_cache .mypy_cache .tox
	@rm -rf node_modules/.cache
	@rm -rf .tiltbuild
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo "Clean complete!"
