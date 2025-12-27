#!/usr/bin/env bash
# Setup script for Resource-Reserver development environment
# Fully automated - just run this script and everything works!

set -e

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${ROOT_DIR}"

echo "=========================================="
echo "Resource-Reserver Development Setup"
echo "Starting automated setup..."
echo "=========================================="
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

# Detect shell
detect_shell() {
    if [ -n "$ZSH_VERSION" ]; then
        echo "zsh"
    elif [ -n "$BASH_VERSION" ]; then
        echo "bash"
    else
        echo "bash"  # Default to bash
    fi
}

SHELL_TYPE=$(detect_shell)
SHELL_RC="$HOME/.${SHELL_TYPE}rc"

# Check if mise is installed
if ! command -v mise &> /dev/null; then
    echo -e "${YELLOW}mise not found - installing automatically...${NC}"
    curl -sSf https://mise.run | sh

    # Add mise to shell
    if ! grep -q "mise activate" "$SHELL_RC" 2>/dev/null; then
        {
            echo ""
            echo '# mise - tool version manager'
            # shellcheck disable=SC2016
            echo 'eval "$(~/.local/bin/mise activate '"$SHELL_TYPE"')"'
        } >> "$SHELL_RC"
        echo -e "${GREEN}Added mise to $SHELL_RC${NC}"
    fi

    # Activate mise for this session
    export PATH="$HOME/.local/bin:$PATH"
    eval "$(~/.local/bin/mise activate "$SHELL_TYPE")"

    echo -e "${GREEN}✓ mise installed successfully${NC}"
else
    echo -e "${GREEN}✓ mise is already installed${NC}"
fi

# Check if Docker is running, try to start if not
check_docker() {
    if ! docker info &> /dev/null; then
        echo -e "${YELLOW}Docker not running - attempting to start...${NC}"

        # Try to start Docker Desktop on macOS
        if [[ "$OSTYPE" == "darwin"* ]]; then
            if [ -d "/Applications/Docker.app" ]; then
                open -a Docker
                echo "Waiting for Docker to start..."

                # Wait up to 30 seconds for Docker to start
                for _ in {1..30}; do
                    if docker info &> /dev/null; then
                        echo -e "${GREEN}✓ Docker started successfully${NC}"
                        return 0
                    fi
                    sleep 1
                done

                echo -e "${RED}Docker failed to start automatically${NC}"
                echo "Please start Docker Desktop manually and run this script again"
                exit 1
            else
                echo -e "${RED}Docker Desktop not found${NC}"
                echo "Install Docker Desktop: https://www.docker.com/products/docker-desktop"
                exit 1
            fi
        else
            echo -e "${RED}Please start Docker and run this script again${NC}"
            exit 1
        fi
    else
        echo -e "${GREEN}✓ Docker is running${NC}"
    fi
}

check_docker

# Install tools via mise
echo ""
echo "Installing development tools (Python 3.11, Node 24, Tilt)..."
mise install
echo -e "${GREEN}✓ Tools installed${NC}"
echo "  - Python $(python --version 2>&1 | cut -d' ' -f2)"
echo "  - Node $(node --version)"
echo "  - Tilt $(tilt version 2>&1 | head -n1 || echo 'latest')"

# Install Python dependencies
echo ""
echo "Installing Python dependencies..."
pip install -q -r apps/backend/requirements.txt
pip install -q pre-commit
echo -e "${GREEN}✓ Python dependencies installed${NC}"

# Install frontend dependencies
echo ""
echo "Installing frontend dependencies..."
pushd apps/frontend > /dev/null
bun install
popd > /dev/null
echo -e "${GREEN}✓ Frontend dependencies installed${NC}"

# Install pre-commit hooks
echo ""
echo "Installing git hooks..."
pre-commit install
pre-commit install --hook-type post-commit

# Configure post-commit hook
if [ -f ".githooks/post-commit" ]; then
    mkdir -p .git/hooks
    ln -sf ../../.githooks/post-commit .git/hooks/post-commit
    chmod +x .git/hooks/post-commit
fi

echo -e "${GREEN}✓ Git hooks installed${NC}"

# Create data directory
echo ""
echo "Creating data directories..."
mkdir -p data/db data/csv
chmod 755 data data/db data/csv
echo -e "${GREEN}✓ Data directories created${NC}"

# Build Docker images (in background to save time)
echo ""
echo "Building Docker images (this may take a few minutes)..."
docker compose build --quiet &
BUILD_PID=$!

echo ""
echo "=========================================="
echo -e "${GREEN}Setup complete!${NC}"
echo "=========================================="
echo ""
echo -e "${BLUE}Quick Start Commands:${NC}"
echo ""
echo "  Start development:    ${GREEN}make dev${NC}   (or: tilt up)"
echo "  Run tests:            ${GREEN}make test${NC}"
echo "  Format code:          ${GREEN}make format${NC}"
echo "  Stop services:        ${GREEN}make stop${NC}"
echo "  View all commands:    ${GREEN}make help${NC}"
echo ""
echo -e "${BLUE}Access Points:${NC}"
echo "  Tilt UI:      http://localhost:10350"
echo "  Backend API:  http://localhost:8000"
echo "  Frontend Web: http://localhost:3000"
echo ""
echo -e "${BLUE}Git Hooks Active:${NC}"
echo "  Pre-commit:  Quality checks before each commit"
echo "  Post-commit: Verifies commit will pass CI/CD"
echo ""
echo "Waiting for Docker images to build..."
wait $BUILD_PID
echo -e "${GREEN}✓ Docker images ready${NC}"
echo ""
echo -e "${GREEN}All done! Run '${BLUE}make dev${GREEN}' to start coding${NC}"
echo ""
