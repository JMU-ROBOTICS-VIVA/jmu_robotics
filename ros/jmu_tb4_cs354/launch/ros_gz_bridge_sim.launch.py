# Copyright 2023 Clearpath Robotics, Inc.
# Copyright 2026 James Madison University
#
# Derived from turtlebot4_gz_bringup/launch/ros_gz_bridge.launch.py (Apache-2.0).
#
# JMU changes:
#   * depth image -> oakd/stereo/image_raw
#   * duplicate Gazebo camera_info -> oakd/stereo/camera_info
#   * do not bridge the simulator-only PointCloud2 stream
#   * lazily publish oakd/rgb/preview/image_raw/compressed using image_transport

from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import EqualsSubstitution, LaunchConfiguration
from launch.substitutions.path_join_substitution import PathJoinSubstitution

from launch_ros.actions import ComposableNodeContainer, Node
from launch_ros.descriptions import ComposableNode


ARGUMENTS = [
    DeclareLaunchArgument(
        'use_sim_time',
        default_value='true',
        choices=['true', 'false'],
        description='Use sim time',
    ),
    DeclareLaunchArgument(
        'robot_name',
        default_value='turtlebot4',
        description='Gazebo model name',
    ),
    DeclareLaunchArgument(
        'dock_name',
        default_value='standard_dock',
        description='Gazebo dock model name',
    ),
    DeclareLaunchArgument(
        'namespace',
        default_value='',
        description='Robot namespace',
    ),
    DeclareLaunchArgument(
        'world',
        default_value='warehouse',
        description='World name',
    ),
    DeclareLaunchArgument(
        'model',
        default_value='standard',
        choices=['standard', 'lite'],
        description='TurtleBot 4 model',
    ),
]


