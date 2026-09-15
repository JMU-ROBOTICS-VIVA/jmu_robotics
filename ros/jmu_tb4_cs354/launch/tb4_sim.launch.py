import os
import re
import subprocess

from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    GroupAction,
    IncludeLaunchDescription,
    OpaqueFunction,
    SetLaunchConfiguration,
    TimerAction,
)
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import (
    EnvironmentVariable,
    LaunchConfiguration,
    PathJoinSubstitution,
    PythonExpression,
)
from launch_ros.actions import Node, PushRosNamespace, SetRemap
from launch_ros.parameter_descriptions import ParameterValue


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


def find_gazebo_sim_processes():
    """Return running Gazebo Sim processes that could conflict with a new sim."""
    try:
        result = subprocess.run(
            ['ps', '-eo', 'pid=,comm=,args='],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise RuntimeError(
            'Unable to check for an existing Gazebo simulation before launch. '
            'Refusing to start the simulator.\n'
            f'Details: {exc}'
        ) from exc

    matches = []
    gz_sim_command = re.compile(r'(?:^|[\s/])gz\s+sim(?:\s|$)')

    for line in result.stdout.splitlines():
        fields = line.strip().split(None, 2)
        if len(fields) < 3:
            continue

        pid, command, args = fields
        if (
            command in {'gz-sim-server', 'gz-sim-gui'}
            or gz_sim_command.search(args)
        ):
            matches.append((pid, args))

    return matches


def check_no_existing_gazebo_sim():
    processes = find_gazebo_sim_processes()
    if not processes:
        return

    process_text = '\n'.join(
        f'  PID {pid}: {args}' for pid, args in processes
    )
    raise RuntimeError(
        '\n\n'
        '============================================================\n'
        'JMU TurtleBot 4 simulator startup blocked\n'
        '============================================================\n'
        'An existing Gazebo simulation process is still running.\n'
        'Starting another simulator could connect to or conflict with the\n'
        'existing Gazebo server.\n\n'
        f'{process_text}\n\n'
        'Run:\n'
        '  ros_tb4_cleanup.sh\n\n'
        'Then launch the simulator again.\n'
        '============================================================\n'
    )


def enable_map_when_localizing(context):
    """Localization always requires a map, so make map mode implicit."""
    localization_enabled = (
        LaunchConfiguration('localization').perform(context).lower() == 'true'
    )

    if localization_enabled:
        return [SetLaunchConfiguration('map', 'true')]

    return []


def generate_launch_description():
    check_ros_domain_id()
    check_no_existing_gazebo_sim()

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

    # Map-oriented RViz configuration used only when map:=true.
    map_rviz_config = PathJoinSubstitution([
        pkg_jmu_tb4,
        'rviz',
        'map.rviz'
    ])

    # Default stock TurtleBot world
    default_world = PathJoinSubstitution([
        pkg_tb4_gz,
        'worlds',
        'warehouse.sdf'
    ])

    # Default map for localization or the lightweight teaching map mode.
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
            default_value=default_world,
            description='Full path to the Gazebo SDF world file'
        ),
        DeclareLaunchArgument(
            'world_name',
            default_value='warehouse',
            description='Name of the world inside the SDF file'
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
            default_value='false',
            choices=['true', 'false'],
            description=(
                'Launch lightweight map teaching mode: map_server, an identity '
                'map->odom transform, and RViz configured to display the map'
            )
        ),
        DeclareLaunchArgument(
            'map_yaml',
            default_value=default_map,
            description='Map YAML file used by map mode or localization'
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

    # Localization always works against a map. Promote map:=true before any
    # map/RViz conditions are evaluated. The lightweight standalone map_server
    # remains suppressed while localization is active; localization owns it.
    configure_map_for_localization = OpaqueFunction(
        function=enable_map_when_localizing
    )

    # Start Gazebo.
    simulator = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([sim_launch]),
        launch_arguments={
            'world': LaunchConfiguration('world'),
            'resource_path': LaunchConfiguration('resource_path'),
            'model': LaunchConfiguration('model'),
            'use_sim_time': LaunchConfiguration('use_sim_time'),
            'gazebo_gui': LaunchConfiguration('gazebo_gui'),
        }.items()
    )

    # When map mode is active, tb4_sim.launch.py launches the map-oriented RViz
    # instance below. Suppress spawn.launch.py's normal base_link RViz instance
    # so that we do not start two copies of RViz.
    # Evaluate this in the parent context before entering the scoped spawn
    # include. That matters because spawn.launch.py itself uses the name 'map'
    # for the YAML filename.
    configure_spawn_rviz = SetLaunchConfiguration(
        'spawn_rviz',
        PythonExpression([
            "'true' if ('", LaunchConfiguration('rviz'), "' == 'true' and '",
            LaunchConfiguration('map'), "' == 'false') else 'false'"
        ])
    )

    # Spawn the TurtleBot and optionally start navigation components.
    # Keep the include scoped because spawn.launch.py also has a launch argument
    # named 'map'. Inside that scope it receives the YAML filename; outside the
    # scope our top-level 'map' argument remains the boolean teaching-mode flag.
    robot = GroupAction(
        scoped=True,
        actions=[
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource([spawn_launch]),
                launch_arguments={
                    'namespace': LaunchConfiguration('namespace'),
                    'model': LaunchConfiguration('model'),
                    'world': LaunchConfiguration('world_name'),
                    'x': LaunchConfiguration('x'),
                    'y': LaunchConfiguration('y'),
                    'z': LaunchConfiguration('z'),
                    'yaw': LaunchConfiguration('yaw'),
                    'map': LaunchConfiguration('map_yaml'),
                    'localization': LaunchConfiguration('localization'),
                    'slam': LaunchConfiguration('slam'),
                    'nav2': LaunchConfiguration('nav2'),
                    'rviz': LaunchConfiguration('spawn_rviz'),
                    'rviz_delay': LaunchConfiguration('rviz_delay'),
                    'use_sim_time': LaunchConfiguration('use_sim_time'),
                }.items()
            )
        ]
    )

    # Lightweight teaching map mode. If localization or SLAM is explicitly
    # requested, do not publish our static map->odom transform or launch this
    # standalone map_server because those stacks own map localization/mapping.
    lightweight_map_condition = IfCondition(PythonExpression([
        "'", LaunchConfiguration('map'), "' == 'true' and '",
        LaunchConfiguration('localization'), "' == 'false' and '",
        LaunchConfiguration('slam'), "' == 'false'"
    ]))

    map_support = GroupAction(
        scoped=True,
        condition=lightweight_map_condition,
        actions=[
            PushRosNamespace(LaunchConfiguration('namespace')),
            SetRemap(src='/tf', dst='tf'),
            SetRemap(src='/tf_static', dst='tf_static'),
            Node(
                package='nav2_map_server',
                executable='map_server',
                name='map_server',
                output='screen',
                parameters=[{
                    'use_sim_time': LaunchConfiguration('use_sim_time'),
                    'yaml_filename': ParameterValue(
                        LaunchConfiguration('map_yaml'),
                        value_type=str,
                    ),
                }],
            ),
            Node(
                package='nav2_lifecycle_manager',
                executable='lifecycle_manager',
                name='lifecycle_manager_map',
                output='screen',
                parameters=[{
                    'use_sim_time': LaunchConfiguration('use_sim_time'),
                    'autostart': True,
                    'node_names': ['map_server'],
                }],
            ),
            Node(
                package='tf2_ros',
                executable='static_transform_publisher',
                name='map_to_odom_static_tf',
                output='screen',
                arguments=[
                    '--x', '0.0',
                    '--y', '0.0',
                    '--z', '0.0',
                    '--roll', '0.0',
                    '--pitch', '0.0',
                    '--yaw', '0.0',
                    '--frame-id', 'map',
                    '--child-frame-id', 'odom',
                ],
            ),
        ]
    )

    # In map mode, start RViz already configured with Fixed Frame=map and an
    # enabled Map display using Transient Local durability on the relative
    # topic 'map' (which resolves to /<namespace>/map).
    map_rviz_condition = IfCondition(PythonExpression([
        "'", LaunchConfiguration('map'), "' == 'true' and '",
        LaunchConfiguration('rviz'), "' == 'true'"
    ]))

    map_rviz = TimerAction(
        period=LaunchConfiguration('rviz_delay'),
        actions=[
            GroupAction(
                scoped=True,
                condition=map_rviz_condition,
                actions=[
                    PushRosNamespace(LaunchConfiguration('namespace')),
                    SetRemap(src='/tf', dst='tf'),
                    SetRemap(src='/tf_static', dst='tf_static'),
                    Node(
                        package='rviz2',
                        executable='rviz2',
                        name='rviz2',
                        output='screen',
                        arguments=['-d', map_rviz_config],
                        parameters=[{
                            'use_sim_time': LaunchConfiguration('use_sim_time')
                        }],
                    ),
                ]
            )
        ]
    )

    ld = LaunchDescription(arguments)
    ld.add_action(configure_map_for_localization)
    ld.add_action(simulator)
    ld.add_action(configure_spawn_rviz)
    ld.add_action(robot)
    ld.add_action(map_support)
    ld.add_action(map_rviz)

    return ld
