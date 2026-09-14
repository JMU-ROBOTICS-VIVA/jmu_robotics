#!/usr/bin/env python3

import argparse
import sys

import rclpy
from rclpy.node import Node
from rclpy.duration import Duration
from rclpy.time import Time
from rclpy.utilities import remove_ros_args

from geometry_msgs.msg import PointStamped
from tf2_ros import Buffer, TransformListener, TransformException
from tf2_geometry_msgs import do_transform_point


def main():
    args_without_ros = remove_ros_args(args=sys.argv)

    parser = argparse.ArgumentParser(
        description="Transform a 3-D point between TF frames."
    )
    parser.add_argument("source_frame")
    parser.add_argument("target_frame")
    parser.add_argument("x", type=float)
    parser.add_argument("y", type=float)
    parser.add_argument("z", type=float)

    args = parser.parse_args(args_without_ros[1:])

    rclpy.init(args=sys.argv)

    node = Node("transform_point")
    tf_buffer = Buffer()

    # A private spin thread lets TF messages arrive while lookup_transform waits.
    tf_listener = TransformListener(
        tf_buffer,
        node,
        spin_thread=True
    )

    try:
        transform = tf_buffer.lookup_transform(
            args.target_frame,
            args.source_frame,
            Time(),
            timeout=Duration(seconds=2.0)
        )

        source_point = PointStamped()
        source_point.header.frame_id = args.source_frame
        source_point.point.x = args.x
        source_point.point.y = args.y
        source_point.point.z = args.z

        target_point = do_transform_point(
            source_point,
            transform
        )

        print(
            "{}: ({:.3f}, {:.3f}, {:.3f})".format(
                args.source_frame,
                args.x,
                args.y,
                args.z
            )
        )

        print(
            "{}: ({:.3f}, {:.3f}, {:.3f})".format(
                args.target_frame,
                target_point.point.x,
                target_point.point.y,
                target_point.point.z
            )
        )

    except TransformException as ex:
        print("Transform failed: {}".format(ex))

    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
