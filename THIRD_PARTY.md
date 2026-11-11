# Third-party dependencies and notices

The bridge's own code is licensed under [MIT](LICENSE). The dependency implementations listed here are obtained separately; their licenses are not replaced by the bridge's MIT license. No dependency implementation source is vendored in the active src/, ros2/ or proto/ directories. Generated Protobuf and ROS files belong to build/install outputs.

This inventory covers the direct SDK dependencies, declared ROS packages and selected development tools visible in the source at PR7 merge `f5cd97075d65a14c1b62e610eed08e0372e50f57`. It prepares source publication; it is not a complete transitive SBOM or a license bundle for distributing compiled SDKs, ROS installations or container images.

## Standalone SDK

| Dependency | Use and version boundary | License / upstream notice |
|---|---|---|
| Robotweax SRT | External transport library; build-guide pin `52be7c86ee1f303cbb0c8718c364217e4dd97a36`, namespaced GCM-enabled build | [MIT license](https://github.com/Robotweax/srt/blob/52be7c86ee1f303cbb0c8718c364217e4dd97a36/LICENSE), copyright 2026 Robotweax GmbH and contributors; [upstream dependency/provenance notices](https://github.com/Robotweax/srt/blob/52be7c86ee1f303cbb0c8718c364217e4dd97a36/THIRD_PARTY.md) |
| OpenSSL | Crypto primitives in the management/command code and SRT; SDK requires 3.0+ | [Apache-2.0, OpenSSL 3.0.13 license](https://github.com/openssl/openssl/blob/85cf92f55d9e2ac5aacf92bedd33fb890b9f8b4c/LICENSE.txt) |
| Protocol Buffers | protoc generates C++ from the bridge's own .proto files; libprotobuf supplies the runtime; requires 3.21+ | [BSD-3-Clause, v21.12 license and generated-code statement](https://github.com/protocolbuffers/protobuf/blob/f0dc78d7e6e331b8c6bb2d5283e06aa26883ca7c/LICENSE), copyright 2008 Google Inc. |
| SQLite | Durable journal storage; requires 3.45+ | [SQLite public-domain dedication](https://www.sqlite.org/copyright.html), for deliverable SQLite library code; build scripts may have separate terms |

The [fresh-clone verification inventory](evidence/publication-docs-2026-11-11/linux-environment.log) records OpenSSL 3.0.13, Protobuf 3.21.12 and SQLite 3.45.1 with Ubuntu package revisions. Those observed versions are not a new dependency pin or an update to historical qualification. The portable core configuration disables these optional dependency paths; it still uses the compiler's C++ standard library and operating-system facilities.

Robotweax SRT and Haivision SRT are distinct projects. Haivision implementation code is not a bridge dependency selected by the build guide. The Robotweax pin's own THIRD_PARTY.md explains its upstream references and separate interoperability tooling; those references do not import Haivision's license into bridge-authored files.

## ROS 2 Jazzy packages

The following external packages are declared by the three bridge manifests, or used by the retained DDS tooling. Each linked package manifest declares Apache License 2.0. These are license-reference source revisions checked on 2026-11-11, not replacements for the versions installed by rosdep or recorded in the accepted artifacts.

| Package | Role | Upstream license declaration |
|---|---|---|
| rclcpp | C++ ROS clients, bridge, worker and simulator | [rclcpp manifest](https://github.com/ros2/rclcpp/blob/35b821a9fb1f937bfbd9c741b7e3353e101d9593/rclcpp/package.xml) |
| rclpy | Python scenario clients | [rclpy manifest](https://github.com/ros2/rclpy/blob/521012e60ba21319ef29141f8f521a0e072fe652/rclpy/package.xml) |
| sensor_msgs | IMU and joint-state interfaces | [sensor_msgs manifest](https://github.com/ros2/common_interfaces/blob/a941f14bb318d8d904505ed935ccbb97f24a70a4/sensor_msgs/package.xml) |
| rcl_interfaces | Parameter messages/services | [rcl_interfaces manifest](https://github.com/ros2/rcl_interfaces/blob/7aa3caf43377ea6ad615bc1040832e2c7566bfbe/rcl_interfaces/package.xml) |
| ament_cmake | ROS package build system | [ament_cmake manifest](https://github.com/ament/ament_cmake/blob/b465a29f21842fcfb5eb70c61a02deb9543a6299/ament_cmake/package.xml) |
| ament_index_python | Installed-package lookup | [ament_index_python manifest](https://github.com/ament/ament_index/blob/2ccdcb8fd19a364fc793273b5793459207a440b9/ament_index_python/package.xml) |
| rosidl_default_generators / rosidl_default_runtime | ROS interface generation/runtime configuration | [generators](https://github.com/ros2/rosidl_defaults/blob/9749b5919add7e5960cd931ec547d45f06bd0025/rosidl_default_generators/package.xml), [runtime](https://github.com/ros2/rosidl_defaults/blob/9749b5919add7e5960cd931ec547d45f06bd0025/rosidl_default_runtime/package.xml) |
| rosidl_runtime_py | Python ROS message conversion | [rosidl_runtime_py manifest](https://github.com/ros2/rosidl_runtime_py/blob/819e5c9c33b8f1986b1dcd6c9c792d95f8e9f486/package.xml) |
| ament_cmake_gtest | ROS test integration | [ament_cmake_gtest manifest](https://github.com/ament/ament_cmake/blob/b465a29f21842fcfb5eb70c61a02deb9543a6299/ament_cmake_gtest/package.xml) |
| rmw_fastrtps_cpp | Retained Fast DDS comparison/development tooling | [rmw_fastrtps_cpp manifest](https://github.com/ros2/rmw_fastrtps/blob/6bba0a746ba362ead10585bf4f4bbc49d62e0955/rmw_fastrtps_cpp/package.xml) |

The ROS graph also brings middleware, serialization, Python and system dependencies. Selected middleware references are [eProsima Fast DDS, Apache-2.0](https://github.com/eProsima/Fast-DDS/blob/cf92048fd49fbcf9ee38c39660387e510b070e55/LICENSE) and [Fast CDR, Apache-2.0](https://github.com/eProsima/Fast-CDR/blob/c781654737ded838e26d11584bbb68e3de795b86/LICENSE). These checked license files do not establish the exact middleware version or complete contents of a given installed ROS environment. The bridge's generated interfaces do not relicense their supporting runtimes.

## Development environment and tests

GoogleTest is used through ament_cmake_gtest when ROS tests are enabled; its [v1.14.0 BSD-3-Clause license](https://github.com/google/googletest/blob/f8d7d77c06936315286eb55f8de22cd23c188571/LICENSE) is a reference, not an enforced test-library pin. Source compilation also uses CMake, Ninja, a C++ toolchain, Python, colcon and rosdep. Their packages, compiler runtimes and transitive dependencies retain their own notices.

The retained container recipes are development/qualification recipes, not published application images. In particular, containers/m3.Dockerfile fetches iproute2 6.17.0 with a recorded archive hash and installs additional network and build tools. [iproute2's GPL version 2 text](https://github.com/iproute2/iproute2/blob/d2a8ffe85ac64f91ee2aa7679a5046f321b54127/COPYING), [tcpdump's BSD license](https://github.com/the-tcpdump-group/tcpdump/blob/0af4382422d0752fc13b7def40a26f959f8dc411/LICENSE) and [iperf3's license and additional notices](https://github.com/esnet/iperf/blob/53f88becd961c1b3a0294d8a7359d62d863cd8f2/LICENSE) are separate from the bridge license. These external executables are not linked into the bridge SDK. Other packages in those recipes, including libcap/libbpf/libelf/libmnl and the Ubuntu/ROS base layers, need their actual package-level notices when redistributing an image. This inventory does not authorize publishing the local development images.

## Before distributing binaries or images

For the concrete artifact, record exact source/package versions and static/dynamic linkage, inventory all bundled/generated/transitive components, and collect their applicable license texts, copyright notices and NOTICE files. Include any required corresponding source or source offers for components whose licenses require them. Keep these materials with the distributed artifact; links in this source inventory alone are not a complete binary/image redistribution package.

The current SDK/ROS install rules copy the bridge MIT license. They do not automatically assemble third-party licenses or notices. No binary/image release or container publication is prepared by this change. New dependency versions need a fresh notice review and their own build provenance.

[Source identities and review checks](evidence/publication-guidance-2026-11-11/README.md) are separate from M3 acceptance. Intrinsic integration remains paused and supplies no dependency to this bridge.
