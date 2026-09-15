import rclpy
from rclpy.node import Node
from rclpy.time import Time
from sensor_msgs.msg import LaserScan
from tf2_ros import Buffer, TransformException, TransformListener


class FrameDemo(Node):
    def __init__(self):
        super().__init__('frame_demo')

        # Relative topic name: the launch namespace selects the robot.
        self.create_subscription(LaserScan, 'scan', self.scan_callback, 10)

        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)
        self.timer = self.create_timer(1.0, self.report_lidar_pose)

    def scan_callback(self, _scan):
        pass

    def report_lidar_pose(self):
        try:
            transform = self.tf_buffer.lookup_transform(
                'base_link',
                'rplidar_link',
                Time(),
            )
        except TransformException as exc:
            self.get_logger().info(f'Transform not available yet: {exc}')
            return

        t = transform.transform.translation
        self.get_logger().info(
            f'rplidar_link in base_link: x={t.x:.3f}, y={t.y:.3f}, z={t.z:.3f}'
        )


def main(args=None):
    rclpy.init(args=args)
    node = FrameDemo()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
