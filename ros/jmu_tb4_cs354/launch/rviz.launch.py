# Copyright 2026 James Madison University
#
# Launch the JMU TurtleBot RViz configuration for the selected robot.
#
# ROBOT_NAMESPACE is set by the JMU CS354 shell environment
# (for example, /robot1 or /robotsim1). An explicit namespace:=...
# launch argument can still override the environment value.

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, GroupAction
from launch.substitutions import EnvironmentVariable, LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node, PushRosNamespace


def generate_launch_description():
    pkg_jmu_tb4 = get_package_share_directory('jmu_tb4_cs354')

    rviz_config = PathJoinSubstitution([
        pkg_jmu_tb4,
        'rviz',
        'robot.rviz',
    ])

    namespace_arg = DeclareLaunchArgument(
        'namespace',
        default_value=EnvironmentVariable(
            'ROBOT_NAMESPACE',
            default_value='',
        ),
        description='Robot namespace; defaults to ROBOT_NAMESPACE',
    )

    use_sim_time_arg = DeclareLaunchArgument(
        'use_sim_time',
        default_value='false',
        choices=['true', 'false'],
        description='Use the simulation clock',
    )

    namespace = LaunchConfiguration('namespace')
    use_sim_time = LaunchConfiguration('use_sim_time')

    rviz = GroupAction([
        PushRosNamespace(namespace),
        Node(
            package='rviz2',
            executable='rviz2',
            arguments=['-d', rviz_config],
            parameters=[{'use_sim_time': use_sim_time}],
            remappings=[
                ('/tf', 'tf'),
                ('/tf_static', 'tf_static'),
            ],
            output='screen',
        ),
    ])

    return LaunchDescription([
        namespace_arg,
        use_sim_time_arg,
        rviz,
    ])
