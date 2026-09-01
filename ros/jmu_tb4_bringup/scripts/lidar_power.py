#!/usr/bin/env python3

import rclpy

from rclpy.node import Node
from irobot_create_msgs.msg import DockStatus
from std_srvs.srv import Empty


class LidarPower(Node):

    def __init__(self):
        super().__init__('lidar_power')

        self.start_client = self.create_client(Empty, 'start_motor')
        self.stop_client = self.create_client(Empty, 'stop_motor')

        self.desired_docked = None

        # The RPLIDAR driver starts the LiDAR when it launches.
        # Only issue start_motor if this node previously stopped it.
        self.lidar_stopped_by_us = False

        self.request_in_flight = False

        self.subscription = self.create_subscription(
            DockStatus,
            'dock_status',
            self.dock_status_callback,
            10,
        )

        self.timer = self.create_timer(
            1.0,
            self.reconcile_lidar_state
        )

        self.get_logger().info(
            'JMU LiDAR dock power controller started.'
        )

    def dock_status_callback(self, msg):
        self.desired_docked = msg.is_docked

    def reconcile_lidar_state(self):
        if self.desired_docked is None:
            return

        if self.request_in_flight:
            return

        if self.desired_docked:
            # If we already stopped it, there is nothing more to do.
            if self.lidar_stopped_by_us:
                return

            client = self.stop_client
            action = 'stopping'
            requested_stop_state = True

        else:
            # The RPLIDAR driver starts running by itself at startup.
            # Therefore, only start it if WE previously stopped it.
            if not self.lidar_stopped_by_us:
                return

            client = self.start_client
            action = 'starting'
            requested_stop_state = False

        if not client.service_is_ready():
            return

        self.get_logger().info(
            f'Robot {"docked" if self.desired_docked else "undocked"}: '
            f'{action} LiDAR.'
        )

        self.request_in_flight = True

        future = client.call_async(Empty.Request())
        future.add_done_callback(
            lambda f, state=requested_stop_state:
                self.service_done(f, state)
        )

    def service_done(self, future, requested_stop_state):
        self.request_in_flight = False

        try:
            future.result()
            self.lidar_stopped_by_us = requested_stop_state

        except Exception as exc:
            self.get_logger().error(
                f'LiDAR motor service failed: {exc}'
            )


def main(args=None):
    rclpy.init(args=args)

    node = LidarPower()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
