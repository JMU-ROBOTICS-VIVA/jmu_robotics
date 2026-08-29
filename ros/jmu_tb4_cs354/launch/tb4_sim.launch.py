from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import EnvironmentVariable, LaunchConfiguration, PathJoinSubstitution


def generate_launch_description():
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

    # Default stock TurtleBot world
    default_world = PathJoinSubstitution([
        pkg_tb4_gz,
        'worlds',
        'warehouse.sdf'
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

    # Spawn the TurtleBot and optionally start navigation components.
    robot = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([spawn_launch]),
        launch_arguments={
            'namespace': LaunchConfiguration('namespace'),
            'model': LaunchConfiguration('model'),
            'world': LaunchConfiguration('world_name'),
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
    ld.add_action(simulator)
    ld.add_action(robot)

    return ld
