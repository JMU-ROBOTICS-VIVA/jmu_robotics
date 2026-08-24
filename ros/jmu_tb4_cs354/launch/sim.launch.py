import os

from pathlib import Path

from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    IncludeLaunchDescription,
    SetEnvironmentVariable,
)
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import (
    EnvironmentVariable,
    LaunchConfiguration,
    PathJoinSubstitution,
)
from launch_ros.actions import Node


def generate_launch_description():

    pkg_turtlebot4_gz_bringup = get_package_share_directory(
        'turtlebot4_gz_bringup')
    pkg_turtlebot4_gz_gui_plugins = get_package_share_directory(
        'turtlebot4_gz_gui_plugins')
    pkg_turtlebot4_description = get_package_share_directory(
        'turtlebot4_description')
    pkg_irobot_create_description = get_package_share_directory(
        'irobot_create_description')
    pkg_irobot_create_gz_bringup = get_package_share_directory(
        'irobot_create_gz_bringup')
    pkg_irobot_create_gz_plugins = get_package_share_directory(
        'irobot_create_gz_plugins')
    pkg_ros_gz_sim = get_package_share_directory('ros_gz_sim')

    default_world = PathJoinSubstitution([
        pkg_turtlebot4_gz_bringup,
        'worlds',
        'warehouse.sdf'
    ])

    world_arg = DeclareLaunchArgument(
        'world',
        default_value=default_world,
        description='Full path to Gazebo SDF world file'
    )

    model_arg = DeclareLaunchArgument(
        'model',
        default_value='lite',
        choices=['standard', 'lite'],
        description='TurtleBot 4 model'
    )

    resource_path_arg = DeclareLaunchArgument(
        'resource_path',
        default_value='',
        description='Additional Gazebo resource/model search path'
    )

    # Keep the standard TurtleBot/Create3 resources, but also permit
    # a project package to supply its own models/resources.
    gz_resource_path = SetEnvironmentVariable(
        name='GZ_SIM_RESOURCE_PATH',
        value=[
            LaunchConfiguration('resource_path'),
            os.pathsep,
            os.path.join(pkg_turtlebot4_gz_bringup, 'worlds'),
            os.pathsep,
            os.path.join(pkg_irobot_create_gz_bringup, 'worlds'),
            os.pathsep,
            str(Path(pkg_turtlebot4_description).parent.resolve()),
            os.pathsep,
            str(Path(pkg_irobot_create_description).parent.resolve()),
            os.pathsep,
            EnvironmentVariable('GZ_SIM_RESOURCE_PATH',
                                default_value='')
        ]
    )

    gz_gui_plugin_path = SetEnvironmentVariable(
        name='GZ_GUI_PLUGIN_PATH',
        value=':'.join([
            os.path.join(pkg_turtlebot4_gz_gui_plugins, 'lib'),
            os.path.join(pkg_irobot_create_gz_plugins, 'lib')
        ])
    )

    gz_sim_launch = PathJoinSubstitution([
        pkg_ros_gz_sim,
        'launch',
        'gz_sim.launch.py'
    ])

    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([gz_sim_launch]),
        launch_arguments=[
            ('gz_args', [
                LaunchConfiguration('world'),
                ' -r',
                ' -v 4',
                ' --gui-config ',
                PathJoinSubstitution([
                    pkg_turtlebot4_gz_bringup,
                    'gui',
                    LaunchConfiguration('model'),
                    'gui.config'
                ])
            ])
        ]
    )

    clock_bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        name='clock_bridge',
        output='screen',
        arguments=[
            '/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock'
        ]
    )

    return LaunchDescription([
        world_arg,
        model_arg,
        resource_path_arg,
        gz_resource_path,
        gz_gui_plugin_path,
        gazebo,
        clock_bridge,
    ])

