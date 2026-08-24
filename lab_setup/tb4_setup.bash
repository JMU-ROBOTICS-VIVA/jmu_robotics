#!/usr/bin/env bash
#
# JMU CS354 TurtleBot 4 shell environment
# Installed as /opt/jmu/cs354/tb4_setup.bash and sourced by /etc/bash.bashrc.
#
# Per-user selection is stored in ~/.config/jmu_tb4/selection.
# Valid physical selections come from /opt/jmu/cs354/tb4_setup.conf.
# S selects the simulator.

[[ $- != *i* ]] && return

# Load site-wide fleet configuration from the same directory as this script.
_JMU_TB4_SETUP_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
_JMU_TB4_SITE_CONFIG="${_JMU_TB4_SETUP_DIR}/tb4_setup.conf"

if [ -r "$_JMU_TB4_SITE_CONFIG" ]; then
    source "$_JMU_TB4_SITE_CONFIG"
else
    echo "WARNING: JMU TurtleBot site configuration was not found:"
    echo "         $_JMU_TB4_SITE_CONFIG"
    PHYSICAL_ROBOTS=()
    SIM_NAMESPACE="/robotsim1"
fi

# ROS environment: base -> JMU infrastructure -> student overlay
if [ -r /opt/ros/jazzy/setup.bash ]; then
    source /opt/ros/jazzy/setup.bash
else
    echo "WARNING: /opt/ros/jazzy/setup.bash was not found."
fi

if [ -r /opt/jmu/cs354/ros/local_setup.bash ]; then
    source /opt/jmu/cs354/ros/local_setup.bash
else
    echo "WARNING: JMU CS354 ROS installation was not found."
fi

if [ -r "$HOME/rosdev/install/local_setup.bash" ]; then
    source "$HOME/rosdev/install/local_setup.bash"
fi

export ROS_DOMAIN_ID=42
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp

_JMU_TB4_CONFIG_DIR="$HOME/.config/jmu_tb4"
_JMU_TB4_SELECTION_FILE="$_JMU_TB4_CONFIG_DIR/selection"

# Return success only when the requested number is explicitly listed in
# PHYSICAL_ROBOTS.  This protects against both invalid menu input and a
# manually edited per-user selection file.
_jmu_tb4_is_physical_robot()
{
    local candidate="$1"
    local robot

    [[ "$candidate" =~ ^[1-9][0-9]*$ ]] || return 1

    for robot in "${PHYSICAL_ROBOTS[@]}"; do
        if [ "$candidate" = "$robot" ]; then
            return 0
        fi
    done

    return 1
}

_jmu_tb4_robot_choices()
{
    local IFS=,
    printf '%s' "${PHYSICAL_ROBOTS[*]}"
}

# Safe, unselected state: do not perform subnet-wide discovery.
_jmu_tb4_clear()
{
    unset ROBOT_NAMESPACE
    unset ROS_DISCOVERY_SERVER
    unset ROS_SUPER_CLIENT
    export ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST
}

# Apply a selection to the CURRENT shell.
_jmu_tb4_apply()
{
    local selection="$1"

    if [[ "$selection" =~ ^[Ss]$ ]]; then
        export ROBOT_NAMESPACE="$SIM_NAMESPACE"
        unset ROS_DISCOVERY_SERVER
        unset ROS_SUPER_CLIENT
        export ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST
        return 0
    fi

    if _jmu_tb4_is_physical_robot "$selection"; then
        export ROBOT_NAMESPACE="/robot${selection}"

        # Physical robot N uses Discovery Server ID N.
        #
        # In ROS_DISCOVERY_SERVER, the server ID is represented by its
        # zero-based position in the semicolon-separated list. Robot N
        # therefore needs N empty entries before its server locator:
        #
        #   Robot 1: ;tb1.cs.jmu.edu:11811
        #   Robot 2: ;;tb2.cs.jmu.edu:11811
        #   ...
        #
        local server_prefix=""
        local i
        for ((i=0; i<selection; i++)); do
            server_prefix="${server_prefix};"
        done

        export ROS_DISCOVERY_SERVER="${server_prefix}tb${selection}.cs.jmu.edu:11811"

        export ROS_SUPER_CLIENT=TRUE
        unset ROS_AUTOMATIC_DISCOVERY_RANGE
        return 0
    fi

    return 1
}

