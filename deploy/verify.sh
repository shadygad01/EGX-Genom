#!/usr/bin/env bash
# Self-contained proof that the VPS migration is complete and correct --
# run this anytime, independent of a deploy, to get real evidence instead
# of a guess. Answers exactly three questions: is the server running the
# same commit as GitHub's main, are all the services actually up, and do
# the live (not just static) features actually work end to end.
#
# Usage: bash deploy/verify.sh
# Exit code is non-zero if anything failed (safe to wire into monitoring).
set -uo pipefail  # deliberately not -e: run every check, report all failures, don't stop at the first

REPO_DIR="/opt/egx-genom"
PASS=0
FAIL=0

check() {
  local desc="$1"; shift
  if "$@" >/dev/null 2>&1; then
    echo "PASS: $desc"
    PASS=$((PASS + 1))
  else
    echo "FAIL: $desc"
    FAIL=$((FAIL + 1))
  fi
}

echo "== EGX-Genom VPS deployment verification =="
echo "Run at: $(date -u +'%Y-%m-%dT%H:%M:%SZ')"
echo

cd "$REPO_DIR" || { echo "FAIL: repo not found at $REPO_DIR"; exit 1; }

echo "-- Version (is this the latest code, or something stale?) --"
git fetch origin main --quiet
LOCAL_SHA=$(git rev-parse HEAD)
REMOTE_SHA=$(git rev-parse origin/main)
echo "Server is running: $LOCAL_SHA"
echo "GitHub main is at:  $REMOTE_SHA"
check "server is running the latest commit on main" [ "$LOCAL_SHA" = "$REMOTE_SHA" ]
echo

echo "-- Systemd services --"
for unit in egx-api.service egx-collector.timer egx-deploy.timer nginx; do
  check "$unit is active" systemctl is-active --quiet "$unit"
done
echo

echo "-- Last auto-deploy run --"
systemctl show egx-deploy.service -p ActiveEnterTimestamp -p Result --no-pager 2>/dev/null || echo "egx-deploy.service not installed"
echo

echo "-- API health --"
check "API answers directly on :3001/health" curl -fsS -m 5 http://127.0.0.1:3001/health -o /dev/null
check "API answers through nginx /api/health" curl -fsS -m 5 http://127.0.0.1/api/health -o /dev/null
echo

echo "-- Dashboard site (through nginx, at the real /EGX-Genom/ path) --"
CODE=$(curl -fsS -m 5 -o /dev/null -w "%{http_code}" http://127.0.0.1/EGX-Genom/ 2>/dev/null || echo "000")
echo "HTTP $CODE"
check "dashboard responds 200 at /EGX-Genom/" [ "$CODE" = "200" ]
echo

echo "-- Live decision route (proves the live-backed build is served, not the static one) --"
DECIDE_CODE=$(curl -fsS -m 30 -o /tmp/egx_verify_decide.json -w "%{http_code}" -X POST http://127.0.0.1/api/decisions \
  -H 'Content-Type: application/json' -d "{\"date\":\"$(date +%F)\"}" 2>/dev/null || echo "000")
echo "HTTP $DECIDE_CODE"
if [ "$DECIDE_CODE" = "501" ]; then
  echo "  -> 501 means DECISION_DATA_DIR isn't pointed at real 'agx run' output yet -- see deploy/README.md step 2."
elif [ "$DECIDE_CODE" = "000" ]; then
  echo "  -> no response at all -- nginx/api routing is broken, not just unconfigured."
fi
check "live /decisions route is configured and reachable (not 501/000)" \
  bash -c "[ '$DECIDE_CODE' != '501' ] && [ '$DECIDE_CODE' != '000' ]"
echo

echo "-- Data freshness --"
if [ -f web/public/data/system_status.json ]; then
  GEN_AT=$(python3 -c "import json; print(json.load(open('web/public/data/system_status.json')).get('generated_at', 'unknown'))" 2>/dev/null || echo "unreadable")
  echo "system_status.json generated_at: $GEN_AT"
else
  echo "system_status.json not found yet -- egx-collector.service hasn't produced a dashboard export."
fi
echo

echo "=============================="
echo "RESULT: $PASS passed, $FAIL failed"
echo "=============================="
[ "$FAIL" -eq 0 ]
