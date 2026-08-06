#!/usr/bin/env bash
set -euo pipefail

echo "=========================================="
echo "EGX-Genom Production Installer (api + collector + auto-deploy)"
echo "=========================================="

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "[1/9] Copying systemd unit files to /etc/systemd/system/..."
cp -f "${SCRIPT_DIR}/egx-api.service" /etc/systemd/system/egx-api.service
cp -f "${SCRIPT_DIR}/egx-collector.service" /etc/systemd/system/egx-collector.service
cp -f "${SCRIPT_DIR}/egx-collector.timer" /etc/systemd/system/egx-collector.timer
cp -f "${SCRIPT_DIR}/egx-deploy.service" /etc/systemd/system/egx-deploy.service
cp -f "${SCRIPT_DIR}/egx-deploy.timer" /etc/systemd/system/egx-deploy.timer

chmod 644 /etc/systemd/system/egx-{api,collector,deploy}.service /etc/systemd/system/egx-{collector,deploy}.timer
chown root:root /etc/systemd/system/egx-{api,collector,deploy}.service /etc/systemd/system/egx-{collector,deploy}.timer

echo "[2/9] Reloading systemd daemon cache..."
systemctl daemon-reload

echo "[3/9] Verifying systemd unit syntax..."
systemd-analyze verify \
  /etc/systemd/system/egx-api.service \
  /etc/systemd/system/egx-collector.service /etc/systemd/system/egx-collector.timer \
  /etc/systemd/system/egx-deploy.service /etc/systemd/system/egx-deploy.timer

echo "[4/9] Enabling and starting egx-api.service..."
systemctl enable egx-api.service
systemctl restart egx-api.service
systemctl status egx-api.service --no-pager

echo "[5/9] Starting egx-collector.service manually to verify execution..."
systemctl start egx-collector.service
systemctl status egx-collector.service --no-pager

echo "[6/9] Enabling and starting egx-collector.timer..."
systemctl enable egx-collector.timer
systemctl start egx-collector.timer

# Safe to (re)start the *timer* even when this installer is itself being
# invoked FROM a running egx-deploy.service instance (see auto-deploy.sh)
# -- `systemctl start` on a Timer unit only (re)computes its next elapse
# time, it does not touch the still-running egx-deploy.service that
# called this script. Never call `systemctl start/restart
# egx-deploy.service` here, though -- that unit is this exact script's
# own caller on an automated run, and restarting it mid-run would kill
# the deploy in progress.
echo "[7/9] Enabling and (re)starting egx-deploy.timer (auto-deploy on every new commit to main)..."
systemctl enable egx-deploy.timer
systemctl start egx-deploy.timer

echo "[8/9] Verifying active timer status..."
systemctl list-timers egx-collector.timer egx-deploy.timer --no-pager

echo "[9/9] Quick health check against the API..."
curl -fsS http://127.0.0.1:3001/health && echo || echo "WARNING: egx-api.service did not answer on :3001/health"

echo "=========================================="
echo "EGX-Genom API + Collector + Auto-Deploy Installed & Running!"
echo "=========================================="
