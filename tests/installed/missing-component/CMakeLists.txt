cmake_minimum_required(VERSION 3.20)
project(robotweax_bridge_missing_component LANGUAGES CXX)
find_package(RobotweaxBridge 0.1 CONFIG REQUIRED COMPONENTS deliberately_unavailable)
message(FATAL_ERROR "Missing bridge component was accepted")
