#!/usr/bin/env bash
# Install the JMU TurtleBot fleet monitor on the dedicated monitoring/web host.
#
# Run as a normal administrative user:
#   ./fleet_monitor/install.sh
#
# Do not invoke the whole script with sudo. It uses sudo for system changes.

set -euo pipefail

SERVICE_USER="rosrpt"
SERVICE_HOME="/var/lib/rosrpt"
INSTALL_DIR="/opt/jmu/fleet-monitor"
CONFIG_DIR="/etc/jmu_tb4"
CONFIG_FILE="$CONFIG_DIR/fleet-monitor.conf"

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"

CONFIG_SOURCE="$SCRIPT_DIR/fleet-monitor.conf"
RUNNER_SOURCE="$SCRIPT_DIR/run_fleet_status.sh"
PUBLISH_SOURCE="$SCRIPT_DIR/publish_status.sh"
FLEET_SERVICE_SOURCE="$SCRIPT_DIR/jmu-tb4-fleet.service"
PUBLISH_SERVICE_SOURCE="$SCRIPT_DIR/jmu-tb4-publish.service"
PUBLISH_PATH_SOURCE="$SCRIPT_DIR/jmu-tb4-publish.path"
WEB_SOURCE="$REPO_ROOT/ros/jmu_tb4_fleet/web/index.html"

if [ "$EUID" -eq 0 ]; then
    echo
    echo "Do NOT run the whole installer with sudo."
    echo "Run:"
    echo "  ./fleet_monitor/install.sh"
    echo
    exit 1
fi

for required in \
    /opt/ros/jazzy/setup.bash \
    /opt/jmu/cs354/ros/local_setup.bash \
    "$CONFIG_SOURCE" \
    "$RUNNER_SOURCE" \
    "$PUBLISH_SOURCE" \
    "$FLEET_SERVICE_SOURCE" \
    "$PUBLISH_SERVICE_SOURCE" \
    "$PUBLISH_PATH_SOURCE" \
    "$WEB_SOURCE"
do
    if [ ! -r "$required" ]; then
        echo "ERROR: Required file not found/readable:"
        echo "  $required"
        exit 1
    fi
done

# Confirm that the normal JMU ROS installation contains the monitor package.
set +u
source /opt/ros/jazzy/setup.bash
source /opt/jmu/cs354/ros/local_setup.bash
set -u

if ! ros2 pkg prefix jmu_tb4_fleet >/dev/null 2>&1; then
    echo
    echo "ERROR: jmu_tb4_fleet is not installed."
    echo "Run the normal repository installer first:"
    echo
    echo "  ./lab_setup/install.sh"
    echo
    exit 1
fi

sudo -v

echo
echo "Configuring dedicated service account: $SERVICE_USER"

if getent passwd "$SERVICE_USER" >/dev/null; then
    echo "  User already exists; preserving it."
else
    sudo useradd \
        --system \
        --user-group \
        --create-home \
        --home-dir "$SERVICE_HOME" \
        --shell /usr/sbin/nologin \
        --comment "JMU TurtleBot ROS fleet monitor" \
        "$SERVICE_USER"
    echo "  Created system user $SERVICE_USER."
fi

if ! getent group "$SERVICE_USER" >/dev/null; then
    echo
    echo "ERROR: User $SERVICE_USER exists but group $SERVICE_USER does not."
    echo "Refusing to alter an existing account automatically."
    echo "Please have the administrator review that account."
    exit 1
fi

# Ensure the expected private state directory exists and belongs to rosrpt.
sudo install -d \
    -o "$SERVICE_USER" \
    -g "$SERVICE_USER" \
    -m 0750 \
    "$SERVICE_HOME"

sudo install -d -o root -g root -m 0755 "$INSTALL_DIR"
sudo install -d -o root -g root -m 0755 "$CONFIG_DIR"

# Preserve machine-specific configuration on reinstall.
if sudo test -e "$CONFIG_FILE"; then
    echo "Preserving existing configuration:"
    echo "  $CONFIG_FILE"
else
    sudo install -o root -g root -m 0644 "$CONFIG_SOURCE" "$CONFIG_FILE"
    echo "Created configuration:"
    echo "  $CONFIG_FILE"
fi

sudo install -o root -g root -m 0755 \
    "$RUNNER_SOURCE" "$INSTALL_DIR/run_fleet_status.sh"

sudo install -o root -g root -m 0755 \
    "$PUBLISH_SOURCE" "$INSTALL_DIR/publish_status.sh"

sudo install -o root -g root -m 0644 \
    "$FLEET_SERVICE_SOURCE" /etc/systemd/system/jmu-tb4-fleet.service

sudo install -o root -g root -m 0644 \
    "$PUBLISH_SERVICE_SOURCE" /etc/systemd/system/jmu-tb4-publish.service

sudo install -o root -g root -m 0644 \
    "$PUBLISH_PATH_SOURCE" /etc/systemd/system/jmu-tb4-publish.path

# Read WEB_ROOT from the active configuration.
# shellcheck source=/dev/null
source <(sudo cat "$CONFIG_FILE")

echo
echo "Installing dashboard into:"
echo "  $WEB_ROOT"

# Keep the web tree root-owned. The ROS service cannot write here.
sudo install -d -o root -g root -m 0755 "$WEB_ROOT"
sudo install -o root -g root -m 0644 "$WEB_SOURCE" "$WEB_ROOT/index.html"

sudo systemctl daemon-reload
sudo systemctl enable --now jmu-tb4-fleet.service
sudo systemctl enable --now jmu-tb4-publish.path

# If the collector has already written a snapshot before the path watcher
# became active, publish it once now.
if sudo test -s "$STATUS_FILE"; then
    sudo systemctl start jmu-tb4-publish.service
fi

echo
echo "============================================================"
echo " JMU TurtleBot fleet monitor installation complete"
echo "============================================================"
echo
echo "Dedicated account:"
getent passwd "$SERVICE_USER" | cut -d: -f1,6,7
echo
echo "Collector:"
echo "  systemctl status jmu-tb4-fleet.service"
echo
echo "Path watcher:"
echo "  systemctl status jmu-tb4-publish.path"
echo
echo "Publication runs:"
echo "  journalctl -u jmu-tb4-publish.service"
echo
echo "Private status:"
echo "  $STATUS_FILE"
echo
echo "Dashboard:"
echo "  $WEB_ROOT/index.html"
echo "  $WEB_STATUS_FILE"
echo
echo "Local URL:"
echo "  http://localhost/turtlebot/"
