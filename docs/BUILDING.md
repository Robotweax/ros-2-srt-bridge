# Fresh-clone build guide

This guide builds the current source and installed packages. It does not launch a bridge node, simulator, DDS comparison, impairment harness or M3 campaign. The retained M3 acceptance applies to its exact historical artifacts; a fresh build is a separate result.

## 1. Clone the bridge

Git and network access are needed for source downloads. The public bridge and SRT repositories can be cloned without GitHub authentication; do not put a token into the clone URL.

```bash
git clone https://github.com/Robotweax/ros-2-srt-bridge.git
cd ros-2-srt-bridge
git rev-parse HEAD
```

Record that commit alongside the compiler, OS and dependency versions used for your build.

## 2. Portable core, without ROS or SRT

Requirements: CMake 3.20+, a C++20 compiler and a build tool. From the bridge root:

```bash
cmake -S . -B build/core-only \
  -DCMAKE_BUILD_TYPE=Debug \
  -DBUILD_PROFILE_PROBE=OFF \
  -DBUILD_SRT_TRANSPORT=OFF \
  -DBUILD_MANAGEMENT_CODEC=OFF \
  -DBUILD_TESTING=ON
cmake --build build/core-only --parallel 2
ctest --test-dir build/core-only --no-tests=error --output-on-failure
cmake --install build/core-only --prefix "$PWD/install/core-only"
```

This selects wire, clock, bandwidth/reconnect and shutdown-trace contracts. It does not build the Linux worker, management protocol, SRT transport or ROS adapters. Consumers can require `RobotweaxBridge` with `COMPONENTS core` from the installed prefix.

## 3. Full SDK and ROS prerequisites

