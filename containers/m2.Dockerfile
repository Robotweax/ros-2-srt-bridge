FROM ros@sha256:8eed0a4669bbf43ee331878a4c39bd8ebddea8e3312a58b4fae8edb14526b617
# Exact M0 development package versions, layered over the pinned ROS image.
RUN apt-get update && apt-get install -y --no-install-recommends \
    ninja-build=1.11.1-2 \
    libprotobuf-dev=3.21.12-8.2ubuntu0.4 \
    protobuf-compiler=3.21.12-8.2ubuntu0.4 \
    libssl-dev=3.0.13-0ubuntu3.16 \
    libsqlite3-dev=3.45.1-1ubuntu2.8 \
    && rm -rf /var/lib/apt/lists/*
