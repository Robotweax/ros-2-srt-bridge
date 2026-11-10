#!/usr/bin/env bash
set -eo pipefail
cd /workspace
cmake -S . -B build/m3-socket-disposition -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=OFF -DRobotweaxSRT_DIR=/workspace/install/srt-m0/lib/cmake/RobotweaxSRT
cmake --build build/m3-socket-disposition --parallel 2
cmake --install build/m3-socket-disposition --prefix /workspace/install/bridge-socket-disposition
g++ -std=c++20 -Wall -Wextra -Wpedantic -Werror -pthread -Isrc/robotweax_srt_bridge_core/include tests/protocol/shutdown_trace_tests.cpp -o build/m3-socket-disposition/shutdown_trace_tests
build/m3-socket-disposition/shutdown_trace_tests
source /opt/ros/jazzy/setup.bash
colcon --log-base log/m3-socket-disposition build --base-paths ros2 --build-base build/m3-socket-disposition-ros --install-base install/m3-socket-disposition-ros --packages-select robotweax_srt_bridge_msgs robotweax_srt_bridge robotweax_srt_bridge_demo --cmake-args -DBUILD_TESTING=OFF -DCMAKE_BUILD_TYPE=Release -DRobotweaxBridge_DIR=/workspace/install/bridge-socket-disposition/lib/cmake/RobotweaxBridge -DRobotweaxSRT_DIR=/workspace/install/srt-m0/lib/cmake/RobotweaxSRT
