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
FASTDDS_INSTALL="${INSTALL_ROOT}/fastdds/localhost-128.xml"
GITHUB_LOGIN_INSTALL="${BIN_INSTALL}/jmu-github-login.sh"
DIAGNOSTIC_INSTALL="${BIN_INSTALL}/ros_tb4_diagnostics.sh"
CLEANUP_INSTALL="${BIN_INSTALL}/ros_tb4_cleanup.sh"
BASHRC="/etc/bash.bashrc"
HOOK_BEGIN="# >>> JMU CS354 TurtleBot environment >>>"

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
ROS_SOURCE="${REPO_ROOT}/ros"
COURSE_REPOS="${REPO_ROOT}/ros/course_packages.repos"
TB4_SETUP_SOURCE="${SCRIPT_DIR}/tb4_setup.bash"
TB4_CONFIG_SOURCE="${SCRIPT_DIR}/tb4_setup.conf"
FASTDDS_SOURCE="${SCRIPT_DIR}/fastdds/localhost-128.xml"
GITHUB_LOGIN_SOURCE="${SCRIPT_DIR}/jmu-github-login.sh"
DIAGNOSTIC_SOURCE="${SCRIPT_DIR}/ros_tb4_diagnostics.sh"
CLEANUP_SOURCE="${SCRIPT_DIR}/ros_tb4_cleanup.sh"

## JMU install runs as root

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

if [ ! -r "$COURSE_REPOS" ]; then
    echo "ERROR: Course package repository list not found:"
    echo "       $COURSE_REPOS"
    exit 1
fi

if [ ! -r "$TB4_SETUP_SOURCE" ]; then
    echo "ERROR: TurtleBot setup script not found:"
    echo "       $TB4_SETUP_SOURCE"
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

if [ ! -r "$GITHUB_LOGIN_SOURCE" ]; then
    echo "ERROR: GitHub login helper not found:"
    echo "       $GITHUB_LOGIN_SOURCE"
    exit 1
fi

if [ ! -r "$DIAGNOSTIC_SOURCE" ]; then
    echo "ERROR: TurtleBot diagnostics script not found:"
    echo "       $DIAGNOSTIC_SOURCE"
    exit 1
fi

if [ ! -r "$CLEANUP_SOURCE" ]; then
    echo "ERROR: TurtleBot cleanup script not found:"
    echo "       $CLEANUP_SOURCE"
    exit 1
fi

if ! command -v colcon >/dev/null 2>&1; then
    echo "ERROR: colcon was not found."
    exit 1
fi

if ! command -v vcs >/dev/null 2>&1; then
    echo "ERROR: vcs was not found."
    echo "Install python3-vcstool before running this installer."
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
echo "Command installation:"
echo "    $BIN_INSTALL"
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
echo "Course package repository list:"
echo "    $COURSE_REPOS"
echo

sudo -v

# ROS setup scripts are not guaranteed to be compatible with Bash nounset
# mode. Keep nounset enabled for this installer, but disable it while
# sourcing the third-party ROS environment.
set +u
source /opt/ros/jazzy/setup.bash
set -u

WORK_DIR="$(mktemp -d /tmp/jmu-cs354-build.XXXXXX)"
COURSE_SOURCE="${WORK_DIR}/course_packages"
cleanup()
{
    rm -rf "$WORK_DIR"
}
trap cleanup EXIT

mkdir -p "$COURSE_SOURCE"

echo "Importing course ROS packages..."
vcs import "$COURSE_SOURCE" < "$COURSE_REPOS"
echo

# This prefix is dedicated to this course infrastructure, so rebuild it
# from scratch to avoid stale files after renames/deletions.
sudo rm -rf "$ROS_INSTALL"
sudo install -d -o "$(id -un)" -g "$(id -gn)" -m 0755 "$ROS_INSTALL"

echo "Building JMU and course ROS packages..."

colcon \
    --log-base "$WORK_DIR/log" \
    build \
    --base-paths "$ROS_SOURCE" "$COURSE_SOURCE" \
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

# Install student/admin helper commands. These are executable and live in
# /opt/jmu/cs354/bin, which tb4_setup.bash adds to PATH.
sudo install \
    -D \
    -o root \
    -g root \
    -m 0755 \
    "$GITHUB_LOGIN_SOURCE" \
    "$GITHUB_LOGIN_INSTALL"

sudo install \
    -D \
    -o root \
    -g root \
    -m 0755 \
    "$DIAGNOSTIC_SOURCE" \
    "$DIAGNOSTIC_INSTALL"

sudo install \
    -D \
    -o root \
    -g root \
    -m 0755 \
    "$CLEANUP_SOURCE" \
    "$CLEANUP_INSTALL"

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
echo "Installed helper commands:"
echo "    $GITHUB_LOGIN_INSTALL"
echo "    $DIAGNOSTIC_INSTALL"
echo "    $CLEANUP_INSTALL"
echo
echo "Open a NEW terminal to test the installation."
echo
