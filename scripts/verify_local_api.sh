#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP_DIR="$ROOT_DIR/.run/verify"
mkdir -p "$TMP_DIR/MonItems"

cat > "$TMP_DIR/MonItems/Test.txt" <<'EOF'
1/100 金币
1/500 祝福油
EOF

(
  cd "$TMP_DIR"
  zip -qr demo.zip MonItems
)

EMAIL="test_$(date +%s)@example.com"
PASSWORD="Passw0rd!"

REGISTER_JSON="$(curl -fsS -X POST "http://localhost:8000/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}")"
TOKEN="$(python3 -c 'import json,sys; print(json.loads(sys.argv[1])["access_token"])' "$REGISTER_JSON")"

TASK_JSON="$(curl -fsS -X POST "http://localhost:8000/api/v1/tasks" \
  -H "Authorization: Bearer $TOKEN" \
  -F "engine=GOM" \
  -F "version_type=复古" \
  -F "req_doc_text=将全部怪物爆率提升20%" \
  -F "version_file=@$TMP_DIR/demo.zip")"

TASK_ID="$(python3 -c 'import json,sys; print(json.loads(sys.argv[1])["id"])' "$TASK_JSON")"
echo "Created task: $TASK_ID"

for _ in {1..20}; do
  STATUS_JSON="$(curl -fsS -H "Authorization: Bearer $TOKEN" "http://localhost:8000/api/v1/tasks/$TASK_ID")"
  STATUS="$(python3 -c 'import json,sys; print(json.loads(sys.argv[1])["status"])' "$STATUS_JSON")"
  PROGRESS="$(python3 -c 'import json,sys; print(json.loads(sys.argv[1])["progress"])' "$STATUS_JSON")"
  echo "Task status: $STATUS ($PROGRESS%)"
  if [[ "$STATUS" == "success" ]]; then
    break
  fi
  if [[ "$STATUS" == "failed" ]]; then
    echo "Task failed"
    exit 1
  fi
  sleep 1
done

curl -fsS -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/tasks/$TASK_ID/download" \
  -o "$TMP_DIR/output.zip"

echo "Download OK: $TMP_DIR/output.zip"
echo "Local API verification passed."
