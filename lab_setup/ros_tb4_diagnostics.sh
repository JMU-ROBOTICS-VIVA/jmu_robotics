#!/usr/bin/env bash
#
# ros_tb4_diagnostics.bash
#
# Read-only diagnostic collection for ROS 2 / Gazebo / Fast DDS problems.
# Run this WHILE the problem is occurring, before killing Gazebo or cleaning
# Fast DDS shared-memory state.
#
# Output:
#   ~/ros_tb4_diagnostics/tb4_diag_<host>_<user>_<timestamp>.txt
#

set -u

TIMEOUT_SECS=8
OUTDIR="$HOME/ros_tb4_diagnostics"
mkdir -p "$OUTDIR"

STAMP="$(date '+%Y%m%d_%H%M%S')"
HOST="$(hostname -s 2>/dev/null || hostname)"
ME="$(id -un)"
OUTFILE="$OUTDIR/rostb4_diag_${HOST}_${ME}_${STAMP}.txt"

# Copy everything printed by this script to both the terminal and the file.
exec > >(tee "$OUTFILE") 2>&1

section()
{
    echo
    echo "======================================================================"
    echo "$1"
    echo "======================================================================"
}

run()
{
    local cmd="$1"
    echo
    echo "\$ $cmd"
    timeout "${TIMEOUT_SECS}s" bash -c "$cmd"
    local status=$?

    if [ "$status" -eq 124 ]; then
        echo "[diagnostic] COMMAND TIMED OUT after ${TIMEOUT_SECS}s"
    elif [ "$status" -ne 0 ]; then
        echo "[diagnostic] command exited with status $status"
    fi

    return 0
}

section "TB4 / ROS / GAZEBO DIAGNOSTIC REPORT"

echo "IMPORTANT: This script does not kill processes or clean /dev/shm."
echo "It is intended to capture the machine while the failure is occurring."
echo
echo "Report file: $OUTFILE"
echo "Date:        $(date --iso-8601=seconds 2>/dev/null || date)"
echo "Host:        $HOST"
echo "User:        $ME"

section "SYSTEM INFORMATION"

run 'hostnamectl 2>/dev/null || true'
run 'uname -a'
run 'uptime'
run 'id'
run 'who'
run 'tty'
run 'free -h'
run 'df -h / /tmp /dev/shm 2>&1'
run 'mount | grep -E "/dev/shm|tmpfs"'

section "ROS / DDS ENVIRONMENT"

run 'env | sort | grep -E "^(ROS|RMW|FAST|FASTDDS|CYCLONEDDS|GZ|IGN|TURTLEBOT|ROBOT)_" || true'
run 'printf "ROS_DISTRO=%s\n" "${ROS_DISTRO-<unset>}"'
run 'printf "ROS_DOMAIN_ID=%s\n" "${ROS_DOMAIN_ID-<unset>}"'
run 'printf "RMW_IMPLEMENTATION=%s\n" "${RMW_IMPLEMENTATION-<unset>}"'
run 'printf "ROS_DISCOVERY_SERVER=%s\n" "${ROS_DISCOVERY_SERVER-<unset>}"'
run 'printf "FASTDDS_BUILTIN_TRANSPORTS=%s\n" "${FASTDDS_BUILTIN_TRANSPORTS-<unset>}"'
run 'printf "ROBOT_NAMESPACE=%s\n" "${ROBOT_NAMESPACE-<unset>}"'

section "EXECUTABLES AND PACKAGE VERSIONS"

run 'type -a ros2 2>/dev/null || true'
run 'type -a gz 2>/dev/null || true'
run 'type -a fastdds 2>/dev/null || true'
run 'python3 --version 2>&1'
run 'gz --versions 2>&1 || gz --version 2>&1 || true'
run 'dpkg-query -W -f="${binary:Package}\t${Version}\n" 2>/dev/null | grep -Ei "fastdds|fastrtps|rmw-fastrtps|ros-jazzy-ros-gz|ros-gz|turtlebot4" | sort || true'

section "RELEVANT PROCESSES -- ALL USERS"

# Looking at all users matters on shared lab computers: a stale Gazebo or DDS
# process may belong to a different login.
run 'ps -eo user,pid,ppid,lstart,stat,cmd --width 300 | grep -Ei "[g]z( |$)|[r]os2|[r]os_gz|[r]viz|[f]astdds|[f]astrtps|[m]otion_control|[t]urtlebot|[p]arameter_bridge|[p]ython.*forward" || true'

section "FAST DDS SHARED MEMORY"

run 'ls -la /dev/shm'
run 'find /dev/shm -maxdepth 1 -type f \( -name "fastrtps*" -o -name "fastdds*" -o -name "sem.fastrtps*" \) -printf "%M  owner=%u  group=%g  size=%s  modified=%TY-%Tm-%Td %TH:%TM:%TS  %p\n" 2>/dev/null | sort || true'

if command -v lslocks >/dev/null 2>&1; then
    run 'lslocks 2>/dev/null | grep -Ei "/dev/shm|fastrtps|fastdds" || true'
else
    echo "lslocks not installed."
fi

if command -v lsof >/dev/null 2>&1; then
    run 'lsof /dev/shm 2>/dev/null | grep -Ei "fastrtps|fastdds" || true'
else
    echo "lsof not installed."
fi

run 'ipcs -m 2>&1'

section "NETWORK"

run 'ip -brief address'
run 'ip route'
run 'ss -lunp 2>&1 | grep -E "(^State|ros|dds|fast|gz|:7[0-9][0-9][0-9]|:11[0-9][0-9][0-9]|:18[0-9][0-9][0-9])" || true'

section "GAZEBO TRANSPORT"

run 'gz topic -l 2>&1'
run 'gz service -l 2>&1'

section "ROS 2 GRAPH"

run 'ros2 daemon status 2>&1'
run 'ros2 node list 2>&1'
run 'ros2 topic list -t 2>&1'
run 'ros2 service list 2>&1'
run 'ros2 action list 2>&1'

section "IMPORTANT ROBOTSIM1 TOPICS"

for topic in \
    /robotsim1/scan \
    /robotsim1/odom \
    /robotsim1/cmd_vel \
    /robotsim1/tf \
    /robotsim1/tf_static
do
    echo
    echo "----- $topic -----"
    run "ros2 topic info '$topic' --verbose 2>&1"
done

section "SHORT MESSAGE-RATE TESTS"

echo "Each test is intentionally short and will normally be terminated by timeout."

for topic in /robotsim1/scan /robotsim1/odom
do
    echo
    echo "----- ros2 topic hz $topic -----"
    run "timeout 5s ros2 topic hz '$topic' 2>&1"
done

section "ROS DOCTOR"

run 'ros2 doctor --report 2>&1'

section "RECENT ROS LOG MESSAGES"

if [ -d "$HOME/.ros/log" ]; then
    run 'find "$HOME/.ros/log" -type f -mmin -60 -print0 2>/dev/null | xargs -0 -r grep -nHEi "RTPS|SHM|open_and_lock|fastrtps|fast.?dds|transport|ERROR|WARN" 2>/dev/null | tail -n 400 || true'
else
    echo "$HOME/.ros/log does not exist."
fi

section "RECENT KERNEL MESSAGES"

# This may be restricted for ordinary users; failure is harmless and useful
# to know.
run 'dmesg --ctime 2>&1 | tail -n 100'

section "END OF REPORT"

echo
echo "Diagnostic collection complete."
echo "Send this file to your instructor:"
echo
echo "    $OUTFILE"
echo
echo "Do NOT run 'fastdds shm clean' until after this report has been collected."
