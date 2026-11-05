# ROS 2 SRT Bridge

Selective WAN bridge for ROS 2: Robotweax SRT SENSOR carries current small
samples; CONTROL carries acknowledged application commands.

[Bridge repository](https://github.com/Robotweax/ros-2-srt-bridge) owns M0–M3.
The later M4 adapter belongs in
[intrinsic-core-srt-integration](https://github.com/Robotweax/intrinsic-core-srt-integration).
SRT is a separately installed dependency; the enclosing SRT checkout is preserved.

## Development status — 2026-11-05

M0's selected local qualification checks pass on Ubuntu 24.04 Linux amd64 under
Docker Desktop emulation. The installed C API probe covers CONTROL/SENSOR,
GCM + SESSIONAUTH v2, IPv4/MSS 1500, IPv6/MSS 1280, payload boundaries,
negative handshakes, nonblocking epoll, and close with full send buffers.
ROS Jazzy type hashes and bounded CDR sizes are checked separately.

M1 includes the wire codec, bounded management validation, ClockMapper,
canonical route manifests with SHA-256, and an event-driven session state machine.
Real protected SRT socket tests pass over IPv4 and IPv6, including delayed binding
acknowledgments, SENSOR rebind, full CONTROL reconnect and stale-session rejection.
Bounded queues, estimated bandwidth admission and cancellable reconnect planning
are implemented, together with a bounded SQLite command journal, typed rate
commands/status, crash recovery and query reconciliation across reconnect.
A threaded transport owner now manages real sockets, epoll, Session, bounded
mailboxes, periodic clock probes and reconnect. A supervised journal process now
mints one-use durable sender tickets and supports bounded asynchronous storage
requests. An automatic endpoint coordinator now applies query-first recovery and shared
revocable start fences for an explicitly enabled simulated rate handler. Request-scoped ERROR responses now surface reconciliation failures without
changing journal truth, and the CMake SDK has a relocated installed-consumer check.
M2 is complete for the recorded Linux amd64 ROS Jazzy simulator profile.
The [M2 acceptance matrix](evidence/m2-ros-jazzy-2026-11-05/ACCEPTANCE.md) records
typed sensors, actual measurement-rate changes, duplicate suppression and
UNKNOWN recovery after lost replies and a two-second bridge outage. M3 performance
comparisons and the M4 Intrinsic adapter remain later work. See [evidence](evidence/m0-2026-11-04/README.md)
and the [handoff](HANDOFF.md) for exact scope and next work.

M1 is complete for the documented Linux amd64 baseline. The
[M1 acceptance matrix](evidence/m1-errors-sdk-2026-11-05/ACCEPTANCE.md) maps each
requirement to retained checks and states the qualification limits.

## Run M0

Requires Docker with Linux amd64 execution, Python 3, Git, and a local SRT
repository containing the pinned commit. From this project directory:

```sh
docker pull --platform linux/amd64 ros@sha256:8eed0a4669bbf43ee331878a4c39bd8ebddea8e3312a58b4fae8edb14526b617
python3 tools/run_m0.py --build-image --srt-source ..
```

The runner creates a separate `.deps/srt` clone when missing and requires a clean
source at `52be7c86ee1f303cbb0c8718c364217e4dd97a36`. It builds and installs the
namespaced SRT package, discovers test inventories, rejects missing/skipped tests,
and runs the installed consumer and ROS type probe. Container execution uses
`--network none`; image download and development-image construction use the network.
Every attempt keeps logs, commands, package inventories, JUnit results and a run
manifest in a new `.local/m0/` directory. It stops at the first failing gate.

For the existing local images recorded in `baselines/dependencies.json`, omit
`--build-image`. That file locks the qualified image digests and package versions.
The development image is local, not published. Its Dockerfile uses a pinned OS
base with apt packages resolved at build time; rebuilding can produce a new
image and must be recorded as a new baseline. The runner records its actual digest
and package inventory rather than assuming it reproduces the previous image.

## Run M1 contracts

After M0 has created the locked local development image:

```sh
python3 tools/run_m1.py
```

This runs all fifteen core contracts on Linux amd64 in Debug and with ASan+UBSan,
checks the discovered test inventory, and saves commands, source fingerprints,
logs and JUnit output in a new `.local/m1/` directory. The current
[error/SDK evidence](evidence/m1-errors-sdk-2026-11-05/README.md) records the checks
and remaining integration work. To also build and run the full installed-SRT
regression and native session harness after M0:

```sh
python3 tools/run_m1.py --native
```

That mode verifies the installed SRT archive against the M0 SHA-256 and runs all
67 root tests, including session and threaded transport counterparts over IPv4 and
IPv6. It also runs the ten transport/worker/endpoint integration cases under ASan+UBSan; the
prebuilt SRT dependency itself is not sanitizer-instrumented. The same command
also installs/relocates the SDK and builds/runs an external consumer, rejecting
unavailable required components and accidental ROS/second-SRT runtime links.

## Build the core without ROS or SRT

Full core: CMake 3.20+, C++20, Protobuf 3.21+ (compiler/library), OpenSSL 3.x, and SQLite 3.45+.
The management codec uses generated Protobuf code after bounded preflight checks.
For wire, clock, bandwidth and reconnect contracts, Protobuf can be disabled:

```sh
cmake -S . -B build/core-only -DBUILD_PROFILE_PROBE=OFF -DBUILD_MANAGEMENT_CODEC=OFF -DCMAKE_BUILD_TYPE=Debug
cmake --build build/core-only --parallel 2
ctest --test-dir build/core-only --no-tests=error --output-on-failure
```

The full core configures independently with
`cmake -S src/robotweax_srt_bridge_core -B build/core`; management is enabled
by default. Link `RobotweaxBridge::core` for wire/clock, bandwidth and reconnect functionality and
`RobotweaxBridge::protocol` for management, manifests, sessions and queues
(`RobotweaxBridge::management` remains an alias).
`RobotweaxBridge::journal` adds durable sender/receiver command storage. Its API
performs blocking file I/O and runs in the supervised journal child, never a ROS
or network callback.
Wire tests use an independent network-byte-order golden vector and 20,000
seeded mutations. The decoder returns borrowed payload views after structural
validation; it does not authorize a session. The ClockMapper qualifies age only
under explicitly supplied drift/error assumptions and a valid epoch/domain binding.
SENSOR queues own the latest unsent sample per route and enforce route rate/deadline
limits. CONTROL preserves FIFO with 64 entries/256 KiB, reserving eight slots/32 KiB
for management and status. Queue admission is volatile and does not mean a command
was durably accepted. The bandwidth budget estimates overhead and commits credits
only after SRT accepts a message. Reconnect planning has no sleeps and never retries
a permanent failure without explicit reactivation.

The Session class correlates probes and gates session/epoch/domain, routes,
sequence and age. The transport owner applies its close/flush actions.
Admission applies at the supplied time; a deferred publisher must recheck freshness
before publication. There is no ROS publication path yet.

Read [ARCHITECTURE.md](ARCHITECTURE.md) for contracts and [HANDOFF.md](HANDOFF.md)
for implementation order and the qualified M1 scope. Next: the isolated ROS Jazzy
demonstration in M2, with actual CDR/type/QoS gates and service interfaces.

## Threaded transport

With the qualified installed SRT package, link `RobotweaxBridge::transport`.
The root build enables `BUILD_SRT_TRANSPORT` alongside the profile probe by default;
standalone core builds retain no SRT dependency. The transport accepts numeric IPv4
or IPv6 endpoints and a supplied credential. It applies the qualified GCM,
SESSIONAUTH and channel profiles, bounded socket buffers, nonblocking mode and
zero linger. One thread owns every socket/provider operation and protocol object;
no user callback, journal operation or handler runs on it.

External sample submission owns a bounded copy and preserves the supplied monotonic
ingress time. The eight route slots replace older unsent samples. QUERY/STATUS
mailboxes have 64 FIFO entries; try-lock admission reports BUSY on contention or
capacity. Receive-side CONTROL stops reading before its 64-entry mailbox fills;
samples remain latest-only and are checked again for expiry when polled. Session
and connection-generation tokens fence stale work after reconnect. Periodic clock
probes and separate cancellable CONTROL/SENSOR retry plans run on the owner.

`request_stop()` ends admission; `join()` belongs to the external lifecycle owner.
Tests stop during active traffic, concurrent producers and absent-peer retries
within five seconds. This qualifies transport lifecycle on the recorded environment;
journal processes have a separate bounded stop protocol. Combined endpoint and
handler lifecycle tests now cover paused workers, concurrent producers and operation
timeouts within five seconds on the qualified environment. COMMAND submission requires a one-use durable
sender ticket; received messages alone never authorize execution. A STATUS supplied by a trusted worker must already have
a durable journal result. ROS callbacks/publication are not implemented yet.

## Supervised journal worker

On the qualified Linux/glibc baseline, link `RobotweaxBridge::worker` and configure
an absolute path to the built `robotweax-journal-worker` executable. The supervisor
uses `posix_spawn` after transport threads are running, passes only standard streams
and private IPC/execution-fence descriptors, and keeps SQLite out of the parent process. IPC frames
are fixed at 2,048 bytes, with at most 64 outstanding requests. One external
coordinator services every supervisor method, including stop/join. `submit()`
and `poll()` never wait for storage. Ticket liveness and start-fence words are
shared atomically with the separate network thread. The child
uses its own current monotonic time when each operation starts, including queue wait.

Only a newly inserted, committed sender LOCAL_QUEUED reply creates a move-only
`DurableCommandTicket`. GET, duplicate admission, receiver admission, expiry and
storage failure cannot mint one. `submit_command(context, std::move(ticket))`
consumes it after volatile mailbox admission; BUSY preserves it. The owner validates
peer, epoch, route, budget and context and checks ticket liveness/deadline again
before queued sends. Stop and detected worker failure revoke its tickets. An
already started send can still reach the peer; it remains a durable intent, not an
execution acknowledgment. Old commands are never automatically resent.

`request_command_check()` provides a bounded asynchronous observation of Session
and freshness for pre/post-DISPATCHING checks. It is not a handler start permit.
A durable DISPATCHING reply can mint a separate move-only `DispatchTicket`.
`request_command_start()` combines it with a fresh owner check to grant a shared
atomic start fence. The same worker must consume that fence before revocation and
its deadline. Session/clock loss races with start through a single compare/exchange;
a running handler may finish, while a revoked unstarted handler cannot apply its
effect. Grant expiry is bounded by both command freshness and the clock model's
probe-age/drift qualification. Later probes cannot extend an issued grant.

On the qualified Linux build the fixed 64-slot fence pool uses sealed memfd geometry
and lock-free 64-bit atomics, mapped separately by the exec child. IPC is now private
version 2; this does not change the network command schema. Handler execution is an
explicit local `simulated_rate_handler` option and performs an absolute rate change
with an expected/new generation. The network thread runs no handler or storage work.

Worker stop revokes tickets immediately, allows two seconds for graceful exit,
then sends SIGKILL. Join uses one four-second deadline across repeat calls. If the
kernel has not reaped the child by that deadline, it returns `shutdown_timeout`;
a fallback reaper retains no owner memory. Paused-process tests verify normal kill
and recovery within five seconds, without claiming a bound on uninterruptible
kernel/device I/O. Unanswered requests require recovery/status query; stop never
fabricates a successful command result.

## Automatic command endpoint

Link `RobotweaxBridge::endpoint` on qualified Linux and construct `CommandEndpoint`
with matching transport/worker peer IDs, process epoch and role. The receiver must
explicitly enable the simulated rate handler. Its coordinator thread owns all
supervisor calls and exclusively consumes CONTROL/check replies; the transport
accessor remains available for sensor ingress/publication and diagnostics.

`execute()` and `query()` use bounded try-lock ingress, while `poll()` returns
committed journal observations or explicit local errors. QUEUED means volatile
mailbox admission. There are 64 input entries, 64 events and 64 tracked request IDs.
One workflow executes at a time, satisfying the per-route dispatch limit. Sender
admission precedes send; receiver admission precedes ACCEPTED; dispatch commit
precedes the final atomic start grant. Successful effects are reported only after
the result commit. Context loss invalidates old journal intents; tracked IDs are
queried after reconnect or missing results. Repeated IDs do not mint new sends.

The coordinator supervises each RPC/check with a configurable timeout (default
three seconds). Failure closes admission/transport and stops the child. Endpoint
stop also reports unresolved local work from existing bounded storage; context-loss
notifications are not device nonexecution proof. Durable terminal observations
remain available. Tests cover combined shutdown within five seconds, including a
paused handler and a full callback mailbox. The uninterruptible-kernel-I/O limit
of the worker supervisor still applies.

The handler's device state is deliberately process-local (initial 200 Hz,
generation 0). It resets when that worker restarts; stored results remain historical
proofs, not a claim about the current device. UNKNOWN never causes automatic replay.
M2 will connect an actual ROS simulator/handler. ERROR responses now make missing
peer records and admission failures observable without rewriting durable status.

## Wire diagnostics and reconciliation

ERROR is a bounded diagnostic from the robot Caller to the operator Listener,
scoped to an enabled command route and nonzero request ID in the current session.
It references a sent COMMAND or QUERY sequence. It carries no state, result, free
text or durable acknowledgment. The separate `errors_v1.proto` keeps the existing
rate-command descriptor hash stable. BUSY/CAPACITY include bounded retry advice;
no diagnostic extends the original start budget or authorizes a resend.

The owner correlates ERROR against a fixed 64-ID recent-send cache (latest COMMAND
and QUERY per ID/route). It rejects unknown, repeated or stale references. Standalone
transport users should bound outstanding distinct IDs accordingly. The endpoint
already limits tracked IDs to 64. Session/epoch/domain/direction/sequence gates still
apply; diagnostics need no execution-clock qualification and never answer ERROR.
Malformed or unauthenticated session/route traffic is dropped/closed rather than
used for diagnostic reflection.

`CommandEvent.peer_error` includes the diagnostic and `peer_context` identifies its
session/generations. Such events have no authoritative journal entry. The endpoint
leaves journal state untouched and suspends automatic queries for that ID in the
current session. Explicit QUERY or reconnection resumes reconciliation; an existing
ID never mints another COMMAND. A late ERROR cannot downgrade a known terminal
result or contradict a recorded admission with an older command error. A peer's
STORAGE diagnostic does not poison the local journal. Actual local storage errors
still fail closed and may disconnect before any diagnostic can be delivered.

BUSY, CONFLICT, CAPACITY, NOT_FOUND, invalid requests, stale start budgets and unknown
clock freshness can therefore be reported without fabricating REJECTED/EXPIRED
journal records. Pre-admission diagnostics do not reserve the receiver ID; callers
must retain their durable original intent and reconcile rather than blindly retry.

## Install the CMake SDK

After M0, on the qualified Linux image, build the SDK without test executables:

```sh
cmake -S . -B build/sdk -G Ninja -DCMAKE_BUILD_TYPE=Release -DCMAKE_PREFIX_PATH="$PWD/install/srt-m0" -DBUILD_PROFILE_PROBE=OFF -DBUILD_SRT_TRANSPORT=ON -DBUILD_TESTING=OFF
cmake --build build/sdk --parallel 3
cmake --install build/sdk --prefix "$PWD/install/bridge"
```

A consumer supplies the bridge and qualified SRT prefixes via CMAKE_PREFIX_PATH:

```cmake
find_package(RobotweaxBridge 0.1 CONFIG REQUIRED COMPONENTS endpoint)
target_link_libraries(my_bridge_node PRIVATE RobotweaxBridge::endpoint)
target_compile_definitions(my_bridge_node PRIVATE
  BRIDGE_WORKER_EXECUTABLE="$<TARGET_FILE:RobotweaxBridge::journal_worker>")
```

Use that executable path in WorkerOptions. Exported components are core, protocol
(management alias), journal, worker, worker_runtime, transport and endpoint as enabled by the build;
missing required components fail configuration. The package includes public headers,
libraries, protobuf sources and the worker executable. SRT remains a separately
installed dependency, never vendored into this project. The qualified SDK is static
Linux amd64; other full SDK profiles require qualification.

For only the portable core, configure `src/robotweax_srt_bridge_core` independently
with BUILD_MANAGEMENT_CODEC=OFF, then install and require COMPONENTS core. That package
requires neither SRT nor Protobuf/OpenSSL/SQLite/ROS and is also checked on macOS arm64.

## Run M2 ROS Jazzy demo

After M0 has installed the pinned SRT dependency, build the separate ROS image:

```sh
python3 tools/run_m2.py --build-image
```

For the already qualified local image, omit `--build-image`. That option builds
and qualifies a new candidate environment, recording its actual immutable digest
and package versions; it does not rewrite the accepted baseline. The runner builds/installs the standalone CMake SDK, then builds
only `ros2/` with colcon against that installed SDK. It runs bounded CDR tests and
a scenario with robot/operator containers on a temporary internal Docker network.
ROS domains 41/42 and localhost-only DDS discovery prevent a direct DDS path;
SRT connects over the containers' non-loopback IPs. There are no published host
ports. Each run retains source hashes, commands, package versions, logs, fault
coordination and results under `.local/m2/`. Containers/network and the temporary
private passphrase file are removed on exit. `--skip-build` is for development
reruns and is not qualification evidence.

The robot publishes `/robot/imu` and `/robot/joint_states`. The listener republishes
`/remote/robot/imu` and `/remote/robot/joint_states` using Best Effort, Volatile,
KeepLast(1). The adapter checks local ROS type hashes, UTF-8 strings up to 64 bytes,
at most six joints, consistent array dimensions, the qualified CDR1 layout and
the 928-byte envelope payload limit before admission/deserialization. The original
ROS header is preserved. Publication also rechecks the active session, sensor
generation, clock qualification and deadline immediately before publishing.

The operator exposes `/bridge/execute_command` and `/bridge/get_command_status`.
An Execute response of `QUEUED` means volatile local admission; durable ACCEPTED,
DISPATCHING and terminal results arrive through GetCommandStatus. Use `refresh`
to request reconciliation of cached nonterminal status. Request IDs are nonzero
16-byte values and must remain stable for the same intent. Route 100 sets an
absolute measurement rate with expected/new device generations.

The supervised `ros_rate_worker` owns the receiver journal and calls the local
`/robot/apply_measurement_rate` service after the SDK's atomic start authorization.
A matching device result is required for SUCCEEDED. An unobserved reply or worker
crash after dispatch becomes UNKNOWN and is never blindly replayed. The simulator
runs separately, applies the rate to its actual sensor timer, and keeps a bounded
request-ID/hash history while it is alive. Its history is not durable across a
simulator restart. The demo's delayed-response fault models an effect whose reply
is lost; it is not a production device driver.

`/bridge/state` reports local diagnostics. Credentials are read from a private
regular file, rather than ROS parameters or command arguments. The laboratory DDS
service path assumes trusted processes within each local ROS domain; WAN SRT
protection does not authenticate local DDS participants. This demo qualifies local
Linux functionality, not WAN performance, physical device safety or Intrinsic.

## M3 network measurements (in progress)

PR #1 contains the merged M0–M2 implementation. M3 now has an isolated SRT
measurement harness; the complete DDS comparison and deterministic FEC fault
matrix remain open. The planned profiles/seeds are in `baselines/m3-plan.json`.

After M0 has installed the pinned SRT archive, run:

```sh
python3 tests/test_m3_tools.py
python3 tools/run_m3.py --build-image --profile N0 --smoke
python3 tools/run_m3.py --profile N0
python3 tools/run_m3.py --profile N1 --seed 1701
```

The default N0 run is five minutes; N1/N2 default to ten minutes per selected
seed. `--smoke` selects 15 seconds and `--seconds` selects a development duration.
Both stay development evidence. `--skip-build` reuses M3 binaries and is also
explicitly marked. The runner never declares complete M3 acceptance.

`containers/m3.Dockerfile` uses the pinned public ROS base and M0 development
package versions. It builds iproute2 6.17.0 from a hash-checked upstream archive
because the older distribution `tc` lacks netem's seed option. Each run records
the actual immutable image, full package inventory, kernel, qdisc readbacks,
source hashes, per-process resource samples, packet accounting and results in
`.local/m3/`. No host qdisc is changed. Only newly created endpoint containers
receive NET_ADMIN; they use an internal Docker network without published ports.
ROS domains remain 41/42 with localhost-only DDS discovery. Packet capture also
checks that no RTPS traffic appears on the SRT network.

N1/N2 apply delay, normal-distributed jitter and seeded random loss to each
endpoint's whole `eth0` egress. The robot direction uses the selected seed and
the operator direction uses seed + 1. Seeds fix PRNG inputs, not application
scheduling or exact packet identities across runs. N0 is neutral netem, enabling
N4 loss/restore transitions without changing qdisc kind. N4 currently injects a
mid-window outage; command-commit barrier timing is still pending. For example:

```sh
python3 tools/run_m3.py --profile N4 --smoke --outage-direction robot
python3 tools/run_m3.py --profile N5 --smoke
```

N5 applies a shared 512 kbit/s TBF per direction and iperf3 `-b 128K` competing UDP from
robot to operator (131,072 bit/s target). The child netem queue is capped at 16 packets; its packet cap
is authoritative after replacing the TBF's default child queue. The workload
keeps the simulator's configured rate at 200 Hz and requests absolute 200 Hz
with a new device generation every two seconds. An uncertain result pauses new
commands; the harness does not guess the device generation or replay the intent.
Actual received rates and payload-counter gaps are recorded, not assumed to
match configured timer rates under emulation.

Age histograms round conservative bridge-ingress age upper bounds up to 1 ms.
They include all publications in the last received diagnostic snapshot, including
startup/transients, and expose exact maximum upper bounds. Up to one diagnostic
interval of tail is not represented; observer counts are retained separately.
Unknown-age and stale rejections are counted separately. Configured clock
assumptions are explicit: 1000 ppm drift, 1 ms timing error, 5 s maximum probe age
and 200 ms maximum interval width for the impaired runs, with the same 250 ms
sample budget. M2's default interval-width limit remains 50 ms.

Command latency includes local Execute invocation through terminal status
observation and up to 200 ms polling. Unresolved/non-admitted attempts are counted
separately. CPU uses process tick deltas; summed RSS can count shared pages more
than once. Packet counts distinguish FEC parity (reserved SRT DATA message number
zero in the pinned provider) from source DATA and SRT protocol controls. Byte
counts are captured Ethernet frame lengths, excluding physical-link overhead;
egress capture occurs before qdisc drops. Capture loss/rotation is checked rather
than silently omitting packets. Raw pcap files and journals stay ignored locally.

These are SRT development measurements. N3, the fully journaled DDS baseline,
the three-seed duration matrix, and final window/rate qualification must pass
before an M3 comparison or performance claim is accepted.

The [sensor-cadence follow-up](evidence/m3-sensor-cadence-2026-11-05/README.md)
identifies a major N0 gap cause: a 10 ms owner wait coalesced the 200 Hz producer
in a latest-only mailbox. Active callers now use a bounded 1 ms wait. Five-minute
N0 IMU gaps fell from 49.24% to 1.38% within observed source-counter spans, with
all 150 commands confirmed. CPU observations and remaining gaps are disclosed;
this is not a lossless/full-rate or DDS performance claim. Per-route ingress and
BUSY/obsolete submission counts plus final test-observer snapshots help attribute
remaining losses. The latest follow-up evidence supersedes the earlier open
hypothesis about the major gap cause while preserving the original measurements.
