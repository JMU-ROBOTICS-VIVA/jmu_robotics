from launch import LaunchDescription
from launch.actions import GroupAction
from launch.substitutions import EnvironmentVariable
from launch_ros.actions import Node, PushRosNamespace, SetRemap


def generate_launch_description():
    return LaunchDescription([
        GroupAction([
            PushRosNamespace(
                EnvironmentVariable('ROBOT_NAMESPACE', default_value='')
            ),

            # tf2 uses absolute /tf and /tf_static by default. Make them
            # relative so the selected robot namespace is applied.
            SetRemap(src='/tf', dst='tf'),
            SetRemap(src='/tf_static', dst='tf_static'),

            Node(
                package='tf_package_reference',
                executable='frame_demo',
                output='screen',
            ),
        ]),
    ])
