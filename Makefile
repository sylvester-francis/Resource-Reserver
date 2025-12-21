# Makefile for Resource-Reserver
# Provides simple one-command developer experience with Bun, Moon, and Mise

.PHONY: help setup dev stop test lint format clean install-hooks docker logs build

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
	@echo "  make build    - Build frontend for production"
	@echo "  make logs     - View service logs"
	@echo ""
	@echo "Maintenance:"
	@echo "  make clean    - Clean caches and temp files"
	@echo "  make docker   - Use Docker Compose instead of Tilt"
	@echo ""
	@echo "Tools: mise (Bun, Python, Moon) | Tilt | Docker"
	@echo ""

# Complete automated setup - ONE command to rule them all
setup:
	@echo "=========================================="
	@echo "Resource-Reserver Automated Setup"
	@echo "=========================================="
	@echo ""
	@echo "📦 Installing tools with mise..."
	@mise install
	@echo ""
	@echo "📦 Installing dependencies..."
	@mise run setup
	@echo ""
	@echo "✅ Setup complete! Run 'make dev' to start."

# Start development environment with Tilt
dev:
	@echo "Starting development environment..."
	@echo "Tilt UI: http://localhost:10350"
	@echo "Backend: http://localhost:8000"
	@echo "Frontend: http://localhost:3000"
	@echo ""
	@mise run dev

# Stop all services
stop:
	@echo "Stopping all services..."
	@mise run down 2>/dev/null || docker compose down

# Run all tests
test:
	@mise run test

# Run linters
lint:
	@mise run lint

# Auto-format code
format:
	@mise run format

# Build for production
build:
	@mise run build

# Install git hooks
install-hooks:
	@mise run setup-hooks

# Use Docker Compose (alternative to Tilt)
docker:
	@echo "Starting services with Docker Compose..."
	@mise run docker
	@echo "Services started!"
	@echo "Backend: http://localhost:8000"
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
	@mise run clean

# Frontend-only development
frontend:
	@mise run frontend-dev

# Backend-only development
backend:
	@mise run backend-dev

# Run Moon tasks
moon-%:
	@moon run $*
