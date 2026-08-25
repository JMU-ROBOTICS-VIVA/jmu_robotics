\
#!/usr/bin/env bash
set -euo pipefail

CONFIG="/etc/jmu_tb4/fleet-monitor.conf"
test -r "$CONFIG" || { echo "ERROR: missing $CONFIG" >&2; exit 1; }
source "$CONFIG"

# Backward-compatible defaults for an existing preserved configuration file.
WRITE_INTERVAL="${WRITE_INTERVAL:-60}"
STALE_SECONDS="${STALE_SECONDS:-15}"
SAMPLE_WINDOW="${SAMPLE_WINDOW:-5}"
PARAMETER_INTERVAL="${PARAMETER_INTERVAL:-60}"

if [ "${#ROBOTS[@]}" -eq 0 ]; then
    echo "ERROR: ROBOTS is empty in $CONFIG" >&2
    exit 1
fi

set +u
source /opt/ros/jazzy/setup.bash
source /opt/jmu/cs354/ros/local_setup.bash
set -u

export ROS_DOMAIN_ID=42
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp
export ROS_SUPER_CLIENT=TRUE
unset ROS_AUTOMATIC_DISCOVERY_RANGE
unset ROBOT_NAMESPACE

max_robot=0
for robot in "${ROBOTS[@]}"; do
    [[ "$robot" =~ ^[1-9][0-9]*$ ]] || {
        echo "ERROR: invalid robot number: $robot" >&2
        exit 1
    }
    (( robot > max_robot )) && max_robot=$robot
done

ROS_DISCOVERY_SERVER=""
for ((id=0; id<=max_robot; id++)); do
    (( id > 0 )) && ROS_DISCOVERY_SERVER+=";"
    for robot in "${ROBOTS[@]}"; do
        if (( robot == id )); then
            ROS_DISCOVERY_SERVER+="tb${robot}.cs.jmu.edu:11811"
            break
        fi
    done
done
export ROS_DISCOVERY_SERVER

exec ros2 run jmu_tb4_fleet fleet_status \
    --robots "${ROBOTS[@]}" \
    --output "$STATUS_FILE" \
    --write-interval "$WRITE_INTERVAL" \
    --stale-seconds "$STALE_SECONDS" \
    --sample-window "$SAMPLE_WINDOW" \
    --parameter-interval "$PARAMETER_INTERVAL"