def generate_launch_description():
    use_sim_time = LaunchConfiguration('use_sim_time')
    robot_name = LaunchConfiguration('robot_name')
    dock_name = LaunchConfiguration('dock_name')
    namespace = LaunchConfiguration('namespace')
    world = LaunchConfiguration('world')

    leds = [
        'power',
        'motors',
        'comms',
        'wifi',
        'battery',
        'user1',
        'user2',
    ]

    pkg_irobot_create_gz_bringup = get_package_share_directory(
        'irobot_create_gz_bringup'
    )

    create3_ros_gz_bridge_launch = PathJoinSubstitution([
        pkg_irobot_create_gz_bringup,
        'launch',
        'create3_ros_gz_bridge.launch.py',
    ])

    create3_bridge = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([create3_ros_gz_bridge_launch]),
        launch_arguments=[
            ('robot_name', robot_name),
            ('dock_name', dock_name),
            ('namespace', namespace),
            ('world', world),
        ],
    )

    lidar_gz_topic = [
        '/world/', world,
        '/model/', robot_name,
        '/link/rplidar_link/sensor/rplidar/scan',
    ]

    lidar_bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        name='lidar_bridge',
        output='screen',
        parameters=[{'use_sim_time': use_sim_time}],
        arguments=[
            lidar_gz_topic +
            ['@sensor_msgs/msg/LaserScan[gz.msgs.LaserScan']
        ],
        remappings=[
            (lidar_gz_topic, 'scan'),
        ],
    )

    # Standard-model HMI bridges retained from the stock TurtleBot 4 simulator.
    hmi_display_msg_bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        name='hmi_display_msg_bridge',
        output='screen',
        parameters=[{'use_sim_time': use_sim_time}],
        arguments=[
            [namespace, '/hmi/display/raw@std_msgs/msg/String]gz.msgs.StringMsg'],
            [namespace, '/hmi/display/selected@std_msgs/msg/Int32]gz.msgs.Int32'],
        ],
        remappings=[
            ([namespace, '/hmi/display/raw'], 'hmi/display/_raw'),
            ([namespace, '/hmi/display/selected'], 'hmi/display/_selected'),
        ],
        condition=IfCondition(
            EqualsSubstitution(LaunchConfiguration('model'), 'standard')
        ),
    )

    hmi_buttons_msg_bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        name='hmi_buttons_msg_bridge',
        output='screen',
        parameters=[{'use_sim_time': use_sim_time}],
        arguments=[
            [namespace, '/hmi/buttons@std_msgs/msg/Int32[gz.msgs.Int32'],
        ],
        remappings=[
            ([namespace, '/hmi/buttons'], 'hmi/buttons/_set'),
        ],
        condition=IfCondition(
            EqualsSubstitution(LaunchConfiguration('model'), 'standard')
        ),
    )

    hmi_led_msg_bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        name='hmi_led_msg_bridge',
        output='screen',
        parameters=[{'use_sim_time': use_sim_time}],
        arguments=[
            [
                namespace, '/hmi/led/', led,
                '@std_msgs/msg/Int32]gz.msgs.Int32',
            ]
            for led in leds
        ],
        remappings=[
            ([namespace, '/hmi/led/' + led], 'hmi/led/_' + led)
            for led in leds
        ],
        condition=IfCondition(
            EqualsSubstitution(LaunchConfiguration('model'), 'standard')
        ),
    )

    camera_prefix = [
        '/world/', world,
        '/model/', robot_name,
        '/link/oakd_rgb_camera_frame/sensor/rgbd_camera/',
    ]

    rgb_gz_topic = camera_prefix + ['image']
    depth_gz_topic = camera_prefix + ['depth_image']
    info_gz_topic = camera_prefix + ['camera_info']

    # Bridge RGB, depth, and the RGB CameraInfo.
    # Intentionally omit the stock PointCloud2 bridge: the physical JMU
    # interface we are standardizing on is RGB + stereo/depth images.
    oakd_camera_bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        name='camera_bridge',
        output='screen',
        parameters=[{'use_sim_time': use_sim_time}],
        arguments=[
            rgb_gz_topic + ['@sensor_msgs/msg/Image[gz.msgs.Image'],
            depth_gz_topic + ['@sensor_msgs/msg/Image[gz.msgs.Image'],
            info_gz_topic + ['@sensor_msgs/msg/CameraInfo[gz.msgs.CameraInfo'],
        ],
        remappings=[
            (rgb_gz_topic, 'oakd/rgb/preview/image_raw'),
            (depth_gz_topic, 'oakd/stereo/image_raw'),
            (info_gz_topic, 'oakd/rgb/preview/camera_info'),
        ],
    )

    # Gazebo's single RGBD sensor provides one CameraInfo stream.  Publish
    # the same simulated calibration metadata under the physical robot's
    # stereo CameraInfo path as a compatibility approximation.
    oakd_stereo_info_bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        name='stereo_camera_info_bridge',
        output='screen',
        parameters=[{'use_sim_time': use_sim_time}],
        arguments=[
            info_gz_topic + ['@sensor_msgs/msg/CameraInfo[gz.msgs.CameraInfo'],
        ],
        remappings=[
            (info_gz_topic, 'oakd/stereo/camera_info'),
        ],
    )

    # Jazzy image_transport's republisher is a composable component.
    # With out_transport=compressed it only subscribes to the raw stream
    # when something subscribes to the compressed output, avoiding JPEG
    # encoding cost when students are not using the compressed topic.
    rgb_compressed_container = ComposableNodeContainer(
        name='sim_image_transport_container',
        namespace='',
        package='rclcpp_components',
        executable='component_container',
        output='screen',
        composable_node_descriptions=[
            ComposableNode(
                package='image_transport',
                plugin='image_transport::Republisher',
                name='rgb_compressed_republisher',
                parameters=[{
                    'use_sim_time': use_sim_time,
                    'in_transport': 'raw',
                    'out_transport': 'compressed',
                }],
                remappings=[
                    ('in', 'oakd/rgb/preview/image_raw'),
                    ('out/compressed', 'oakd/rgb/preview/image_raw/compressed'),
                ],
            ),
        ],
    )

    ld = LaunchDescription(ARGUMENTS)
    ld.add_action(create3_bridge)
    ld.add_action(hmi_display_msg_bridge)
    ld.add_action(hmi_buttons_msg_bridge)
    ld.add_action(hmi_led_msg_bridge)
    ld.add_action(lidar_bridge)
    ld.add_action(oakd_camera_bridge)
    ld.add_action(oakd_stereo_info_bridge)
    ld.add_action(rgb_compressed_container)
    return ld
