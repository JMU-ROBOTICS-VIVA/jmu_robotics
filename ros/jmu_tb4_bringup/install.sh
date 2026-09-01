#!/usr/bin/env bash
set -euo pipefail

PACKAGE="jmu_tb4_bringup"
ROS_DISTRO="${ROS_DISTRO:-jazzy}"
DESTINATION="/opt/jmu/turtlebot4/ros"

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/../.." && pwd)"
WORKSPACE="${REPO_ROOT}/ros"

if [[ "${EUID}" -eq 0 ]]; then
    echo "ERROR: Run this script as the normal user, not with sudo." >&2
    echo "       The script uses sudo only for installation into ${DESTINATION}." >&2
    exit 1
fi

ROS_SETUP="/opt/ros/${ROS_DISTRO}/setup.bash"

if [[ ! -f "${ROS_SETUP}" ]]; then
    echo "ERROR: ROS setup file not found: ${ROS_SETUP}" >&2
    exit 1
fi

if [[ ! -d "${WORKSPACE}" ]]; then
    echo "ERROR: ROS workspace not found: ${WORKSPACE}" >&2
    exit 1
fi

# shellcheck disable=SC1090
source "${ROS_SETUP}"

cd "${WORKSPACE}"

if ! colcon list 2>/dev/null | awk '{print $1}' | grep -qx "${PACKAGE}"; then
    echo "ERROR: colcon cannot find package '${PACKAGE}' under ${WORKSPACE}." >&2
    exit 1
fi

BUILD_ROOT="$(mktemp -d "/tmp/${PACKAGE}.XXXXXX")"
trap 'rm -rf "${BUILD_ROOT}"' EXIT

echo "Building ${PACKAGE}"
echo "Workspace:   ${WORKSPACE}"
echo "Destination: ${DESTINATION}"
echo

colcon --log-base "${BUILD_ROOT}/log" build     --merge-install     --build-base "${BUILD_ROOT}/build"     --install-base "${BUILD_ROOT}/install"     --packages-select "${PACKAGE}"

EXPECTED="${BUILD_ROOT}/install/lib/${PACKAGE}/lidar_power"

if [[ ! -x "${EXPECTED}" ]]; then
    echo "ERROR: Expected executable was not produced:" >&2
    echo "       ${EXPECTED}" >&2
    exit 1
fi

echo
echo "Build succeeded."
echo "Installing JMU TurtleBot overlay..."
echo

sudo mkdir -p "${DESTINATION}"
sudo rsync -a "${BUILD_ROOT}/install/" "${DESTINATION}/"

INSTALLED="${DESTINATION}/lib/${PACKAGE}/lidar_power"

if [[ ! -x "${INSTALLED}" ]]; then
    echo "ERROR: Installation completed, but ${INSTALLED} is missing." >&2
    exit 1
fi

echo
echo "Installation successful."
echo
echo "Installed overlay:"
echo "  ${DESTINATION}"
echo
echo "No service restart or reboot was performed."
echo "Reboot the TurtleBot when appropriate:"
echo
echo "  sudo reboot"
