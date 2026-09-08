import os
from pathlib import Path

from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    IncludeLaunchDescription,
    LogInfo,
    OpaqueFunction,
    SetLaunchConfiguration,
)
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import EnvironmentVariable, LaunchConfiguration, PathJoinSubstitution


def check_ros_domain_id():
    expected_domain = '43'
    # ROS 2 uses domain 0 when ROS_DOMAIN_ID is not set.
    actual_domain = os.environ.get('ROS_DOMAIN_ID', '0')
    if actual_domain != expected_domain:
        raise RuntimeError(
            '\n\n'
            '============================================================\n'
            'JMU TurtleBot 4 simulator configuration error\n'
            '============================================================\n'
            f'ROS_DOMAIN_ID is {actual_domain}, but the simulator requires '
            f'ROS_DOMAIN_ID={expected_domain}.\n\n'
            'Run tb4-select and select the simulator.\n'
            'Then launch the simulator again.\n'
            '============================================================\n'
        )


def resolve_world_path(world_argument, turtlebot_share):
    """Resolve a user-friendly world argument to an absolute SDF path.

    Resolution rules:
      * absolute path or ~/...: use that filesystem path
      * ./... or ../...: resolve relative to the current working directory
      * bare name (maze or maze.sdf): use turtlebot4_gz_bringup/worlds/
      * other relative path: resolve relative to turtlebot4_gz_bringup
    """
    requested = os.path.expanduser(world_argument.strip())
    if not requested:
        raise RuntimeError('The world launch argument may not be empty.')

    if os.path.isabs(requested):
        world_path = Path(requested)
    elif requested.startswith('./') or requested.startswith('../'):
        world_path = Path(requested).resolve()
    else:
        relative_path = Path(requested)

        # A bare world name is the common classroom case.  Add .sdf if the
        # user omitted it, then look in the stock TurtleBot worlds directory.
        if len(relative_path.parts) == 1:
            if relative_path.suffix == '':
                relative_path = relative_path.with_suffix('.sdf')
            relative_path = Path('worlds') / relative_path

        world_path = Path(turtlebot_share) / relative_path

    world_path = world_path.resolve()

    if not world_path.is_file():
        raise RuntimeError(
            '\n\n'
            '============================================================\n'
            'JMU TurtleBot 4 simulator world error\n'
            '============================================================\n'
            f'Could not find the requested Gazebo world:\n  {world_argument}\n\n'
            f'Resolved path:\n  {world_path}\n\n'
            'Examples:\n'
            '  world:=maze\n'
            '  world:=maze.sdf\n'
            '  world:=worlds/maze.sdf\n'
            '  world:=./my_worlds/test.sdf\n'
            '  world:=/absolute/path/to/test.sdf\n'
            '============================================================\n'
        )

    return str(world_path)


def resolve_world_arguments(context, turtlebot_share):
    requested_world = LaunchConfiguration('world').perform(context)
    resolved_world = resolve_world_path(requested_world, turtlebot_share)

    requested_world_name = LaunchConfiguration('world_name').perform(context).strip()
    resolved_world_name = requested_world_name or Path(resolved_world).stem

    return [
        SetLaunchConfiguration('resolved_world', resolved_world),
        SetLaunchConfiguration('resolved_world_name', resolved_world_name),
        LogInfo(
            msg=(
                f'Gazebo world: {resolved_world} '
                f'(world name: {resolved_world_name})'
            )
        ),
    ]


