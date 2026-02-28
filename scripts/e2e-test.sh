#!/usr/bin/env bash
set -euo pipefail

API="http://localhost:8000"

# wait for backend
echo "Waiting for backend..."
for i in $(seq 1 60); do
    curl -sf "$API/health" > /dev/null 2>&1 && break
    [ "$i" -eq 60 ] && { echo "Backend never came up"; exit 1; }
    sleep 1
done

# health
echo "Checking health..."
curl -sf "$API/health" | python3 -c "
import sys, json
h = json.load(sys.stdin)
assert h['checks']['database']['status'] == 'up', 'DB not up'
print('  DB: up')
print('  LLM:', h['checks']['llm']['status'])
"

# seed data
echo "Checking seed data..."
TOTAL=$(curl -sf "$API/analytics" | python3 -c "import sys,json; print(json.load(sys.stdin)['total_traces'])")
echo "  Found $TOTAL traces"
[ "$TOTAL" -ge 25 ] || { echo "Expected >= 25 seed traces, got $TOTAL"; exit 1; }

# create a trace, check analytics increment
echo "Creating test trace..."
TID=$(curl -sf -X POST "$API/traces" \
  -H "Content-Type: application/json" \
  -d '{"user_message":"e2e test","bot_response":"ok","response_time_ms":100,"categories":["Billing","Refund"]}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
echo "  Created trace $TID"

NEW_TOTAL=$(curl -sf "$API/analytics" | python3 -c "import sys,json; print(json.load(sys.stdin)['total_traces'])")
[ "$NEW_TOTAL" -eq $((TOTAL + 1)) ] || { echo "Total didn't increment: $TOTAL -> $NEW_TOTAL"; exit 1; }
echo "  Analytics: $TOTAL -> $NEW_TOTAL"

# category filtering
echo "Checking category filters..."
curl -sf "$API/traces?category=Billing" | python3 -c "
import sys, json
traces = json.load(sys.stdin)
assert all('Billing' in t['categories'] for t in traces), 'Non-Billing trace in Billing filter'
assert any(t['id'] == $TID for t in traces), 'New trace missing from Billing results'
print('  Billing filter: ok')
"

curl -sf "$API/traces?category=Cancellation" | python3 -c "
import sys, json
traces = json.load(sys.stdin)
assert not any(t['id'] == $TID for t in traces), 'Test trace wrongly in Cancellation'
print('  Cancellation exclusion: ok')
"

# frontend reachable
echo "Checking frontend..."
curl -sf -o /dev/null http://localhost:80
echo "  Frontend: ok"

echo ""
echo "All checks passed!"
