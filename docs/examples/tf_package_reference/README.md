# TF package reference

This directory is a **worked reference**, not a starter/template repository.
Students should create their own package with the standard ROS 2 command:

```bash
cd ~/rosdev/src
ros2 pkg create --build-type ament_python \
    --license Apache-2.0 \
    --dependencies rclpy tf2_ros sensor_msgs \
    my_robot_package
```

The important ideas illustrated here are:

- use relative topic names in Python (`scan`, not `/robotsim1/scan`)
- use unqualified course-facing TF frames (`base_link`, `rplidar_link`)
- put the node in `ROBOT_NAMESPACE` in the launch file
- remap `/tf -> tf` and `/tf_static -> tf_static` in the launch file
- install launch files through `setup.py`
