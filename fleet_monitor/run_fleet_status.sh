#!/usr/bin/env bash
# Run the ROS collector as the dedicated rosrpt service account.

set -euo pipefail

CONFIG="/etc/jmu_tb4/fleet-monitor.conf"

if [ ! -r "$CONFIG" ]; then
    echo "ERROR: Fleet monitor config not found: $CONFIG" >&2
    exit 1
fi

# shellcheck source=/dev/null
source "$CONFIG"

if [ "${#ROBOTS[@]}" -eq 0 ]; then
    echo "ERROR: ROBOTS is empty in $CONFIG" >&2
    exit 1
fi

# ROS setup scripts are not guaranteed to be nounset-clean.
set +u
source /opt/ros/jazzy/setup.bash
source /opt/jmu/cs354/ros/local_setup.bash
set -u

export ROS_DOMAIN_ID=42
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp
export ROS_SUPER_CLIENT=TRUE
unset ROS_AUTOMATIC_DISCOVERY_RANGE
unset ROBOT_NAMESPACE

# Build ROS_DISCOVERY_SERVER so server position N corresponds to Robot N.
max_robot=0
for robot in "${ROBOTS[@]}"; do
    if ! [[ "$robot" =~ ^[1-9][0-9]*$ ]]; then
        echo "ERROR: Invalid robot number in ROBOTS: $robot" >&2
        exit 1
    fi
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
    --rate-window "$RATE_WINDOW" \
    --stream-inactive-seconds "$STREAM_INACTIVE_SECONDS" \
    --parameter-interval "$PARAMETER_INTERVAL"
