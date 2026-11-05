FROM ros@sha256:8eed0a4669bbf43ee331878a4c39bd8ebddea8e3312a58b4fae8edb14526b617
# M3 needs the netem PRNG seed attribute absent from Noble's older tc binary.
# Retain source URL/hash; runtime uses the resulting immutable image digest.
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    ninja-build=1.11.1-2 libprotobuf-dev=3.21.12-8.2ubuntu0.4 protobuf-compiler=3.21.12-8.2ubuntu0.4 \
    libssl-dev=3.0.13-0ubuntu3.16 libsqlite3-dev=3.45.1-1ubuntu2.8 \
    curl bison flex pkg-config libmnl-dev libelf-dev libbpf-dev libcap-dev \
    iputils-ping tcpdump iperf3 \
    && rm -rf /var/lib/apt/lists/*
RUN curl --fail --location --silent --show-error \
      https://www.kernel.org/pub/linux/utils/net/iproute2/iproute2-6.17.0.tar.xz -o /tmp/iproute2.tar.xz \
    && echo '9781e59410ab7dea8e9f79bb10ff1488e63d10fcbb70503b94426ba27a8e2dec  /tmp/iproute2.tar.xz' | sha256sum -c - \
    && tar -xJf /tmp/iproute2.tar.xz -C /tmp \
    && cd /tmp/iproute2-6.17.0 && make -j3 && make install \
    && rm -rf /tmp/iproute2-6.17.0 /tmp/iproute2.tar.xz
