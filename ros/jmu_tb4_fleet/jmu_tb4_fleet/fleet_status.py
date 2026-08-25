#!/usr/bin/env python3

"""Low-overhead JMU TurtleBot 4 fleet monitor.

Low-rate battery and dock topics are monitored continuously.

High-rate sensor topics (LiDAR and OAK-D CameraInfo) are subscribed only for a
short sampling window immediately before each status snapshot. This avoids
continuously deserializing fleet-wide sensor traffic merely to estimate Hz/FPS.
"""

import argparse
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import sys
import tempfile
import time

import rclpy
from rcl_interfaces.msg import ParameterType
from rcl_interfaces.srv import GetParameters
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy
from rclpy.utilities import remove_ros_args

from irobot_create_msgs.msg import DockStatus
from sensor_msgs.msg import BatteryState, CameraInfo, LaserScan


OAK_PARAMETER_NAMES = [
    "camera.i_pipeline_type",
    "rgb.i_fps",
    "stereo.i_fps",
    "left.i_fps",
    "right.i_fps",
]

BATTERY_STATUS = {
    BatteryState.POWER_SUPPLY_STATUS_UNKNOWN: "unknown",
    BatteryState.POWER_SUPPLY_STATUS_CHARGING: "charging",
    BatteryState.POWER_SUPPLY_STATUS_DISCHARGING: "discharging",
    BatteryState.POWER_SUPPLY_STATUS_NOT_CHARGING: "not_charging",
    BatteryState.POWER_SUPPLY_STATUS_FULL: "full",
}

BATTERY_HEALTH = {
    BatteryState.POWER_SUPPLY_HEALTH_UNKNOWN: "unknown",
    BatteryState.POWER_SUPPLY_HEALTH_GOOD: "good",
    BatteryState.POWER_SUPPLY_HEALTH_OVERHEAT: "overheat",
    BatteryState.POWER_SUPPLY_HEALTH_DEAD: "dead",
    BatteryState.POWER_SUPPLY_HEALTH_OVERVOLTAGE: "overvoltage",
    BatteryState.POWER_SUPPLY_HEALTH_UNSPEC_FAILURE: "unspecified_failure",
    BatteryState.POWER_SUPPLY_HEALTH_COLD: "cold",
    BatteryState.POWER_SUPPLY_HEALTH_WATCHDOG_TIMER_EXPIRE: "watchdog_timer_expired",
    BatteryState.POWER_SUPPLY_HEALTH_SAFETY_TIMER_EXPIRE: "safety_timer_expired",
}


def utc_now_string():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def finite_or_none(value):
    value = float(value)
    return value if math.isfinite(value) else None


def parameter_value_to_python(value):
    t = value.type
    if t == ParameterType.PARAMETER_NOT_SET:
        return None
    if t == ParameterType.PARAMETER_BOOL:
        return bool(value.bool_value)
    if t == ParameterType.PARAMETER_INTEGER:
        return int(value.integer_value)
    if t == ParameterType.PARAMETER_DOUBLE:
        return float(value.double_value)
    if t == ParameterType.PARAMETER_STRING:
        return str(value.string_value)
    if t == ParameterType.PARAMETER_BYTE_ARRAY:
        return list(value.byte_array_value)
    if t == ParameterType.PARAMETER_BOOL_ARRAY:
        return list(value.bool_array_value)
    if t == ParameterType.PARAMETER_INTEGER_ARRAY:
        return list(value.integer_array_value)
    if t == ParameterType.PARAMETER_DOUBLE_ARRAY:
        return list(value.double_array_value)
    if t == ParameterType.PARAMETER_STRING_ARRAY:
        return list(value.string_array_value)
    return None


def expected_depth_fps(params):
    stereo = params.get("stereo.i_fps")
    if isinstance(stereo, (int, float)) and stereo > 0:
        return float(stereo)

    mono = [
        float(params[name])
        for name in ("left.i_fps", "right.i_fps")
        if isinstance(params.get(name), (int, float)) and params[name] > 0
    ]
    return min(mono) if mono else None


def stream_health(expected, observed):
    if expected is None:
        return "unknown"
    if observed is None:
        return "waiting"
    if observed <= 0.0:
        return "failed"
    if expected > 0 and observed / expected < 0.80:
        return "warning"
    return "ok"


