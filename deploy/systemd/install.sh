#!/usr/bin/env bash
set -euo pipefail

echo "=========================================="
echo "EGX-Genom Production Installer (api + collector)"
echo "=========================================="

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "[1/8] Copying systemd unit files to /etc/systemd/system/..."
cp -f "${SCRIPT_DIR}/egx-api.service" /etc/systemd/system/egx-api.service
cp -f "${SCRIPT_DIR}/egx-collector.service" /etc/systemd/system/egx-collector.service
cp -f "${SCRIPT_DIR}/egx-collector.timer" /etc/systemd/system/egx-collector.timer

chmod 644 /etc/systemd/system/egx-api.service /etc/systemd/system/egx-collector.service /etc/systemd/system/egx-collector.timer
chown root:root /etc/systemd/system/egx-api.service /etc/systemd/system/egx-collector.service /etc/systemd/system/egx-collector.timer

echo "[2/8] Reloading systemd daemon cache..."
systemctl daemon-reload

echo "[3/8] Verifying systemd unit syntax..."
systemd-analyze verify /etc/systemd/system/egx-api.service /etc/systemd/system/egx-collector.service /etc/systemd/system/egx-collector.timer

echo "[4/8] Enabling and starting egx-api.service..."
systemctl enable egx-api.service
systemctl restart egx-api.service
systemctl status egx-api.service --no-pager

echo "[5/8] Starting egx-collector.service manually to verify execution..."
systemctl start egx-collector.service
systemctl status egx-collector.service --no-pager

echo "[6/8] Enabling and starting egx-collector.timer..."
systemctl enable egx-collector.timer
systemctl start egx-collector.timer

echo "[7/8] Verifying active timer status..."
systemctl list-timers egx-collector.timer --no-pager

echo "[8/8] Quick health check against the API..."
curl -fsS http://127.0.0.1:3001/health && echo || echo "WARNING: egx-api.service did not answer on :3001/health"

echo "=========================================="
echo "EGX-Genom API + Collector Installed & Running!"
echo "=========================================="
