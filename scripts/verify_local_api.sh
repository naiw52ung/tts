#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP_DIR="$ROOT_DIR/.run/verify"
mkdir -p "$TMP_DIR/MonItems"
ADMIN_KEY="${ADMIN_API_KEY:-legendai-local-admin-key}"

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

ME_JSON="$(curl -fsS -H "Authorization: Bearer $TOKEN" "http://localhost:8000/api/v1/users/me")"
BALANCE_BEFORE="$(python3 -c 'import json,sys; print(json.loads(sys.argv[1])["balance"])' "$ME_JSON")"
echo "Initial balance: $BALANCE_BEFORE"

TEMPLATES_JSON="$(curl -fsS -H "Authorization: Bearer $TOKEN" "http://localhost:8000/api/v1/tasks/templates")"
TEMPLATE_ID="$(python3 -c 'import json,sys; x=json.loads(sys.argv[1]); print(x[0]["id"] if x else "")' "$TEMPLATES_JSON")"
if [[ -z "$TEMPLATE_ID" ]]; then
  echo "No template data found"
  exit 1
fi

DRY_RUN_JSON="$(curl -fsS -X POST "http://localhost:8000/api/v1/tasks/dry-run" \
  -H "Authorization: Bearer $TOKEN" \
  -F "engine=GOM" \
  -F "version_type=复古" \
  -F "template_id=$TEMPLATE_ID" \
  -F "version_file=@$TMP_DIR/demo.zip")"
DRY_RUN_CHANGES="$(python3 -c 'import json,sys; print(json.loads(sys.argv[1])["change_count"])' "$DRY_RUN_JSON")"
echo "Dry-run changes: $DRY_RUN_CHANGES"

ORDER_JSON="$(curl -fsS -X POST "http://localhost:8000/api/v1/payments/orders" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"amount":30,"channel":"mock","remark":"local_verify"}')"
ORDER_NO="$(python3 -c 'import json,sys; print(json.loads(sys.argv[1])["order_no"])' "$ORDER_JSON")"
echo "Created order: $ORDER_NO"

curl -fsS -X POST "http://localhost:8000/api/v1/payments/orders/$ORDER_NO/mock-paid" \
  -H "X-Admin-Key: $ADMIN_KEY" >/dev/null
echo "Mock payment callback: OK"

TASK_JSON="$(curl -fsS -X POST "http://localhost:8000/api/v1/tasks" \
  -H "Authorization: Bearer $TOKEN" \
  -F "engine=GOM" \
  -F "version_type=复古" \
  -F "template_id=$TEMPLATE_ID" \
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

ME_AFTER_JSON="$(curl -fsS -H "Authorization: Bearer $TOKEN" "http://localhost:8000/api/v1/users/me")"
BALANCE_AFTER="$(python3 -c 'import json,sys; print(json.loads(sys.argv[1])["balance"])' "$ME_AFTER_JSON")"
LEDGER_COUNT="$(python3 -c 'import json,sys; print(len(json.loads(sys.argv[1]).get("recent_ledger", [])))' "$ME_AFTER_JSON")"
echo "Balance after payment+task: $BALANCE_AFTER"
echo "Recent ledger count: $LEDGER_COUNT"

echo "Download OK: $TMP_DIR/output.zip"
echo "Local API verification passed."
