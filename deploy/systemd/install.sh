#!/usr/bin/env bash
set -euo pipefail

echo "=========================================="
echo "EGX-Genom Production Collector Installer"
echo "=========================================="

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "[1/6] Copying systemd unit files to /etc/systemd/system/..."
cp -f "${SCRIPT_DIR}/egx-collector.service" /etc/systemd/system/egx-collector.service
cp -f "${SCRIPT_DIR}/egx-collector.timer" /etc/systemd/system/egx-collector.timer

chmod 644 /etc/systemd/system/egx-collector.service /etc/systemd/system/egx-collector.timer
chown root:root /etc/systemd/system/egx-collector.service /etc/systemd/system/egx-collector.timer

echo "[2/6] Reloading systemd daemon cache..."
systemctl daemon-reload

echo "[3/6] Verifying systemd unit syntax..."
systemd-analyze verify /etc/systemd/system/egx-collector.service /etc/systemd/system/egx-collector.timer

echo "[4/6] Starting egx-collector.service manually to verify execution..."
systemctl start egx-collector.service
systemctl status egx-collector.service --no-pager

echo "[5/6] Enabling and starting egx-collector.timer..."
systemctl enable egx-collector.timer
systemctl start egx-collector.timer

echo "[6/6] Verifying active timer status..."
systemctl list-timers egx-collector.timer --no-pager

echo "=========================================="
echo "EGX-Genom Collector Installed & Running!"
echo "=========================================="
