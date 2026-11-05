cmake_minimum_required(VERSION 3.20)
project(robotweax_srt_bridge_msgs)
find_package(ament_cmake REQUIRED)
find_package(rosidl_default_generators REQUIRED)
rosidl_generate_interfaces(${PROJECT_NAME}
  msg/CommandStatus.msg msg/BridgeState.msg msg/SimulatorState.msg
  srv/ExecuteCommand.srv srv/GetCommandStatus.srv srv/ApplyMeasurementRate.srv)
ament_export_dependencies(rosidl_default_runtime)
ament_package()
