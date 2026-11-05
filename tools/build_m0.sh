#!/bin/sh
# Run inside the M0 development container with the project mounted at /workspace.
set -eu
cd /workspace
cmake -S .deps/srt -B build/srt-m0 -G Ninja \
  -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=OFF -DCMAKE_INSTALL_PREFIX=/workspace/install/srt-m0 \
  -DROBOTWEAX_SRT_INSTALL_LAYOUT=namespaced \
  -DROBOTWEAX_SRT_BUILD_TESTS=ON -DROBOTWEAX_SRT_BUILD_EXAMPLES=ON \
  -DROBOTWEAX_SRT_BUILD_BENCHMARKS=OFF -DROBOTWEAX_SRT_BUILD_TOOLS=OFF \
  -DROBOTWEAX_SRT_CRYPTO_BACKEND=openssl -DENABLE_AEAD_API_PREVIEW=ON \
  -DROBOTWEAX_SRT_ENABLE_EXPERIMENTAL_ACP1=OFF \
  -DROBOTWEAX_SRT_ENABLE_EXPERIMENTAL_CONTROLLERS=OFF \
  -DROBOTWEAX_SRT_ENABLE_EXPERIMENTAL_FILTERS=OFF
cmake --build build/srt-m0 --parallel "${BUILD_JOBS:-6}"
cmake --install build/srt-m0
cmake -S . -B build/m0 -G Ninja -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_PREFIX_PATH=/workspace/install/srt-m0
cmake --build build/m0 --parallel "${BUILD_JOBS:-6}"
