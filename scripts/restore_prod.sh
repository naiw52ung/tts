#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <backup_dir>"
  echo "Example: $0 ./backups/20260424_120000"
  exit 1
fi

BACKUP_DIR="$1"

if [[ ! -f ".env.prod" ]]; then
  echo ".env.prod not found. Create it from .env.prod.example first."
  exit 1
fi
if [[ ! -f "$BACKUP_DIR/postgres.sql" ]]; then
  echo "Missing file: $BACKUP_DIR/postgres.sql"
  exit 1
fi
if [[ ! -f "$BACKUP_DIR/storage.tar.gz" ]]; then
  echo "Missing file: $BACKUP_DIR/storage.tar.gz"
  exit 1
fi

set -a
source .env.prod
set +a

POSTGRES_USER="${POSTGRES_USER:-legendai}"
POSTGRES_DB="${POSTGRES_DB:-legendai}"

echo "[1/4] Ensure stack is up"
docker compose --env-file .env.prod -f docker-compose.prod.yml up -d postgres api worker >/dev/null

echo "[2/4] Restore postgres schema and data"
docker compose --env-file .env.prod -f docker-compose.prod.yml exec -T postgres \
  psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
docker compose --env-file .env.prod -f docker-compose.prod.yml exec -T postgres \
  psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" < "$BACKUP_DIR/postgres.sql"

echo "[3/4] Restore storage files"
docker compose --env-file .env.prod -f docker-compose.prod.yml exec -T api \
  sh -lc 'mkdir -p /data/storage && rm -rf /data/storage/*'
cat "$BACKUP_DIR/storage.tar.gz" | docker compose --env-file .env.prod -f docker-compose.prod.yml exec -T api \
  sh -lc 'tar -xzf - -C /data'

echo "[4/4] Restart app services"
docker compose --env-file .env.prod -f docker-compose.prod.yml restart api worker nginx >/dev/null
echo "Restore completed from: $BACKUP_DIR"
