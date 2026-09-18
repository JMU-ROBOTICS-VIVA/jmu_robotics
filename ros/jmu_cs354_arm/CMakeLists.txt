cmake_minimum_required(VERSION 3.8)
project(jmu_cs354_arm)

find_package(ament_cmake REQUIRED)

install(
  DIRECTORY
    launch
    urdf
    rviz
  DESTINATION share/${PROJECT_NAME}
)

install(
  PROGRAMS
    scripts/set_joints
  DESTINATION lib/${PROJECT_NAME}
)

ament_package()
