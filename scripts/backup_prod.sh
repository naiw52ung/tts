#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ ! -f ".env.prod" ]]; then
  echo ".env.prod not found. Create it from .env.prod.example first."
  exit 1
fi

set -a
source .env.prod
set +a

POSTGRES_USER="${POSTGRES_USER:-legendai}"
POSTGRES_DB="${POSTGRES_DB:-legendai}"
BACKUP_ROOT="${BACKUP_ROOT:-$ROOT_DIR/backups}"
KEEP_DAYS="${BACKUP_KEEP_DAYS:-7}"
TS="$(date +%Y%m%d_%H%M%S)"
TARGET_DIR="$BACKUP_ROOT/$TS"

mkdir -p "$TARGET_DIR"

echo "[1/4] Ensure stack is up"
docker compose --env-file .env.prod -f docker-compose.prod.yml up -d postgres api >/dev/null

echo "[2/4] Backup postgres"
docker compose --env-file .env.prod -f docker-compose.prod.yml exec -T postgres \
  pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" > "$TARGET_DIR/postgres.sql"

echo "[3/4] Backup storage volume"
docker compose --env-file .env.prod -f docker-compose.prod.yml exec -T api \
  sh -lc 'tar -czf - -C /data storage' > "$TARGET_DIR/storage.tar.gz"

echo "[4/4] Write metadata and cleanup old backups"
cat > "$TARGET_DIR/metadata.txt" <<EOF
timestamp=$TS
postgres_db=$POSTGRES_DB
postgres_user=$POSTGRES_USER
project_dir=$ROOT_DIR
EOF

find "$BACKUP_ROOT" -mindepth 1 -maxdepth 1 -type d -mtime +"$KEEP_DAYS" -exec rm -rf {} +

echo "Backup completed: $TARGET_DIR"
