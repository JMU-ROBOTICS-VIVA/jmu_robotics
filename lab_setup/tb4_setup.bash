#!/usr/bin/env bash
#
# JMU CS354 TurtleBot 4 shell environment
# Installed as /opt/jmu/cs354/tb4_setup.bash and sourced by /etc/bash.bashrc.
#
# Per-user selection is stored in ~/.config/jmu_tb4/selection.
# Valid selections: S (simulator) or 1-7 (physical TurtleBot).

[[ $- != *i* ]] && return

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

    case "$selection" in
        S|s)
            # Simulator namespace is outside physical robot numbers 1-7.
            export ROBOT_NAMESPACE="/robot9"
            unset ROS_DISCOVERY_SERVER
            unset ROS_SUPER_CLIENT
            export ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST
            ;;

        [1-7])
            export ROBOT_NAMESPACE="/robot${selection}"

            # Physical robot N uses Discovery Server ID N.
            #
            # In ROS_DISCOVERY_SERVER, the server ID is represented by its
            # zero-based position in the semicolon-separated list. Because
            # our robots intentionally use IDs 1 through 7, Robot N needs N
            # empty entries before its server locator:
            #
            #   Robot 1: ;tb1.cs.jmu.edu:11811
            #   Robot 2: ;;tb2.cs.jmu.edu:11811
            #   ...
            #   Robot 7: ;;;;;;;tb7.cs.jmu.edu:11811
            #
            local server_prefix=""
            local i

            for ((i=0; i<selection; i++)); do
                server_prefix="${server_prefix};"
            done

            export ROS_DISCOVERY_SERVER="${server_prefix}tb${selection}.cs.jmu.edu:11811"

            export ROS_SUPER_CLIENT=TRUE
            unset ROS_AUTOMATIC_DISCOVERY_RANGE
            ;;

        *)
            return 1
            ;;
    esac

    return 0
}

_jmu_tb4_print_status()
{
    local selection

    echo
    echo "------------------------------------------------------------"
    echo "JMU CS354 TurtleBot Environment"
    echo

    if [ ! -r "$_JMU_TB4_SELECTION_FILE" ]; then
        echo "  No robot environment has been selected."
        echo
        echo "Run 'tb4-select' to select:"
        echo "  S     Simulator"
        echo "  1-7   Physical TurtleBot"
        echo "------------------------------------------------------------"
        echo
        return 1
    fi

    selection=$(<"$_JMU_TB4_SELECTION_FILE")

    case "$selection" in
        S)
            echo "  Mode:       Simulator"
            echo "  Namespace:  $ROBOT_NAMESPACE"
            echo
            echo "Run 'tb4-select' to change environments."
            ;;
        [1-7])
            echo "  Mode:       Physical Robot"
            echo "  Robot:      $selection"
            echo "  Host:       tb${selection}.cs.jmu.edu"
            echo "  Namespace:  $ROBOT_NAMESPACE"
            echo
            echo "Run 'tb4-select' to change environments."
            ;;
        *)
            echo "  WARNING: Invalid saved configuration."
            echo
            echo "Run 'tb4-select' to select an environment."
            ;;
    esac

    echo "------------------------------------------------------------"
    echo
}

tb4-status()
{
    _jmu_tb4_print_status
}

_jmu_tb4_require_robot_namespace()
{
    if [ -z "${ROBOT_NAMESPACE:-}" ]; then
        echo "No single TurtleBot environment is selected."
        echo "Run 'tb4-select' and select the simulator or one physical robot."
        return 1
    fi
}

tb4-select()
{
    local answer
    local selection

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
    echo "    S     Simulator"
    echo "    1     TurtleBot 1"
    echo "    2     TurtleBot 2"
    echo "    3     TurtleBot 3"
    echo "    4     TurtleBot 4"
    echo "    5     TurtleBot 5"
    echo "    6     TurtleBot 6"
    echo "    7     TurtleBot 7"
    echo

    while true; do
        read -r -p "Selection [S,1-7]: " selection

        case "$selection" in
            S|s)
                selection="S"
                break
                ;;
            [1-7])
                break
                ;;
            *)
                echo
                echo "Invalid selection. Enter S or a number from 1 through 7."
                echo
                ;;
        esac
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
# publisher resolves to /robotN/cmd_vel.
tb4-teleop()
{
    _jmu_tb4_require_robot_namespace || return 1

    ros2 run teleop_twist_keyboard teleop_twist_keyboard \
        --ros-args \
        -r "__ns:=${ROBOT_NAMESPACE}"
}

# Echo a transform from the currently selected robot's TF tree.
# Frame names are intentionally unqualified: e.g. base_link, odom,
# rplidar_link. The selected robot is identified by ROBOT_NAMESPACE.
tb4-tf()
{
    _jmu_tb4_require_robot_namespace || return 1

    if [ "$#" -lt 2 ]; then
        echo "Usage: tb4-tf <target-frame> <source-frame> [tf2_echo options]"
        return 2
    fi

    ros2 run tf2_ros tf2_echo "$@" \
        --ros-args \
        -r "__ns:=${ROBOT_NAMESPACE}" \
        -r /tf:=tf \
        -r /tf_static:=tf_static
}

# Generate a PDF/DOT view of the currently selected robot's TF tree.
tb4-tf-tree()
{
    _jmu_tb4_require_robot_namespace || return 1

    ros2 run tf2_tools view_frames \
        --ros-args \
        -r "__ns:=${ROBOT_NAMESPACE}" \
        -r /tf:=tf \
        -r /tf_static:=tf_static
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
