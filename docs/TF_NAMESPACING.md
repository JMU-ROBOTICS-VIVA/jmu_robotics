# CS 354 ROS Namespaces and TF

## Course rule

Robot identity belongs in the ROS namespace, not in student code.

Student programs should use relative topic names such as:

```text
scan
odom
cmd_vel
hazard_detection
```

Do not hard-code names such as `/robotsim1/scan` or `/robot3/scan`.

Likewise, student code should use the course-facing TF frame names:

```text
map
odom
base_link
rplidar_link
```

Simulator-specific frames containing names such as `robotsim1/...` are implementation details and should not be used by student programs.

## Why TF needs one extra launch-file step

Many tf2 nodes use the absolute ROS topic names `/tf` and `/tf_static`. Absolute names ignore the node namespace. A launch file for a robot-facing node should therefore remap those names to the relative names `tf` and `tf_static` while placing the node in the selected robot namespace.

```python
GroupAction([
    PushRosNamespace(EnvironmentVariable('ROBOT_NAMESPACE')),
    SetRemap(src='/tf', dst='tf'),
    SetRemap(src='/tf_static', dst='tf_static'),
    Node(
        package='my_package',
        executable='my_node',
    ),
])
```

If `ROBOT_NAMESPACE=/robotsim1`, `tf` resolves to `/robotsim1/tf`. If `ROBOT_NAMESPACE=/robot3`, the exact same launch file uses `/robot3/tf`.

## Command-line helpers

After selecting one robot with `tb4-select`:

```bash
tb4-tf odom base_link
tb4-tf base_link rplidar_link
tb4-tf-tree
```

The helpers only hide the topic remapping needed by tf2 command-line tools. They do not modify TF frame names.

## Creating a student package

Students should continue to create packages with the standard ROS 2 command rather than cloning a course template package. For example:

```bash
cd ~/rosdev/src
ros2 pkg create --build-type ament_python \
    --license Apache-2.0 \
    --dependencies rclpy tf2_ros sensor_msgs \
    my_robot_package
```

Then add the node and launch file needed by the assignment. The `docs/examples/tf_package_reference` directory is a worked reference showing the resulting structure and TF remapping pattern; it is not intended to be copied as a starter repository.
