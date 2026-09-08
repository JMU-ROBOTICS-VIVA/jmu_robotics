#!/usr/bin/env bash
# Conservative cleanup for the JMU CS354 TurtleBot 4 Gazebo simulator.
#
# This script intentionally targets only Gazebo Sim processes. It does not
# kill arbitrary ROS 2 nodes, stop the ROS 2 daemon, or use SIGKILL.

set -u

find_gazebo_sim_pids() {
    ps -eo pid=,comm=,args= | awk '
        $2 == "gz-sim-server" ||
        $2 == "gz-sim-gui" ||
        $0 ~ /(^|[[:space:]\/])gz[[:space:]]+sim([[:space:]]|$)/ {
            print $1
        }
    '
}

show_processes() {
    local pid
    for pid in "$@"; do
        if kill -0 "$pid" 2>/dev/null; then
            ps -p "$pid" -o pid=,ppid=,stat=,comm=,args=
        fi
    done
}

get_running_pids() {
    local pid
    local -a candidates=("$@")
    RUNNING_PIDS=()

    for pid in "${candidates[@]}"; do
        if kill -0 "$pid" 2>/dev/null; then
            RUNNING_PIDS+=("$pid")
        fi
    done
}

wait_for_exit() {
    local attempts="$1"
    shift
    local -a candidates=("$@")
    local i

    for ((i = 0; i < attempts; i++)); do
        get_running_pids "${candidates[@]}"
        if ((${#RUNNING_PIDS[@]} == 0)); then
            return 0
        fi
        sleep 0.25
    done

    return 1
}

echo "Checking for running Gazebo simulation processes..."
mapfile -t gazebo_pids < <(find_gazebo_sim_pids)

if ((${#gazebo_pids[@]} == 0)); then
    echo "No Gazebo simulation processes found."
    exit 0
fi

echo
echo "Found the following Gazebo simulation processes:"
show_processes "${gazebo_pids[@]}"

echo
echo "Requesting graceful shutdown with SIGINT..."
for pid in "${gazebo_pids[@]}"; do
    kill -INT "$pid" 2>/dev/null || true
done

if wait_for_exit 20 "${gazebo_pids[@]}"; then
    echo "Gazebo simulation stopped cleanly."
    exit 0
fi

get_running_pids "${gazebo_pids[@]}"
echo
echo "Some Gazebo processes did not exit after SIGINT:"
show_processes "${RUNNING_PIDS[@]}"

echo
echo "Sending SIGTERM to the remaining Gazebo processes..."
remaining=("${RUNNING_PIDS[@]}")
for pid in "${remaining[@]}"; do
    kill -TERM "$pid" 2>/dev/null || true
done

if wait_for_exit 12 "${remaining[@]}"; then
    echo "Gazebo simulation stopped."
    exit 0
fi

get_running_pids "${remaining[@]}"
echo
echo "WARNING: Gazebo processes are still running:"
show_processes "${RUNNING_PIDS[@]}"
echo
echo "No SIGKILL was sent. Investigate these processes before launching Gazebo again."
exit 1