_jmu_tb4_print_status()
{
    local selection

    echo
    echo "------------------------------------------------------------"
    echo "JMU CS354 TurtleBot Environment"
    echo
    echo "  ROS domain:  ${ROS_DOMAIN_ID:-<unset>}"
    if [ "${ROS_DOMAIN_ID:-}" != "42" ]; then
        echo "  WARNING: expected ROS_DOMAIN_ID=42"
    fi
    echo

    if [ ! -r "$_JMU_TB4_SELECTION_FILE" ]; then
        echo "  No robot environment has been selected."
        echo
        echo "Run 'tb4-select' to select:"
        echo "  S                 Simulator ($SIM_NAMESPACE)"
        if [ "${#PHYSICAL_ROBOTS[@]}" -gt 0 ]; then
            echo "  ${PHYSICAL_ROBOTS[*]}   Physical TurtleBot(s)"
        else
            echo "  No physical TurtleBots are currently configured."
        fi
        echo "------------------------------------------------------------"
        echo
        return 1
    fi

    selection=$(<"$_JMU_TB4_SELECTION_FILE")

    if [[ "$selection" =~ ^[Ss]$ ]]; then
        echo "  Mode:       Simulator"
        echo "  Namespace:  $ROBOT_NAMESPACE"
        echo
        echo "Run 'tb4-select' to change environments."
    elif _jmu_tb4_is_physical_robot "$selection"; then
        echo "  Mode:       Physical Robot"
        echo "  Robot:      $selection"
        echo "  Host:       tb${selection}.cs.jmu.edu"
        echo "  Namespace:  $ROBOT_NAMESPACE"
        echo
        echo "Run 'tb4-select' to change environments."
    else
        echo "  WARNING: Invalid saved configuration."
        echo
        echo "Run 'tb4-select' to select an environment."
    fi

    echo "------------------------------------------------------------"
    echo
}

tb4-status()
{
    _jmu_tb4_print_status
}

tb4-select()
{
    local answer
    local selection
    local robot
    local robot_choices

    robot_choices="$(_jmu_tb4_robot_choices)"

    echo
    echo "============================================================"
    echo " JMU TurtleBot 4 Environment Selection"
    echo "============================================================"
    echo
    echo "IMPORTANT:"
    echo
    echo "Before changing the ROS environment:"
    echo
    echo "  1. Close all OTHER terminal windows and tabs."
    echo "  2. Stop any running ROS 2 programs."
    echo "  3. Stop RViz and Gazebo if they are running."
    echo
    echo "Already-running processes cannot receive the new environment."
    echo
    read -r -p "Type YES when you have done this: " answer

    if [ "$answer" != "YES" ]; then
        echo
        echo "No changes were made."
        echo
        return 1
    fi

    echo
    echo "Select the environment:"
    echo
    echo "    S     Simulator ($SIM_NAMESPACE)"
    for robot in "${PHYSICAL_ROBOTS[@]}"; do
        echo "    $robot     TurtleBot $robot"
    done
    echo

    while true; do
        if [ -n "$robot_choices" ]; then
            read -r -p "Selection [S,${robot_choices}]: " selection
        else
            read -r -p "Selection [S]: " selection
        fi

        if [[ "$selection" =~ ^[Ss]$ ]]; then
            selection="S"
            break
        fi

        if _jmu_tb4_is_physical_robot "$selection"; then
            break
        fi

        echo
        if [ -n "$robot_choices" ]; then
            echo "Invalid selection. Enter S or one of: ${PHYSICAL_ROBOTS[*]}."
        else
            echo "Invalid selection. Only S (simulator) is currently available."
        fi
        echo
    done

    # Stop the ROS CLI daemon while this shell still has the OLD discovery
    # environment, avoiding a daemon that retains stale discovery settings.
    ros2 daemon stop >/dev/null 2>&1 || true

    mkdir -p "$_JMU_TB4_CONFIG_DIR"
    printf '%s\n' "$selection" > "$_JMU_TB4_SELECTION_FILE"

    if ! _jmu_tb4_apply "$selection"; then
        echo
        echo "ERROR: Could not apply TurtleBot configuration."
        echo
        return 1
    fi

    echo
    echo "============================================================"

    if [ "$selection" = "S" ]; then
        echo " This terminal is now configured for the SIMULATOR."
        echo
        echo " Namespace: $ROBOT_NAMESPACE"
    else
        echo " This terminal is now configured for ROBOT $selection."
        echo
        echo " Host:      tb${selection}.cs.jmu.edu"
        echo " Namespace: $ROBOT_NAMESPACE"
    fi

    echo
    echo " New terminals will automatically use this configuration."
    echo "============================================================"
    echo
}

# Convenience wrapper. ROBOT_NAMESPACE is a JMU environment variable;
# arbitrary ROS nodes do not automatically use it. This explicitly places
# teleop_twist_keyboard in the selected namespace, so its relative cmd_vel
# publisher resolves beneath the selected robot namespace.
tb4-teleop()
{
    if [ -z "${ROBOT_NAMESPACE:-}" ]; then
        echo "No TurtleBot environment is selected."
        echo "Run 'tb4-select' first."
        return 1
    fi

    ros2 run teleop_twist_keyboard teleop_twist_keyboard \
        --ros-args \
        -p stamped:=true \
        -r "__ns:=${ROBOT_NAMESPACE}"
}

# Initialize every new interactive shell.
if [ -r "$_JMU_TB4_SELECTION_FILE" ]; then
    _jmu_tb4_saved_selection=$(<"$_JMU_TB4_SELECTION_FILE")

    if ! _jmu_tb4_apply "$_jmu_tb4_saved_selection"; then
        _jmu_tb4_clear
    fi
else
    _jmu_tb4_clear
fi

_jmu_tb4_print_status
