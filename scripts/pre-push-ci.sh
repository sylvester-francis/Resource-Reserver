#!/usr/bin/env bash
# Pre-push CI checks for backend and frontend.
set -euo pipefail

if [[ "${SKIP_PRE_PUSH_CI:-}" =~ ^(1|true|yes)$ ]]; then
  echo "Skipping pre-push checks (SKIP_PRE_PUSH_CI set)."
  exit 0
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="${ROOT_DIR}/apps/backend"
FRONTEND_DIR="${ROOT_DIR}/apps/frontend"

backend_pid=""
frontend_pid=""
docker_started="false"

cleanup() {
  if [[ "${frontend_pid}" != "" ]]; then
    kill "${frontend_pid}" 2>/dev/null || true
  fi
  if [[ "${backend_pid}" != "" ]]; then
    kill "${backend_pid}" 2>/dev/null || true
  fi
  if [[ "${docker_started}" == "true" ]]; then
    docker compose down >/dev/null 2>&1 || true
  fi
}

trap cleanup EXIT

wait_for_url() {
  local url="$1"
  local retries="${2:-30}"
  local delay="${3:-1}"

  for _ in $(seq 1 "${retries}"); do
    if curl -fsS "${url}" >/dev/null 2>&1; then
      return 0
    fi
    sleep "${delay}"
  done

  echo "Timed out waiting for ${url}" >&2
  return 1
}

cd "${ROOT_DIR}"

# shellcheck disable=SC1091
if [[ -f "venv/bin/activate" ]]; then
  source venv/bin/activate
fi

echo "==> Running Python lint and format checks"
cd "${BACKEND_DIR}"
ruff check . --output-format=github
ruff format . --check

echo "==> Running Python tests"
pytest --cov=app --cov=cli --cov-report=term-missing -v

echo "==> Running frontend lint, build, and unit tests"
cd "${FRONTEND_DIR}"
npm run lint
npm run build
npm run test
cd "${ROOT_DIR}"

echo "==> Running Docker build and smoke tests"
docker compose build backend frontend
docker compose up -d backend frontend
docker_started="true"
wait_for_url "http://localhost:8000/health" 30 1
wait_for_url "http://localhost:3000/login" 30 1
docker compose exec -T backend mkdir -p /tmp/.reservation-cli
docker compose exec -T backend python -m cli.main auth --help
docker compose down
docker_started="false"

echo "==> Running Playwright E2E tests"
DATABASE_URL="${DATABASE_URL:-sqlite:///./data/db/resource_reserver_dev.db}" \
REDIS_URL="${REDIS_URL:-redis://localhost:6379/0}" \
SECRET_KEY="${SECRET_KEY:-test-secret-key}" \
ALGORITHM="${ALGORITHM:-HS256}" \
uvicorn --app-dir "${BACKEND_DIR}" app.main:app --host 0.0.0.0 --port 8000 &
backend_pid=$!
wait_for_url "http://localhost:8000/health" 30 1

cd "${FRONTEND_DIR}"
NEXT_PUBLIC_API_URL="${NEXT_PUBLIC_API_URL:-http://localhost:8000}" \
PLAYWRIGHT_BASE_URL="${PLAYWRIGHT_BASE_URL:-http://localhost:3000}" \
CI="" \
npm run test:e2e
