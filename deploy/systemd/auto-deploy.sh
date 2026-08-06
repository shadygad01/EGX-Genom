#!/usr/bin/env bash
# Pull-based auto-deploy: checks GitHub for new commits on main and, only if
# something actually changed, rebuilds and reinstalls. Run periodically by
# egx-deploy.timer (see egx-deploy.service). No SSH, no GitHub secrets, no
# credentials of any kind -- this repo is public, so `git fetch` needs no
# authentication, same as `egx-collector.service` needs none to fetch prices.
# Same "fail loudly" posture as the rest of deploy/: `set -e` means a failed
# build or a failed verification check leaves the unit in `failed` state,
# visible to `systemctl status egx-deploy.service` / `journalctl -u egx-deploy`,
# rather than silently leaving a half-updated site running.
set -euo pipefail

REPO_DIR="/opt/egx-genom"
cd "$REPO_DIR"

git fetch origin main
LOCAL_SHA=$(git rev-parse HEAD)
REMOTE_SHA=$(git rev-parse origin/main)

if [ "$LOCAL_SHA" = "$REMOTE_SHA" ]; then
  echo "Already up to date at $LOCAL_SHA. Nothing to deploy."
  exit 0
fi

echo "New commit(s) on main: $LOCAL_SHA -> $REMOTE_SHA. Deploying..."

# Only affects tracked files -- egx-collector.service's own runtime output
# under research/data/ (knowledge.json, events.json, shadow_fund.json, the
# dashboard export dir, etc.) is untracked and is never touched by this.
git reset --hard origin/main

cd research && uv sync --frozen && cd ..
npm ci
npm run build -w api
npm run build -w web -- --mode selfhosted

bash deploy/systemd/install.sh

echo "--- Verifying the deployment actually works ---"
systemctl is-active egx-api.service
systemctl is-active nginx
echo "API health (direct):"
curl -fsS http://127.0.0.1:3001/health
echo
echo "API health (through nginx /api/):"
curl -fsS http://127.0.0.1/api/health
echo
echo "Dashboard site (through nginx /EGX-Genom/):"
code=$(curl -fsS -o /dev/null -w "%{http_code}" http://127.0.0.1/EGX-Genom/)
echo "HTTP $code"
[ "$code" = "200" ]

echo "DEPLOY OK: now running $REMOTE_SHA"
