import os

from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    GroupAction,
    IncludeLaunchDescription,
    LogInfo,
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
from launch_ros.actions import Node, PushRosNamespace
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


def resolve_environment(context, pkg_tb4_gz, pkg_tb4_navigation):
    """Resolve stock world names and instructor overrides to concrete paths."""
    stock_world = LaunchConfiguration('world').perform(context)
    world_file_override = LaunchConfiguration('world_file').perform(context).strip()
    world_name_override = LaunchConfiguration('world_name').perform(context).strip()
    map_yaml_override = LaunchConfiguration('map_yaml').perform(context).strip()

    # Stock environments are intentionally easy for students to select.
    if world_file_override:
        world_file = os.path.abspath(os.path.expanduser(world_file_override))
        world_name = (
            world_name_override
            if world_name_override
            else os.path.splitext(os.path.basename(world_file))[0]
        )
        # For a custom world, never silently pair it with a stock map.  An
        # instructor must provide map_yaml explicitly if a static map is needed.
        map_yaml = (
            os.path.abspath(os.path.expanduser(map_yaml_override))
            if map_yaml_override
            else ''
        )
    else:
        world_file = os.path.join(pkg_tb4_gz, 'worlds', f'{stock_world}.sdf')
        world_name = world_name_override if world_name_override else stock_world
        map_yaml = (
            os.path.abspath(os.path.expanduser(map_yaml_override))
            if map_yaml_override
            else os.path.join(pkg_tb4_navigation, 'maps', f'{stock_world}.yaml')
        )

    if not os.path.isfile(world_file):
        raise RuntimeError(
            f"Gazebo world file does not exist: {world_file}\n"
            f"Selected world: {stock_world}"
        )

    map_enabled = LaunchConfiguration('map').perform(context).lower() == 'true'
    localization_enabled = (
        LaunchConfiguration('localization').perform(context).lower() == 'true'
    )
    slam_enabled = LaunchConfiguration('slam').perform(context).lower() == 'true'
    nav2_enabled = LaunchConfiguration('nav2').perform(context).lower() == 'true'

    # Static-map consumers need a YAML file.  SLAM is the exception because it
    # produces a map rather than loading one.
    needs_static_map = (
        localization_enabled
        or (nav2_enabled and not slam_enabled)
        or (map_enabled and not localization_enabled and not slam_enabled)
    )

    if needs_static_map and not map_yaml:
        raise RuntimeError(
            'This custom Gazebo world requires an explicit map_yaml:=... '
            'when map/localization/static-map navigation is enabled.'
        )
    if needs_static_map and not os.path.isfile(map_yaml):
        raise RuntimeError(
            f"Map YAML file does not exist: {map_yaml}\n"
            f"Selected world: {stock_world}"
        )

    map_description = map_yaml if map_yaml else '(none; not required)'

    return [
        SetLaunchConfiguration('resolved_world_file', world_file),
        SetLaunchConfiguration('resolved_world_name', world_name),
        SetLaunchConfiguration('resolved_map_yaml', map_yaml),
        LogInfo(msg=f'[tb4_sim] Gazebo world: {world_file}'),
        LogInfo(msg=f'[tb4_sim] Gazebo world name: {world_name}'),
        LogInfo(msg=f'[tb4_sim] Occupancy map: {map_description}'),
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

    # Map-oriented RViz configuration used only when map:=true.
    map_rviz_config = PathJoinSubstitution([
        pkg_jmu_tb4,
        'rviz',
        'map.rviz'
    ])

    # The top-level launch accepts a friendly stock world name.  Concrete
    # paths are resolved after launch arguments have been parsed so that
    # world:=maze can automatically select both maze.sdf and maze.yaml.

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
            choices=['warehouse', 'maze', 'depot'],
            description=(
                'Stock TurtleBot 4 environment. Automatically selects the '
                'matching Gazebo SDF and, when needed, occupancy map.'
            )
        ),
        DeclareLaunchArgument(
            'world_file',
            default_value='',
            description=(
                'Optional explicit Gazebo SDF path. Overrides the SDF selected '
                'by world:=warehouse|maze|depot.'
            )
        ),
        DeclareLaunchArgument(
            'world_name',
            default_value='',
            description=(
                'Optional Gazebo world name override. Normally inferred from '
                'the stock world selection; useful with world_file overrides.'
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
            default_value='false',
            choices=['true', 'false'],
            description=(
                'Launch lightweight map teaching mode: map_server, an identity '
                'map->odom transform, and RViz configured to display the map'
            )
        ),
        DeclareLaunchArgument(
            'map_yaml',
            default_value='',
            description=(
                'Optional explicit occupancy-map YAML path. If omitted, the '
                'map matching world:=warehouse|maze|depot is selected.'
            )
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

    resolve_environment_action = OpaqueFunction(
        function=resolve_environment,
        args=[pkg_tb4_gz, pkg_tb4_navigation],
    )

    # Start Gazebo.
    simulator = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([sim_launch]),
        launch_arguments={
            'world': LaunchConfiguration('resolved_world_file'),
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
                    'world': LaunchConfiguration('resolved_world_name'),
                    'x': LaunchConfiguration('x'),
                    'y': LaunchConfiguration('y'),
                    'z': LaunchConfiguration('z'),
                    'yaw': LaunchConfiguration('yaw'),
                    'map': LaunchConfiguration('resolved_map_yaml'),
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
            Node(
                package='nav2_map_server',
                executable='map_server',
                name='map_server',
                output='screen',
                parameters=[{
                    'use_sim_time': LaunchConfiguration('use_sim_time'),
                    'yaml_filename': ParameterValue(
                        LaunchConfiguration('resolved_map_yaml'),
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
                remappings=[
                    ('/tf', 'tf'),
                    ('/tf_static', 'tf_static'),
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
                    Node(
                        package='rviz2',
                        executable='rviz2',
                        name='rviz2',
                        output='screen',
                        arguments=['-d', map_rviz_config],
                        parameters=[{
                            'use_sim_time': LaunchConfiguration('use_sim_time')
                        }],
                        remappings=[
                            ('/tf', 'tf'),
                            ('/tf_static', 'tf_static'),
                        ],
                    ),
                ]
            )
        ]
    )

    ld = LaunchDescription(arguments)
    ld.add_action(resolve_environment_action)
    ld.add_action(simulator)
    ld.add_action(configure_spawn_rviz)
    ld.add_action(robot)
    ld.add_action(map_support)
    ld.add_action(map_rviz)

    return ld
