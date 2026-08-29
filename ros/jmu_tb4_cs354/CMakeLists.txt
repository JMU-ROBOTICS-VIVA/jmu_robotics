cmake_minimum_required(VERSION 3.8)
project(jmu_tb4_cs354)

find_package(ament_cmake REQUIRED)

install(
  PROGRAMS scripts/sim_robot_description.py
  DESTINATION share/${PROJECT_NAME}/scripts
)

install(
  DIRECTORY launch rviz
  DESTINATION share/${PROJECT_NAME}
)

ament_package()

