# JMU TurtleBot 4 Bringup

This package contains JMU-specific TurtleBot 4 bringup customizations used by the robotics lab.

The goal is to keep the standard ROS 2 Jazzy TurtleBot packages installed from Debian unchanged while placing JMU-specific behavior in a small overlay package that can be version controlled and redeployed consistently.

## Why this package exists

The stock TurtleBot 4 Jazzy configuration does not match the needs of the JMU robotics lab in several areas:

1. The Create 3 `hazard_detection` topic is not republished by default when using the TurtleBot 4 discovery-server configuration.
2. The stock TurtleBot power saver stops the LiDAR and camera while docked. We disable the stock power saver and manage the LiDAR explicitly.
3. The RPLIDAR `start_motor` service is not safe to call repeatedly while the scanner is already running. Doing so can cause the RPLIDAR ROS process to exit with an error such as:

   ```text
   Cannot start scan: '80008000'
   Failed to set scan mode
   ```

4. The OAK-D camera startup is delayed to reduce the chance of a large USB/power spike during robot startup.

## Files

### `config/republisher.yaml`

JMU copy of the Create 3 republisher configuration.

The important change is that the following publisher is enabled:

```yaml
"hazard_detection", "irobot_create_msgs/msg/HazardDetectionVector",
```

This exposes the Create 3 hazard information as:

```text
/robotN/hazard_detection
```

while leaving the Create 3 itself in its private namespace:

```text
/robotN/_do_not_use
```

The Debian-owned file under `/opt/ros/jazzy` should not be edited.

### `config/turtlebot4.yaml`

JMU TurtleBot parameters.

The stock TurtleBot power saver is disabled:

```yaml
power_saver: false
```

JMU manages the LiDAR dock/undock behavior explicitly instead of allowing both the stock power saver and the JMU node to control the same RPLIDAR services.

### `launch/lite.launch.py`

JMU TurtleBot 4 Lite launch file.

It is based on the upstream TurtleBot 4 Lite launch behavior but adds the JMU-specific configuration:

- uses the JMU `turtlebot4.yaml`
- passes the JMU `republisher.yaml` to the stock `robot.launch.py`
- launches the JMU `lidar_power` node
- uses the JMU OAK-D Lite configuration
- delays OAK-D startup

Because this file follows upstream TurtleBot launch behavior, it should be reviewed when the TurtleBot 4 Jazzy packages receive significant updates.

### `scripts/lidar_power.py`

Controls the RPLIDAR motor based on Create 3 dock state.

The RPLIDAR driver automatically starts the scanner when the driver launches. Therefore, the JMU controller must not call `start_motor` simply because it receives an "undocked" status.

The node tracks whether **it** previously stopped the LiDAR:

```python
self.lidar_stopped_by_us = False
```

Behavior:

```text
Robot boots undocked
    RPLIDAR starts normally
    JMU lidar_power does nothing

Robot docks
    JMU lidar_power calls stop_motor
    lidar_stopped_by_us = True

Robot undocks
    JMU lidar_power calls start_motor
    lidar_stopped_by_us = False
```

This avoids issuing a second `start_motor` request to an already-running RPLIDAR.

## Building and installing

Run the included installer from the repository checkout:

```bash
cd ~/jmu_robotics/ros/jmu_tb4_bringup
./install.sh
```

The installer:

1. sources ROS 2 Jazzy
2. builds only `jmu_tb4_bringup`
3. uses a temporary build/install tree
4. installs the resulting overlay into:

   ```text
   /opt/jmu/turtlebot4/ros
   ```

5. does **not** restart services or reboot automatically

After installation, reboot the robot:

```bash
sudo reboot
```

## Verification

Replace `robot3` below with the appropriate robot namespace.

### Verify LiDAR

```bash
ros2 topic info /robot3/scan
ros2 topic hz /robot3/scan
```

The scan topic should have a publisher and should publish at the normal RPLIDAR rate.

### Verify hazard detection

```bash
ros2 topic info /robot3/hazard_detection
ros2 topic echo /robot3/hazard_detection
```

The topic should have a publisher. Pressing the Create 3 bumper should produce a hazard message.

The physical Create 3 publishes hazard information when the hazard state changes. This differs from the Create 3 Gazebo simulator, which currently publishes `hazard_detection` periodically at approximately 62 Hz. JMU intentionally does not maintain a copied simulator launch stack only to change this upstream behavior.

Student code therefore must not assume that one physical collision results in exactly one subscriber callback.

### Verify dock/undock LiDAR behavior

Monitor the TurtleBot service:

```bash
sudo journalctl -u turtlebot4.service -f
```

Then test:

```text
undocked:
    LiDAR running

dock:
    "Robot docked: stopping LiDAR."
    LiDAR stops

undock:
    "Robot undocked: starting LiDAR."
    LiDAR starts
    /robotN/scan resumes
```

Repeated dock/undock cycles should not produce:

```text
Cannot start scan: '80008000'
```

## Important maintenance rule

Do not make persistent JMU configuration changes directly under:

```text
/opt/ros/jazzy
```

Those files are owned by Debian packages and may be overwritten by package upgrades or reinstalls.

JMU-specific changes should live in this repository and be deployed through the overlay under:

```text
/opt/jmu/turtlebot4/ros
```

## Related simulator configuration

The CS354 simulator launch file also checks that the simulator is running in the expected ROS domain.

The simulator should use:

```bash
ROS_DOMAIN_ID=0
```

The physical TurtleBot lab uses a different ROS domain. The guard prevents the simulator from starting in the wrong domain and then appearing partially broken.
