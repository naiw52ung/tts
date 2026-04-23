#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ ! -f ".env.prod" ]]; then
  echo ".env.prod not found. Create it from .env.prod.example first."
  exit 1
fi

echo "[1/3] Building and starting production stack"
docker compose --env-file .env.prod -f docker-compose.prod.yml up -d --build

echo "[2/3] Services status"
docker compose --env-file .env.prod -f docker-compose.prod.yml ps

echo "[3/3] Quick health check"
sleep 2
curl -fsS http://127.0.0.1/api/health >/dev/null 2>&1 || true
echo "Deployment command finished. Check logs if needed:"
echo "docker compose --env-file .env.prod -f docker-compose.prod.yml logs -f api"
