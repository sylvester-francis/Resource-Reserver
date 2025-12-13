# Tiltfile - Development workflow for Resource-Reserver
# Documentation: https://docs.tilt.dev/

# Load Docker Compose configuration
docker_compose('docker-compose.yml')

# Configure Docker Compose resources with labels and dependencies
dc_resource('backend', labels=['api'])
dc_resource('frontend', labels=['web'], resource_deps=['backend'])

# Custom resources for better organization
local_resource(
    'lint-backend',
    cmd='ruff check app/ cli/ --output-format=github',
    labels=['quality'],
    auto_init=False,
    trigger_mode=TRIGGER_MODE_MANUAL
)

local_resource(
    'test-backend',
    cmd='pytest tests/ --maxfail=1 --tb=short',
    labels=['testing'],
    auto_init=False,
    trigger_mode=TRIGGER_MODE_MANUAL,
    resource_deps=['backend']
)

local_resource(
    'format-code',
    cmd='black . && ruff check --fix .',
    labels=['quality'],
    auto_init=False,
    trigger_mode=TRIGGER_MODE_MANUAL
)

# Watch additional files for changes
watch_file('requirements.txt')
watch_file('frontend/package.json')
watch_file('.env')

# Print helpful information on startup
print("""
========================================
Resource-Reserver Development Environment
========================================

Services:
  - Backend API:  http://localhost:8000
  - Frontend Web: http://localhost:3000
  - API Docs:     http://localhost:8000/docs
  - Tilt UI:      http://localhost:10350

Manual Tasks (click in Tilt UI):
  - lint-backend: Run ruff on Python code
  - test-backend: Run pytest test suite
  - format-code:  Format all code with black/ruff

Live Reload:
  - Backend: Edit files in app/ or cli/
  - Frontend: Edit files in frontend/

Press space or visit http://localhost:10350 to open Tilt UI
Press Ctrl+C to stop all services
========================================
""")
