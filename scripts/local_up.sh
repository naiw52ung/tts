#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"
RUN_DIR="$ROOT_DIR/.run"
mkdir -p "$RUN_DIR"

if lsof -nP -iTCP:8000 -sTCP:LISTEN >/dev/null 2>&1; then
  echo "Port 8000 is already in use. Please stop the existing process first."
  echo "You can inspect it with: lsof -nP -iTCP:8000 -sTCP:LISTEN"
  exit 1
fi

if lsof -nP -iTCP:5173 -sTCP:LISTEN >/dev/null 2>&1; then
  echo "Port 5173 is already in use. Please stop the existing process first."
  echo "You can inspect it with: lsof -nP -iTCP:5173 -sTCP:LISTEN"
  exit 1
fi

echo "[1/5] Preparing backend virtualenv"
cd "$BACKEND_DIR"
if [[ ! -d ".venv" ]]; then
  python3 -m venv .venv
fi
source .venv/bin/activate
if [[ "${SKIP_PIP_INSTALL:-0}" == "1" ]]; then
  echo "Skipping pip install (SKIP_PIP_INSTALL=1)"
else
  pip install --default-timeout 120 --retries 5 -r requirements.txt >/dev/null
fi

echo "[2/5] Starting backend (SQLite + Celery eager)"
export SECRET_KEY="legendai-local-dev-secret"
export DATABASE_URL="sqlite:///$ROOT_DIR/backend/legendai_local.db"
export REDIS_URL="memory://"
export CELERY_TASK_ALWAYS_EAGER="true"
export CELERY_TASK_EAGER_PROPAGATES="true"
export STORAGE_ROOT="$ROOT_DIR/backend/local_storage"
export ADMIN_API_KEY="${ADMIN_API_KEY:-legendai-local-admin-key}"
mkdir -p "$STORAGE_ROOT"

nohup .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 > "$RUN_DIR/backend.log" 2>&1 &
echo $! > "$RUN_DIR/backend.pid"

echo "[3/5] Backend started, waiting for readiness"
for _ in {1..20}; do
  if curl -fsS "http://localhost:8000/health" >/dev/null 2>&1; then
    echo "Backend is ready."
    break
  fi
  sleep 1
done

if ! curl -fsS "http://localhost:8000/health" >/dev/null 2>&1; then
  echo "Backend failed to become ready. Check $RUN_DIR/backend.log"
  exit 1
fi

echo "[4/5] Preparing frontend dependencies"
cd "$FRONTEND_DIR"
npm install >/dev/null

echo "[5/5] Starting frontend"
nohup npm run dev > "$RUN_DIR/frontend.log" 2>&1 &
echo $! > "$RUN_DIR/frontend.pid"

echo ""
echo "Local stack started:"
echo "  Frontend: http://localhost:5173"
echo "  API docs: http://localhost:8000/docs"
echo "Logs:"
echo "  $RUN_DIR/backend.log"
echo "  $RUN_DIR/frontend.log"
echo "Stop with: ./scripts/local_down.sh"