class SampleCounter:
    """Measure arrival frequency during one finite sample window."""

    def __init__(self):
        self.clear()

    def clear(self):
        self.count = 0
        self.first = None
        self.last = None

    def tick(self, now):
        if self.first is None:
            self.first = now
        self.last = now
        self.count += 1

    def rate(self):
        if self.count < 2 or self.first is None or self.last is None:
            return 0.0 if self.count else None
        elapsed = self.last - self.first
        if elapsed <= 0:
            return 0.0
        return round((self.count - 1) / elapsed, 2)


class FleetStatus(Node):
    def __init__(
        self,
        robots,
        output_path,
        write_interval,
        stale_seconds,
        sample_window,
        parameter_interval,
        stdout,
    ):
        super().__init__("jmu_tb4_fleet_status")

        self.robots = list(robots)
        self.output_path = Path(output_path)
        self.write_interval = write_interval
        self.stale_seconds = stale_seconds
        self.sample_window = sample_window
        self.parameter_interval = parameter_interval
        self.stdout = stdout

        self.sensor_qos = QoSProfile(
            depth=10,
            reliability=ReliabilityPolicy.BEST_EFFORT,
            durability=DurabilityPolicy.VOLATILE,
        )

        self.state = {}
        self.sample_subscriptions = []
        self.sampling = False
        self.sample_end = None
        self.next_write = None

        for robot in self.robots:
            ns = f"/robot{robot}"
            self.state[robot] = {
                "robot": robot,
                "hostname": f"tb{robot}.cs.jmu.edu",
                "namespace": ns,
                "last_seen_monotonic": None,
                "last_seen": None,
                "battery": None,
                "dock": None,
                "sample_counters": {
                    name: SampleCounter()
                    for name in ("scan", "rgb", "depth")
                },
                "sample_rates": {
                    "scan": None,
                    "rgb": None,
                    "depth": None,
                },
                "sampled_at": None,
                "oak_parameters": {},
                "oak_parameters_last_read": None,
                "oak_parameter_query_pending": False,
            }

            # Low-rate topics stay subscribed continuously.
            self.create_subscription(
                BatteryState,
                f"{ns}/battery_state",
                lambda msg, r=robot: self._battery_callback(r, msg),
                self.sensor_qos,
            )
            self.create_subscription(
                DockStatus,
                f"{ns}/dock_status",
                lambda msg, r=robot: self._dock_callback(r, msg),
                self.sensor_qos,
            )

            client = self.create_client(GetParameters, f"{ns}/oakd/get_parameters")
            self.state[robot]["oak_parameter_client"] = client

        self.create_timer(self.parameter_interval, self._query_oak_parameters)

        # Lightweight state-machine timer; no high-rate subscriptions exist
        # outside the finite sample window.
        self.create_timer(0.5, self._scheduler_tick)

        self.get_logger().info(
            "Monitoring TurtleBots: " + ", ".join(str(r) for r in self.robots)
        )
        self.get_logger().info(f"Writing status to: {self.output_path}")
        self.get_logger().info(
            f"Snapshot interval: {self.write_interval:.1f}s; "
            f"sensor sample window: {self.sample_window:.1f}s"
        )

        self._query_oak_parameters()

        # Produce the first useful snapshot quickly: sample now for one window.
        now = time.monotonic()
        self.next_write = now + self.sample_window
        self._begin_sensor_sample(now)

    def _mark_seen(self, robot):
        self.state[robot]["last_seen_monotonic"] = time.monotonic()
        self.state[robot]["last_seen"] = utc_now_string()

    def _battery_callback(self, robot, msg):
        self._mark_seen(robot)

        percentage = finite_or_none(msg.percentage)
        if percentage is not None:
            percentage *= 100.0

        self.state[robot]["battery"] = {
            "percentage": None if percentage is None else round(percentage, 1),
            "voltage_v": finite_or_none(msg.voltage),
            "current_a": finite_or_none(msg.current),
            "charge_ah": finite_or_none(msg.charge),
            "capacity_ah": finite_or_none(msg.capacity),
            "design_capacity_ah": finite_or_none(msg.design_capacity),
            "status": BATTERY_STATUS.get(msg.power_supply_status, "unknown"),
            "health": BATTERY_HEALTH.get(msg.power_supply_health, "unknown"),
            "present": bool(msg.present),
        }

    def _dock_callback(self, robot, msg):
        self._mark_seen(robot)
        self.state[robot]["dock"] = {
            "is_docked": bool(msg.is_docked),
            "dock_visible": bool(msg.dock_visible),
        }

    def _sample_callback(self, robot, stream):
        now = time.monotonic()
        self._mark_seen(robot)
        self.state[robot]["sample_counters"][stream].tick(now)

    def _begin_sensor_sample(self, now=None):
        if self.sampling:
            return

        now = time.monotonic() if now is None else now

        for robot in self.robots:
            for counter in self.state[robot]["sample_counters"].values():
                counter.clear()

        for robot in self.robots:
            ns = f"/robot{robot}"

            self.sample_subscriptions.append(
                self.create_subscription(
                    LaserScan,
                    f"{ns}/scan",
                    lambda msg, r=robot: self._sample_callback(r, "scan"),
                    self.sensor_qos,
                )
            )
            self.sample_subscriptions.append(
                self.create_subscription(
                    CameraInfo,
                    f"{ns}/oakd/rgb/preview/camera_info",
                    lambda msg, r=robot: self._sample_callback(r, "rgb"),
                    self.sensor_qos,
                )
            )
            self.sample_subscriptions.append(
                self.create_subscription(
                    CameraInfo,
                    f"{ns}/oakd/stereo/camera_info",
                    lambda msg, r=robot: self._sample_callback(r, "depth"),
                    self.sensor_qos,
                )
            )

        self.sampling = True
        self.sample_end = now + self.sample_window

    def _finish_sensor_sample(self):
        sampled_at = utc_now_string()

        for robot in self.robots:
            state = self.state[robot]
            for stream, counter in state["sample_counters"].items():
                state["sample_rates"][stream] = counter.rate()
            state["sampled_at"] = sampled_at

        for subscription in self.sample_subscriptions:
            self.destroy_subscription(subscription)

        self.sample_subscriptions.clear()
        self.sampling = False
        self.sample_end = None

    def _scheduler_tick(self):
        now = time.monotonic()

        if self.sampling:
            if now >= self.sample_end:
                self._finish_sensor_sample()
                self._write_status()
                self.next_write = now + self.write_interval
            return

        # Begin the next sample so it ends at approximately next_write.
        if self.next_write is None:
            self.next_write = now + self.write_interval

        if now >= self.next_write - self.sample_window:
            self._begin_sensor_sample(now)

    def _query_oak_parameters(self):
        for robot in self.robots:
            state = self.state[robot]
            if state["oak_parameter_query_pending"]:
                continue

            client = state["oak_parameter_client"]
            if not client.service_is_ready():
                continue

            request = GetParameters.Request()
            request.names = OAK_PARAMETER_NAMES
            state["oak_parameter_query_pending"] = True

            future = client.call_async(request)
            future.add_done_callback(
                lambda f, r=robot: self._oak_parameters_done(r, f)
            )

    def _oak_parameters_done(self, robot, future):
        state = self.state[robot]
        state["oak_parameter_query_pending"] = False

        try:
            response = future.result()
            state["oak_parameters"] = {
                name: parameter_value_to_python(value)
                for name, value in zip(OAK_PARAMETER_NAMES, response.values)
            }
            state["oak_parameters_last_read"] = utc_now_string()
        except Exception as exc:
            self.get_logger().debug(
                f"Could not read OAK-D parameters from robot {robot}: {exc}"
            )

    def _document(self):
        now_mono = time.monotonic()
        robots = []

        for robot in self.robots:
            state = self.state[robot]
            last = state["last_seen_monotonic"]
            age = None if last is None else max(0.0, now_mono - last)
            online = age is not None and age <= self.stale_seconds

            scan_hz = state["sample_rates"]["scan"]
            rgb_hz = state["sample_rates"]["rgb"]
            depth_hz = state["sample_rates"]["depth"]

            params = state["oak_parameters"]
            configured_mode = params.get("camera.i_pipeline_type")
            configured_rgb_fps = params.get("rgb.i_fps")
            configured_depth_fps = expected_depth_fps(params)

            rgb_active = rgb_hz is not None and rgb_hz > 0
            depth_active = depth_hz is not None and depth_hz > 0

            if rgb_active and depth_active:
                observed_mode = "RGBD"
            elif rgb_active:
                observed_mode = "RGB"
            elif depth_active:
                observed_mode = "depth"
            else:
                observed_mode = "off"

            robots.append({
                "robot": robot,
                "hostname": state["hostname"],
                "namespace": state["namespace"],
                "online": online,
                "last_seen": state["last_seen"],
                "last_seen_age_seconds": None if age is None else round(age, 1),
                "battery": state["battery"],
                "dock": state["dock"],
                "lidar": {
                    "active": scan_hz is not None and scan_hz > 0,
                    "scan_hz": scan_hz,
                    "sampled_at": state["sampled_at"],
                },
                "camera": {
                    "active": rgb_active or depth_active,
                    "configured_mode": configured_mode,
                    "observed_mode": observed_mode,
                    "configured_rgb_fps": configured_rgb_fps,
                    "observed_rgb_fps": rgb_hz,
                    "rgb_health": stream_health(configured_rgb_fps, rgb_hz),
                    "configured_depth_fps": configured_depth_fps,
                    "observed_depth_fps": depth_hz,
                    "depth_health": stream_health(configured_depth_fps, depth_hz),
                    "effective_parameters": params,
                    "parameters_last_read": state["oak_parameters_last_read"],
                    "sampled_at": state["sampled_at"],
                },
            })

        return {
            "schema_version": 4,
            "generated_at": utc_now_string(),
            "sample_window_seconds": self.sample_window,
            "snapshot_interval_seconds": self.write_interval,
            "robots": robots,
        }

    def _write_status(self):
        document = self._document()
        self.output_path.parent.mkdir(parents=True, exist_ok=True)

        fd, tmp_name = tempfile.mkstemp(
            prefix=self.output_path.name + ".",
            suffix=".tmp",
            dir=self.output_path.parent,
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                json.dump(document, stream, indent=2, allow_nan=False)
                stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())

            os.replace(tmp_name, self.output_path)
        except Exception:
            try:
                os.unlink(tmp_name)
            except FileNotFoundError:
                pass
            raise

        if self.stdout:
            print(json.dumps(document, indent=2, allow_nan=False), flush=True)


