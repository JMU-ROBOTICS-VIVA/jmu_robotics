#!/usr/bin/env bash
set -euo pipefail

PACKAGE="jmu_tb4_bringup"
ROS_DISTRO="${ROS_DISTRO:-jazzy}"
DESTINATION="/opt/jmu/turtlebot4/ros"
STARTUP_LINK="/etc/ros/jazzy/turtlebot4.d/lite.launch.py"

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/../.." && pwd)"
WORKSPACE="${REPO_ROOT}/ros"

if [[ "${EUID}" -eq 0 ]]; then
    echo "ERROR: Run this script as the normal user, not with sudo." >&2
    echo "       sudo is used only for the final install and startup symlink." >&2
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

# ROS setup scripts may reference unset variables, so temporarily disable
# nounset while sourcing ROS and then restore it.
set +u
# shellcheck disable=SC1090
source "${ROS_SETUP}"
set -u

cd "${WORKSPACE}"

if ! colcon list 2>/dev/null | awk '{print $1}' | grep -qx "${PACKAGE}"; then
    echo "ERROR: colcon cannot find package '${PACKAGE}' under ${WORKSPACE}." >&2
    exit 1
fi

# Build in a fresh temporary tree so stale files and previous colcon install
# layouts cannot affect the deployment.
BUILD_ROOT="$(mktemp -d "/tmp/${PACKAGE}.XXXXXX")"
trap 'rm -rf "${BUILD_ROOT}"' EXIT

echo "Building ${PACKAGE}"
echo "Workspace:   ${WORKSPACE}"
echo "Destination: ${DESTINATION}"
echo

colcon --log-base "${BUILD_ROOT}/log" build \
    --merge-install \
    --build-base "${BUILD_ROOT}/build" \
    --install-base "${BUILD_ROOT}/install" \
    --packages-select "${PACKAGE}"

EXPECTED_LIDAR="${BUILD_ROOT}/install/lib/${PACKAGE}/lidar_power"
EXPECTED_LAUNCH="${BUILD_ROOT}/install/share/${PACKAGE}/launch/lite.launch.py"

if [[ ! -x "${EXPECTED_LIDAR}" ]]; then
    echo "ERROR: Expected executable was not produced:" >&2
    echo "       ${EXPECTED_LIDAR}" >&2
    exit 1
fi

if [[ ! -f "${EXPECTED_LAUNCH}" ]]; then
    echo "ERROR: Expected launch file was not produced:" >&2
    echo "       ${EXPECTED_LAUNCH}" >&2
    exit 1
fi

echo
echo "Build succeeded."
echo "Installing JMU TurtleBot overlay..."
echo

sudo mkdir -p "${DESTINATION}"
sudo rsync -a "${BUILD_ROOT}/install/" "${DESTINATION}/"

INSTALLED_LIDAR="${DESTINATION}/lib/${PACKAGE}/lidar_power"
JMU_LAUNCH="${DESTINATION}/share/${PACKAGE}/launch/lite.launch.py"

if [[ ! -x "${INSTALLED_LIDAR}" ]]; then
    echo "ERROR: Installation completed, but ${INSTALLED_LIDAR} is missing." >&2
    exit 1
fi

if [[ ! -f "${JMU_LAUNCH}" ]]; then
    echo "ERROR: Installation completed, but ${JMU_LAUNCH} is missing." >&2
    exit 1
fi

echo
echo "Configuring TurtleBot startup launch..."

sudo mkdir -p "$(dirname "${STARTUP_LINK}")"

CURRENT_TARGET="$(readlink -f "${STARTUP_LINK}" 2>/dev/null || true)"

# Preserve the existing startup entry once if it is not already our JMU link.
if [[ -e "${STARTUP_LINK}" || -L "${STARTUP_LINK}" ]]; then
    if [[ "${CURRENT_TARGET}" != "${JMU_LAUNCH}" ]]; then
        BACKUP="${STARTUP_LINK}.pre-jmu"
        if [[ ! -e "${BACKUP}" && ! -L "${BACKUP}" ]]; then
            echo "Saving existing startup entry as:"
            echo "  ${BACKUP}"
            sudo cp -a "${STARTUP_LINK}" "${BACKUP}"
        fi
    fi
fi

sudo ln -sfn "${JMU_LAUNCH}" "${STARTUP_LINK}"

RESOLVED_TARGET="$(readlink -f "${STARTUP_LINK}" 2>/dev/null || true)"

if [[ "${RESOLVED_TARGET}" != "${JMU_LAUNCH}" ]]; then
    echo "ERROR: Startup link was not configured correctly." >&2
    echo "       Expected: ${JMU_LAUNCH}" >&2
    echo "       Found:    ${RESOLVED_TARGET:-<unresolved>}" >&2
    exit 1
fi

echo
echo "Installation successful."
echo
echo "Installed overlay:"
echo "  ${DESTINATION}"
echo
echo "Startup launch:"
echo "  ${STARTUP_LINK} -> ${RESOLVED_TARGET}"
echo
echo "No service restart or reboot was performed."
echo "Reboot the TurtleBot when appropriate:"
echo
echo "  sudo reboot"