Use **Ubuntu 24.04 amd64 with ROS 2 Jazzy installed** for the complete path. Follow the official [Jazzy installation guide](https://docs.ros.org/en/jazzy/Installation/Ubuntu-Install-Debs.html) to configure the ROS package repository first.

The following are dependency-installation steps for your chosen development environment; they are separate from compilation:

```bash
sudo apt-get update
sudo apt-get install -y \
  build-essential cmake ninja-build git pkg-config \
  libssl-dev libprotobuf-dev protobuf-compiler libsqlite3-dev \
  python3-colcon-common-extensions python3-rosdep
source /opt/ros/jazzy/setup.bash
```

The full SDK requires OpenSSL 3.x, Protobuf 3.21+ (compiler and library) and SQLite 3.45+. Initialize rosdep once if your environment has not already done so, following the [official rosdep guide](https://docs.ros.org/en/jazzy/Tutorials/Intermediate/Rosdep.html), then resolve the ROS package dependencies from the bridge root:

```bash
rosdep update
rosdep install --from-paths ros2 --ignore-src --rosdistro jazzy -y
```

These operations use the network and may install packages. Package repositories change over time. Capture your actual versions; this guide does not promise byte-for-byte reconstruction of the historical development images. No host kernel, networking, real-time or simulator tuning is required by these build steps.

## 4. Fetch the pinned SRT source

From a new bridge clone, fetch the exact dependency into its own ignored directory:

```bash
git init .deps/srt
git -C .deps/srt remote add origin https://github.com/Robotweax/srt.git
git -C .deps/srt fetch --depth 1 origin 52be7c86ee1f303cbb0c8718c364217e4dd97a36
git -C .deps/srt checkout --detach FETCH_HEAD
test "$(git -C .deps/srt rev-parse HEAD)" = 52be7c86ee1f303cbb0c8718c364217e4dd97a36
test -z "$(git -C .deps/srt status --porcelain --untracked-files=all)"
```

The initialization is for an empty .deps/srt directory. For a subsequent build, inspect the existing checkout and its commit rather than re-adding its remote. This is the Robotweax fork's namespaced CMake package, `RobotweaxSRT`; the bridge uses its version-pinned GCM/SESSIONAUTH API.

## 5. Build and install SRT

```bash
cmake -S .deps/srt -B build/srt -G Ninja \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_INSTALL_PREFIX="$PWD/install/srt" \
  -DBUILD_SHARED_LIBS=OFF \
  -DROBOTWEAX_SRT_INSTALL_LAYOUT=namespaced \
  -DROBOTWEAX_SRT_BUILD_TESTS=OFF \
  -DROBOTWEAX_SRT_BUILD_EXAMPLES=OFF \
  -DROBOTWEAX_SRT_BUILD_BENCHMARKS=OFF \
  -DROBOTWEAX_SRT_BUILD_TOOLS=OFF \
  -DROBOTWEAX_SRT_CRYPTO_BACKEND=openssl \
  -DENABLE_AEAD_API_PREVIEW=ON
cmake --build build/srt --parallel 2
cmake --install build/srt
```

The GCM flag must be enabled in both the matching installed headers and library. Experimental ACP1/controller/filter options remain at their disabled defaults. These build-only options intentionally omit SDK tests/examples; they do not reproduce the accepted M0/M3 build flags.

## 6. Build and install the bridge SDK

```bash
cmake -S . -B build/bridge -G Ninja \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_PREFIX_PATH="$PWD/install/srt" \
  -DCMAKE_INSTALL_PREFIX="$PWD/install/bridge" \
  -DBUILD_SHARED_LIBS=OFF \
  -DBUILD_MANAGEMENT_CODEC=ON \
  -DBUILD_PROFILE_PROBE=OFF \
  -DBUILD_SRT_TRANSPORT=ON \
  -DBUILD_TESTING=OFF
cmake --build build/bridge --parallel 2
cmake --install build/bridge
```

This installs the SDK, exported CMake targets, worker executable and MIT license into install/bridge. It uses no pre-existing SDK prefix. The Linux-only worker uses Linux process/IPC facilities; the portable-core result does not qualify that component on other operating systems.

## 7. Build the ROS packages

In the same shell, from the bridge root:

```bash
source /opt/ros/jazzy/setup.bash
colcon --log-base log/fresh-build build \
  --base-paths ros2 \
  --build-base build/ros \
  --install-base install/ros \
  --cmake-args \
    -DCMAKE_BUILD_TYPE=Release \
    -DBUILD_TESTING=OFF \
    "-DCMAKE_PREFIX_PATH=$PWD/install/bridge;$PWD/install/srt"
source install/ros/setup.bash
ros2 pkg prefix robotweax_srt_bridge_msgs
ros2 pkg prefix robotweax_srt_bridge
ros2 pkg prefix robotweax_srt_bridge_demo
```

Build only ros2/ with colcon: the standalone SDK and dependency are already installed. Leave those install prefixes in place while using the ROS executables, since the SDK worker path is bound at build time. Each ROS package installs its MIT license under its package share directory.

Package discovery confirms installation, not transport communication or simulator behavior. ROS tests, endpoint execution and qualification harnesses are separate activities.

## Reproducibility and retained evidence

- Use separate empty build/install directories for a different compiler, architecture, SRT commit or ROS distribution.
- Record source commit, SRT commit, CMake options, compiler/package inventory and build/test output. A container image's actual platform ID is part of that record if a container is used.
- The local image names and immutable IDs in baselines/ describe historical qualification environments; they are not public images a new user can assume are available.
- Do not update accepted baselines, freeze files or historical evidence to describe a new build. New validation gets its own record.
- Intrinsic integration remains paused and is not a dependency of this guide.

The [README](../README.md), [architecture](../ARCHITECTURE.md) and [scoped acceptance](../M3_SCOPED_ACCEPTANCE.md) describe supported contracts and their limits.

## Verification of these instructions

The documented command blocks were checked from fresh GitHub checkouts of bridge commit `1e52b76fd7eff6fd040f1be6fe79905dacadd106` and the SRT pin above. The portable core passed all five contract tests on macOS arm64. A separate Linux amd64 container build, with networking disabled and empty SRT/bridge/ROS prefixes, built and installed the full SDK and all three ROS packages; package discovery and four installed license copies were checked.

The Linux validation reused an existing Ubuntu/ROS dependency image, recorded by its actual image ID. Apt/rosdep bootstrap was not executed on a fresh host. No bridge node, simulator or M3 campaign was launched. This is source/build/install verification, not runtime qualification or a replacement M3 baseline. [Validation details](../evidence/publication-docs-2026-11-11/build-verification.json).
