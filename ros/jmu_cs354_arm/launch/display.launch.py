import os

from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription

from launch_ros.actions import Node


def generate_launch_description():

    package_dir = get_package_share_directory('jmu_cs354_arm')

    urdf_file = os.path.join(
        package_dir,
        'urdf',
        'cs354_arm.urdf'
    )

    rviz_config = os.path.join(
        package_dir,
        'rviz',
        'arm.rviz'
    )

    with open(urdf_file, 'r') as f:
        robot_description = f.read()

    return LaunchDescription([

        # Takes the URDF + /joint_states and publishes TF.
        Node(
            package='robot_state_publisher',
            executable='robot_state_publisher',
            name='robot_state_publisher',
            output='screen',
            parameters=[{
                'robot_description': robot_description,
                'use_sim_time': False
            }]
        ),

        # Gives us sliders for shoulder_joint and elbow_joint.
        Node(
            package='joint_state_publisher_gui',
            executable='joint_state_publisher_gui',
            name='joint_state_publisher_gui',
            output='screen',
            parameters=[{
                'source_list': ['/arm_joint_command']
            }]
        ),

        # Visualize the model and coordinate frames.
        Node(
            package='rviz2',
            executable='rviz2',
            name='rviz2',
            arguments=['-d', rviz_config],
            output='screen'
        ),
    ])

