#!/usr/bin/env python3
"""
Generate the stock TurtleBot 4 URDF with JMU simulator camera settings.

Leaves /opt/ros untouched.  Runs the installed TurtleBot 4 xacro, changes
existing Gazebo sensor rates, and adds a separate high-resolution RGB sensor
alongside the original RGBD sensor (which still serves preview and depth).
The resulting robot_description XML is written to stdout.
"""

import argparse
import copy
import subprocess
import sys
import xml.etree.ElementTree as ET


HD_SENSOR_NAME = "rgb_camera_hd"


def find_sensor(root, name: str) -> ET.Element:
    matches = [
        sensor for sensor in root.iter("sensor")
        if sensor.get("name") == name
    ]
    if len(matches) != 1:
        raise RuntimeError(
            f"Expected exactly one <sensor name='{name}'>, found {len(matches)}"
        )
    return matches[0]


def set_sensor_rate(root, sensor_name: str, rate: float) -> None:
    sensor = find_sensor(root, sensor_name)
    update_rate = sensor.find("update_rate")
    if update_rate is None:
        raise RuntimeError(
            f"Sensor '{sensor_name}' has no <update_rate> element"
        )
    update_rate.text = f"{rate:g}"


def add_hd_rgb_camera(root, width: int, height: int, rate: float) -> None:
    """Clone the RGBD camera's pose/optics, but not its depth stream.

    Both sensors belong to the same <gazebo reference='oakd_rgb_camera_frame'>
    element.  Gazebo then assigns the HD sensor its own standard image and
    camera_info topic paths based on its distinct sensor name.
    """
    original = find_sensor(root, "rgbd_camera")
    if any(s.get("name") == HD_SENSOR_NAME for s in root.iter("sensor")):
        raise RuntimeError(f"Sensor '{HD_SENSOR_NAME}' already exists")

    parent = next((elem for elem in root.iter() if original in elem), None)
    if (
        parent is None
        or parent.tag != "gazebo"
        or parent.get("reference") != "oakd_rgb_camera_frame"
    ):
        raise RuntimeError(
            "Expected the RGBD sensor under <gazebo reference='oakd_rgb_camera_frame'>"
        )

    hd = copy.deepcopy(original)
    hd.set("name", HD_SENSOR_NAME)
    hd.set("type", "camera")  # Standard RGB camera: no duplicate depth/point-cloud output.

    image = hd.find("./camera/image")
    if image is None:
        raise RuntimeError("RGBD sensor has no <camera><image> definition")
    for tag, value in (("width", width), ("height", height)):
        item = image.find(tag)
        if item is None:
            raise RuntimeError(f"RGBD sensor has no <image><{tag}> element")
        item.text = str(value)

    update_rate = hd.find("update_rate")
    if update_rate is None:
        raise RuntimeError("RGBD sensor has no <update_rate> element")
    update_rate.text = f"{rate:g}"

    visualize = hd.find("visualize")
    if visualize is not None:
        visualize.text = "false"  # Don't open another Gazebo camera visualization.

    parent.append(hd)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--xacro", required=True)
    parser.add_argument("--namespace", required=True)
    parser.add_argument("--lidar-rate", type=float, default=8.0)
    parser.add_argument("--camera-rate", type=float, default=10.0)
    parser.add_argument("--hd-width", type=int, default=1280)
    parser.add_argument("--hd-height", type=int, default=720)
    parser.add_argument("--hd-camera-rate", type=float, default=10.0)
    args = parser.parse_args()

    if args.hd_width <= 0 or args.hd_height <= 0 or args.hd_camera_rate <= 0:
        parser.error("HD camera width, height, and rate must all be positive")

    cmd = [
        "xacro",
        args.xacro,
        "gazebo:=ignition",
        f"namespace:={args.namespace}",
    ]

    result = subprocess.run(
        cmd,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    root = ET.fromstring(result.stdout)
    set_sensor_rate(root, "rplidar", args.lidar_rate)
    set_sensor_rate(root, "rgbd_camera", args.camera_rate)
    add_hd_rgb_camera(root, args.hd_width, args.hd_height, args.hd_camera_rate)

    sys.stdout.write(ET.tostring(root, encoding="unicode"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
