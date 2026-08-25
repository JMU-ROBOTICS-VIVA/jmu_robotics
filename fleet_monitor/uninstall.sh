#!/usr/bin/env bash
# Remove fleet-monitor services and installed program files.
# By default, preserve the rosrpt user, configuration, private state, and web data.

set -euo pipefail

if [ "$EUID" -ne 0 ]; then
    echo "Run this uninstall script with sudo:"
    echo "  sudo ./fleet_monitor/uninstall.sh"
    exit 1
fi

systemctl disable --now jmu-tb4-publish.path 2>/dev/null || true
systemctl disable --now jmu-tb4-fleet.service 2>/dev/null || true
systemctl stop jmu-tb4-publish.service 2>/dev/null || true

rm -f /etc/systemd/system/jmu-tb4-fleet.service
rm -f /etc/systemd/system/jmu-tb4-publish.service
rm -f /etc/systemd/system/jmu-tb4-publish.path
systemctl daemon-reload

rm -rf /opt/jmu/fleet-monitor

echo
echo "Fleet monitor services removed."
echo "Preserved:"
echo "  user:        rosrpt"
echo "  config:      /etc/jmu_tb4/fleet-monitor.conf"
echo "  state:       /var/lib/rosrpt"
echo "  web content: /var/www/html/turtlebot"
