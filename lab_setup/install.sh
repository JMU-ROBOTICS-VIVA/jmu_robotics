#!/usr/bin/env bash
# Install JMU CS354 TurtleBot infrastructure on a lab machine.
# Run as a normal administrative user: ./lab_setup/install.sh
# Do NOT run the whole script with sudo; it requests sudo where needed.

set -euo pipefail

INSTALL_ROOT="/opt/jmu/cs354"
ROS_INSTALL="${INSTALL_ROOT}/ros"
BIN_INSTALL="${INSTALL_ROOT}/bin"
SHELL_INSTALL="${INSTALL_ROOT}/tb4_setup.bash"
CONFIG_INSTALL="${INSTALL_ROOT}/tb4_setup.conf"
GITHUB_LOGIN_INSTALL="${BIN_INSTALL}/jmu-github-login"
FASTDDS_INSTALL="${INSTALL_ROOT}/fastdds/localhost-128.xml"

BASHRC="/etc/bash.bashrc"

HOOK_BEGIN="# >>> JMU CS354 TurtleBot environment >>>"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
ROS_SOURCE="${REPO_ROOT}/ros"
ROS_REPOS="${ROS_SOURCE}/course_packages.repos"
TB4_SETUP_SOURCE="${SCRIPT_DIR}/tb4_setup.bash"
TB4_CONFIG_SOURCE="${SCRIPT_DIR}/tb4_setup.conf"
GITHUB_LOGIN_SOURCE="${SCRIPT_DIR}/jmu-github-login.sh"
FASTDDS_SOURCE="${SCRIPT_DIR}/fastdds/localhost-128.xml"

# jmu install runs as root, so, we remove this for now
#if [ "$EUID" -eq 0 ]; then
#    echo
#    echo "Do NOT run this script with sudo."
#    echo "Run it as your normal administrative account:"
#    echo
#    echo "    ./lab_setup/install.sh"
#    echo
#    exit 1
#fi

if [ ! -r /opt/ros/jazzy/setup.bash ]; then
    echo "ERROR: ROS 2 Jazzy was not found under /opt/ros/jazzy."
    exit 1
fi

if [ ! -d "$ROS_SOURCE" ]; then
    echo "ERROR: ROS source directory not found:"
    echo "       $ROS_SOURCE"
    exit 1
fi

if [ ! -r "$TB4_SETUP_SOURCE" ]; then
    echo "ERROR: TurtleBot setup script not found:"
    echo "       $TB4_SETUP_SOURCE"
    exit 1
fi

if [ ! -r "$GITHUB_LOGIN_SOURCE" ]; then
    echo "ERROR: GitHub login script script not found:"
    echo "       $GITHUB_LOGIN_SOURCE"
    exit 1
fi

if [ ! -r "$TB4_CONFIG_SOURCE" ]; then
    echo "ERROR: TurtleBot site configuration not found:"
    echo "       $TB4_CONFIG_SOURCE"
    exit 1
fi

if [ ! -r "$FASTDDS_SOURCE" ]; then
    echo "ERROR: Fast DDS simulator profile not found:"
    echo "       $FASTDDS_SOURCE"
    exit 1
fi

if ! command -v colcon >/dev/null 2>&1; then
    echo "ERROR: colcon was not found."
    exit 1
fi

if ! command -v vcs >/dev/null 2>&1; then
    echo "ERROR: vcs was not found."
    echo "Install it with:"
    echo
    echo "    sudo apt install python3-vcstool"
    exit 1
fi

echo
echo "============================================================"
echo " Installing JMU CS354 TurtleBot infrastructure"
echo "============================================================"
echo
echo "Repository:"
echo "    $REPO_ROOT"
echo
echo "ROS installation:"
echo "    $ROS_INSTALL"
echo
echo "Shell setup:"
echo "    $SHELL_INSTALL"
echo
echo "Site configuration:"
echo "    $CONFIG_INSTALL"
echo
echo "Fast DDS simulator profile:"
echo "    $FASTDDS_INSTALL"
echo

sudo -v

# ROS setup scripts are not guaranteed to be compatible with Bash nounset
# mode. Keep nounset enabled for this installer, but disable it while
# sourcing the third-party ROS environment.
set +u
source /opt/ros/jazzy/setup.bash
set -u

WORK_DIR="$(mktemp -d /tmp/jmu-cs354-build.XXXXXX)"
cleanup()
{
    rm -rf "$WORK_DIR"
}
trap cleanup EXIT

EXTERNAL_ROS_SOURCE="${WORK_DIR}/external_src"
mkdir -p "$EXTERNAL_ROS_SOURCE"

echo "Fetching external ROS packages..."

vcs import "$EXTERNAL_ROS_SOURCE" < "$ROS_REPOS"

# This prefix is dedicated to this course infrastructure, so rebuild it
# from scratch to avoid stale files after renames/deletions.
sudo rm -rf "$ROS_INSTALL"
sudo install -d -o "$(id -un)" -g "$(id -gn)" -m 0755 "$ROS_INSTALL"

echo "Building JMU ROS packages..."

colcon \
    --log-base "$WORK_DIR/log" \
    build \
    --base-paths "$ROS_SOURCE" "${EXTERNAL_ROS_SOURCE}" \
    --build-base "$WORK_DIR/build" \
    --install-base "$ROS_INSTALL"

# Students may read the infrastructure but may not modify it.
sudo chown -R root:root "$ROS_INSTALL"
sudo chmod -R go-w "$ROS_INSTALL"

sudo install \
    -D \
    -o root \
    -g root \
    -m 0644 \
    "$TB4_SETUP_SOURCE" \
    "$SHELL_INSTALL"

sudo install \
    -D \
    -o root \
    -g root \
    -m 0644 \
    "$TB4_CONFIG_SOURCE" \
    "$CONFIG_INSTALL"

sudo install \
    -D \
    -o root \
    -g root \
    -m 0644 \
    "$FASTDDS_SOURCE" \
    "$FASTDDS_INSTALL"

sudo install \
    -D \
    -o root \
    -g root \
    -m 0755 \
    "$GITHUB_LOGIN_SOURCE" \
    "$GITHUB_LOGIN_INSTALL"

# Preserve the original file once, then add an idempotent hook.
if [ ! -e "${BASHRC}.pre-jmu-cs354" ]; then
    sudo cp -a "$BASHRC" "${BASHRC}.pre-jmu-cs354"
fi

if ! grep -Fq "$HOOK_BEGIN" "$BASHRC"; then
    sudo tee -a "$BASHRC" >/dev/null <<'BASHRC_EOF'
# >>> JMU CS354 TurtleBot environment >>>
if [ -r /opt/jmu/cs354/tb4_setup.bash ]; then
    source /opt/jmu/cs354/tb4_setup.bash
fi
# <<< JMU CS354 TurtleBot environment <<<
BASHRC_EOF
else
    echo "JMU TurtleBot Bash hook is already present in $BASHRC."
fi

echo
echo "============================================================"
echo " JMU CS354 TurtleBot installation complete"
echo "============================================================"
echo
echo "Installed ROS infrastructure:"
echo "    $ROS_INSTALL"
echo
echo "Installed shell configuration:"
echo "    $SHELL_INSTALL"
echo
echo "Installed site configuration:"
echo "    $CONFIG_INSTALL"
echo
echo "Installed Fast DDS simulator profile:"
echo "    $FASTDDS_INSTALL"
echo
echo "Installed GitHub login command:"
echo "    $GITHUB_LOGIN_INSTALL"
echo
echo "Open a NEW terminal to test the installation."
echo
