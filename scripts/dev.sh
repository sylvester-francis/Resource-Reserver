#!/usr/bin/env bash
# One-command quick start for Resource-Reserver
# Run this to go from zero to running in one command!

set -e

echo ""
echo "╔═══════════════════════════════════════════════════╗"
echo "║  Resource-Reserver - One-Command Quick Start     ║"
echo "╚═══════════════════════════════════════════════════╝"
echo ""

# Check for mise
if ! command -v mise > /dev/null 2>&1; then
    echo "⚠️  mise not found. Installing mise..."
    curl https://mise.run | sh
    export PATH="$HOME/.local/bin:$PATH"
    echo "✅ mise installed!"
    echo ""
fi

# Ensure mise is activated
if [ -z "$MISE_SHELL" ]; then
    eval "$(mise activate bash)"
fi

# Install tools if needed
if [ ! -f ".mise-installed" ]; then
    echo "📦 Installing tools (Bun, Python, Moon)..."
    mise install
    touch .mise-installed
    echo "✅ Tools installed!"
    echo ""
fi

# Check if dependencies need installation
if [ ! -d "apps/frontend/node_modules" ]; then
    echo "📦 Installing project dependencies..."
    mise run setup
    echo ""
fi

# Start development environment
echo "🚀 Starting development environment..."
echo ""
echo "   Tilt UI: http://localhost:10350"
echo "   Backend: http://localhost:8000"
echo "   Frontend: http://localhost:3000"
echo ""

mise run dev