def positive_float(value):
    value = float(value)
    if value <= 0:
        raise argparse.ArgumentTypeError("must be greater than zero")
    return value


def robot_number(value):
    value = int(value)
    if value <= 0:
        raise argparse.ArgumentTypeError("robot number must be positive")
    return value


def parse_args(argv):
    parser = argparse.ArgumentParser(
        description="Monitor JMU TurtleBot 4 fleet status with low CPU overhead."
    )
    parser.add_argument(
        "--robots",
        nargs="+",
        type=robot_number,
        default=[1, 2, 3, 4, 5, 6, 7],
        metavar="N",
        help="robot numbers to monitor (default: 1 2 3 4 5 6 7)",
    )
    parser.add_argument(
        "--output",
        default="/tmp/tb4_status.json",
        help="JSON output path (default: /tmp/tb4_status.json)",
    )
    parser.add_argument(
        "--write-interval",
        type=positive_float,
        default=60.0,
        metavar="SECONDS",
        help="seconds between status snapshots (default: 60)",
    )
    parser.add_argument(
        "--stale-seconds",
        type=positive_float,
        default=15.0,
        metavar="SECONDS",
        help="mark robot offline after this many seconds without monitored data "
             "(default: 15)",
    )
    parser.add_argument(
        "--sample-window",
        type=positive_float,
        default=5.0,
        metavar="SECONDS",
        help="seconds to subscribe to high-rate sensor streams before each "
             "snapshot (default: 5)",
    )
    parser.add_argument(
        "--parameter-interval",
        type=positive_float,
        default=60.0,
        metavar="SECONDS",
        help="seconds between OAK-D effective parameter reads (default: 60)",
    )
    parser.add_argument(
        "--stdout",
        action="store_true",
        help="also print each generated JSON document to stdout",
    )
    parsed = parser.parse_args(argv)

    if parsed.sample_window >= parsed.write_interval:
        parser.error("--sample-window must be less than --write-interval")

    return parsed


def main(args=None):
    raw_args = sys.argv if args is None else args
    non_ros_args = remove_ros_args(args=raw_args)
    parsed = parse_args(non_ros_args[1:])

    rclpy.init(args=raw_args)
    node = FleetStatus(
        robots=parsed.robots,
        output_path=parsed.output,
        write_interval=parsed.write_interval,
        stale_seconds=parsed.stale_seconds,
        sample_window=parsed.sample_window,
        parameter_interval=parsed.parameter_interval,
        stdout=parsed.stdout,
    )

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        if node.sampling:
            node._finish_sensor_sample()
        node._write_status()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
