# Copyright 2026 James Madison University
#
# JMU simulator robot description.
# Uses the stock TurtleBot 4 xacro, then overrides only simulated sensor rates.

from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import Command, LaunchConfiguration, PathJoinSubstitution

from launch_ros.actions import Node


ARGUMENTS = [
    DeclareLaunchArgument(
        'model',
        default_value='standard',
        choices=['standard', 'lite'],
        description='TurtleBot 4 model',
    ),
    DeclareLaunchArgument(
        'use_sim_time',
        default_value='false',
        choices=['true', 'false'],
        description='Use simulation time',
    ),
    DeclareLaunchArgument(
        'robot_name',
        default_value='turtlebot4',
        description='Robot name',
    ),
    DeclareLaunchArgument(
        'namespace',
        default_value=LaunchConfiguration('robot_name'),
        description='Robot namespace used inside the stock xacro',
    ),
    DeclareLaunchArgument(
        'lidar_rate',
        default_value='8.0',
        description='Simulated RPLIDAR update rate in Hz',
    ),
    DeclareLaunchArgument(
        'camera_rate',
        default_value='10.0',
        description='Simulated RGBD camera update rate in Hz',
    ),
]


def generate_launch_description():
    pkg_turtlebot4_description = get_package_share_directory(
        'turtlebot4_description'
    )
    pkg_jmu_tb4 = get_package_share_directory('jmu_tb4_cs354')

    xacro_file = PathJoinSubstitution([
        pkg_turtlebot4_description,
        'urdf',
        LaunchConfiguration('model'),
        'turtlebot4.urdf.xacro',
    ])

    description_tool = PathJoinSubstitution([
        pkg_jmu_tb4,
        'scripts',
        'sim_robot_description.py',
    ])

    robot_description = Command([
        'python3', ' ',
        description_tool, ' ',
        '--xacro', ' ', xacro_file, ' ',
        '--namespace', ' ', LaunchConfiguration('namespace'), ' ',
        '--lidar-rate', ' ', LaunchConfiguration('lidar_rate'), ' ',
        '--camera-rate', ' ', LaunchConfiguration('camera_rate'),
    ])

    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        output='screen',
        parameters=[
            {'use_sim_time': LaunchConfiguration('use_sim_time')},
            {'robot_description': robot_description},
        ],
        remappings=[
            ('/tf', 'tf'),
            ('/tf_static', 'tf_static'),
        ],
    )

    joint_state_publisher = Node(
        package='joint_state_publisher',
        executable='joint_state_publisher',
        name='joint_state_publisher',
        output='screen',
        parameters=[
            {'use_sim_time': LaunchConfiguration('use_sim_time')},
        ],
        remappings=[
            ('/tf', 'tf'),
            ('/tf_static', 'tf_static'),
        ],
    )

    ld = LaunchDescription(ARGUMENTS)
    ld.add_action(robot_state_publisher)
    ld.add_action(joint_state_publisher)
    return ld