def generate_launch_description():
    check_ros_domain_id()

    # Package directories
    pkg_jmu_tb4 = get_package_share_directory('jmu_tb4_cs354')
    pkg_tb4_gz = get_package_share_directory('turtlebot4_gz_bringup')
    pkg_tb4_navigation = get_package_share_directory('turtlebot4_navigation')

    # Our two lower-level launch files
    sim_launch = PathJoinSubstitution([
        pkg_jmu_tb4,
        'launch',
        'sim.launch.py'
    ])
    spawn_launch = PathJoinSubstitution([
        pkg_jmu_tb4,
        'launch',
        'spawn.launch.py'
    ])

    # Default map, used only if localization is requested
    default_map = PathJoinSubstitution([
        pkg_tb4_navigation,
        'maps',
        'warehouse.yaml'
    ])
    arguments = [
        DeclareLaunchArgument(
            'namespace',
            default_value=EnvironmentVariable(
                'ROBOT_NAMESPACE',
                default_value='/robotsim1'
            ),
            description='Robot namespace; spawn.launch.py normalizes a leading slash for Gazebo'
        ),
        DeclareLaunchArgument(
            'world',
            default_value='warehouse',
            description=(
                'Gazebo world: a stock TurtleBot world name, a path relative to '
                'turtlebot4_gz_bringup, or an explicit filesystem path'
            )
        ),
        DeclareLaunchArgument(
            'world_name',
            default_value='',
            description=(
                'Name of the world inside the SDF file; by default it is '
                'inferred from the SDF filename'
            )
        ),
        DeclareLaunchArgument(
            'resource_path',
            default_value='',
            description='Additional Gazebo resource path'
        ),
        DeclareLaunchArgument(
            'model',
            default_value='lite',
            choices=['standard', 'lite'],
            description='TurtleBot 4 model'
        ),
        DeclareLaunchArgument(
            'use_sim_time',
            default_value='true',
            choices=['true', 'false'],
            description='Use simulation time'
        ),
        DeclareLaunchArgument(
            'localization',
            default_value='false',
            choices=['true', 'false'],
            description='Launch localization'
        ),
        DeclareLaunchArgument(
            'slam',
            default_value='false',
            choices=['true', 'false'],
            description='Launch SLAM'
        ),
        DeclareLaunchArgument(
            'nav2',
            default_value='false',
            choices=['true', 'false'],
            description='Launch Nav2'
        ),
        DeclareLaunchArgument(
            'rviz',
            default_value='true',
            choices=['true', 'false'],
            description='Launch RViz'
        ),
        DeclareLaunchArgument(
            'rviz_delay',
            default_value='5.0',
            description='Delay before starting RViz, in seconds'
        ),
        DeclareLaunchArgument(
            'gazebo_gui',
            default_value='true',
            choices=['true', 'false'],
            description='Launch the Gazebo graphical client'
        ),
        DeclareLaunchArgument(
            'map',
            default_value=default_map,
            description='Map YAML file used for localization'
        ),
    ]
    for pose_element in ['x', 'y', 'z', 'yaw']:
        arguments.append(
            DeclareLaunchArgument(
                pose_element,
                default_value='0.0',
                description=f'{pose_element} component of robot spawn pose'
            )
        )

    # Resolve the user-facing world argument before starting Gazebo or spawning
    # the robot.  The lower-level launch files continue to receive the full SDF
    # path and the actual Gazebo world name they expect.
    world_resolver = OpaqueFunction(
        function=resolve_world_arguments,
        args=[pkg_tb4_gz],
    )

    # Start Gazebo.
    simulator = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([sim_launch]),
        launch_arguments={
            'world': LaunchConfiguration('resolved_world'),
            'resource_path': LaunchConfiguration('resource_path'),
            'model': LaunchConfiguration('model'),
            'use_sim_time': LaunchConfiguration('use_sim_time'),
            'gazebo_gui': LaunchConfiguration('gazebo_gui'),
        }.items()
    )
    # Spawn the TurtleBot and optionally start navigation components.
    robot = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([spawn_launch]),
        launch_arguments={
            'namespace': LaunchConfiguration('namespace'),
            'model': LaunchConfiguration('model'),
            'world': LaunchConfiguration('resolved_world_name'),
            'x': LaunchConfiguration('x'),
            'y': LaunchConfiguration('y'),
            'z': LaunchConfiguration('z'),
            'yaw': LaunchConfiguration('yaw'),
            'map': LaunchConfiguration('map'),
            'localization': LaunchConfiguration('localization'),
            'slam': LaunchConfiguration('slam'),
            'nav2': LaunchConfiguration('nav2'),
            'rviz': LaunchConfiguration('rviz'),
            'rviz_delay': LaunchConfiguration('rviz_delay'),
            'use_sim_time': LaunchConfiguration('use_sim_time'),
        }.items()
    )
    ld = LaunchDescription(arguments)
    ld.add_action(world_resolver)
    ld.add_action(simulator)
    ld.add_action(robot)

    return ld
