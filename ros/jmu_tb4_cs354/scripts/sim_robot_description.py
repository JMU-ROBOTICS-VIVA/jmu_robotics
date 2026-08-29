#!/usr/bin/env python3
"""
Generate the stock TurtleBot 4 URDF and override only simulator sensor rates.

This deliberately leaves /opt/ros untouched.  It runs the installed TurtleBot 4
xacro, parses the generated URDF, changes the Gazebo sensor update_rate values,
and writes the modified robot_description XML to stdout.
"""

import argparse
import subprocess
import sys
import xml.etree.ElementTree as ET


def set_sensor_rate(root, sensor_name: str, rate: float) -> None:
    matches = [
        sensor for sensor in root.iter("sensor")
        if sensor.get("name") == sensor_name
    ]
    if len(matches) != 1:
        raise RuntimeError(
            f"Expected exactly one <sensor name='{sensor_name}'>, found {len(matches)}"
        )

    update_rate = matches[0].find("update_rate")
    if update_rate is None:
        raise RuntimeError(
            f"Sensor '{sensor_name}' has no <update_rate> element"
        )

    update_rate.text = f"{rate:g}"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--xacro", required=True)
    parser.add_argument("--namespace", required=True)
    parser.add_argument("--lidar-rate", type=float, default=8.0)
    parser.add_argument("--camera-rate", type=float, default=10.0)
    args = parser.parse_args()

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

    sys.stdout.write(ET.tostring(root, encoding="unicode"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
