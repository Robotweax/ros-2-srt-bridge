# ROS 2 SRT Bridge

Selective WAN bridge for ROS 2: Robotweax SRT SENSOR carries current small
samples; CONTROL carries acknowledged application commands.

[Bridge repository](https://github.com/Robotweax/ros-2-srt-bridge) owns M0–M3.
The later M4 adapter belongs in
[intrinsic-core-srt-integration](https://github.com/Robotweax/intrinsic-core-srt-integration).
SRT is a separately installed dependency; the enclosing SRT checkout is preserved.

## Development status — 2026-11-09

Current delivery focus: [DELIVERY_PLAN.md](DELIVERY_PLAN.md). M0–M2 are accepted
for the documented simulator baseline; M3 remains open. The bounded probe cohort
closed the instrumentation loop (N0 8/8, N5 128/128). The
[sender receipt change](evidence/m3-sender-reconciliation-2026-11-09/README.md)
now carries actual local abandonment to the exact sender journal row as
UNKNOWN/reconcile_required, preserving query-first recovery, peer results and
one-use tickets. SDK81/ROS41/host399 checks pass. It prevents tracking-capacity overflow from leaving an orphan
journal row. Private worker IPC4 requires matched SDK/ROS workers; the new
`sender-reconcile` install layout preserves earlier calibrated builds.
The [30s N3 follow-up](evidence/m3-n3-thirty-second-matrix-2026-11-09/README.md)
is audited FAIL after five passing cases: three source slots skipped in case6;
the harness now enforces that missed gate (host402). Three later executions are
excluded from cohort qualification. Next: loaded DDS discovery/comparison and
consolidated acceptance; no automatic N3 retry. No tuning, forced expiry or historical118 replay. PR2 stays draft;
Intrinsic/M4 has not started. Older entries below retain their historical scope
and are not the current work queue.

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
UNKNOWN recovery after lost replies and a two-second bridge outage. M3 qualification
is in progress; performance comparisons remain unqualified and M4 has not started. See [evidence](evidence/m0-2026-11-04/README.md)
and the [handoff](HANDOFF.md) for exact scope and next work.

M1 is complete for the documented Linux amd64 baseline. The
[M1 acceptance matrix](evidence/m1-errors-sdk-2026-11-05/ACCEPTANCE.md) maps each
requirement to retained checks and states the qualification limits.

The earlier [remaining N5 seeds and telemetry diagnosis](evidence/m3-broader-seeds-telemetry-2026-11-08/README.md)
records125/125 command successes for1701 and97/98 for2903, with one unresolved
intent and both command gates failed for2903. Prior4211 remains136/136 in its
separate cohort. Telemetry remains poor and varies by seed; identical closed-tap
packet multisets and qdisc/retirement observations narrow investigation without
proving a unique provider cause. Runtime/provider unchanged, host282 PASS; PR2 draft.

The [session2903 reproduction and SENSOR visibility](evidence/m3-session-sensor-visibility-2026-11-08/README.md)
adds a separate default-off provider stream. N0 passes8/8; instrumented N5 fails
11/12 with intent12 unresolved. Matched monotonic observations show5.0046s old-
CONTROL-flow silence despite successful sender send accounting, then late egress.
SENSOR counters narrow a separate acceptance/window gap. Exact local-path/provider
reasons remain unproved; SDK72/ROS41/host296 pass, PR2 stays draft.

The [UDP/neighbor/qdisc isolation cohort](evidence/m3-udp-neighbor-qdisc-2026-11-08/README.md)
passes N0 8/8 and N5/2903 126/126 with24 skipped slots. It distinguishes a
pre-PASS stall with PROBE/INCOMPLETE neighbor samples from post-PASS stalls with
root queue pressure; an idle gap with no sender activity stays a negative control.
No tuning or runtime/provider rebuild; host306 PASS. The earlier failure remains
unresolved and M3/PR2 remain incomplete/draft.

The [controlled ARP reply-loss fixture](evidence/m3-controlled-arp-reply-loss-2026-11-08/README.md)
qualifies a counted PIPE→DROP path:2 generated peer replies drop before the taps;
restoration delivers all3 originally queued UDP identities once and a distinct
fresh control. Clean and scoped loss cases pass; the first broader capture fixture
remains failed. Host317 PASS, runtime/provider unchanged, no tuning or new N5 claim.

The [loaded ARP eligibility cohort](evidence/m3-loaded-arp-eligibility-2026-11-09/README.md)
passes N0 8/8 and N5/2903 134/134 with16 skips. A separately marked audit of all
positive reply increments finds8 robot read envelopes with eligible/PASS growth
but no reply source hook, alongside root pressure. This is downstream absence or
delay, not8 proved packet drops or a fixed historical failure. Host327 PASS;
runtime/defaults unchanged, no tuning, PR2 draft.

[Packet-level ARP tracing](evidence/m3-arp-packet-tracing-2026-11-09/README.md)
now distinguishes13 actual qdisc drops from5 queued replies arriving after the
18 missing-tap counter windows in a new N5 cohort. Full tracing records16 robot
reply drops and10 driver starts; seven survivors queue69–114ms. Zero observer
loss/pending, no tuning. N0 passes8/8; N5 progress **fails** with121 successes and
one REJECTED/context_lost command34,28skips. Host341 PASS; original failures and
UNKNOWNs remain, M3 incomplete/PR2 draft. Next: worker/start-fence rejection
diagnosis before any separately planned mitigation.

[Command34 start-fence diagnosis](evidence/m3-command34-start-fence-2026-11-09/README.md)
finds a13.48ms admission clock margin, with dispatch0.447ms past that observed
clock deadline and4.872s of original budget left at rejection. Only34 crosses
that boundary among122 attempts. Actual grant/consume/start-check decisions were
not logged, so coordinator refusal versus worker gate remains unresolved. The
isolated probe and three existing execution tests pass; host350 PASS, all
installed binaries unchanged. No tuning or N5 retry; targeted start-stage
visibility is next.

[Targeted start tracing](evidence/m3-start-tracing-2026-11-09/README.md) is now
implemented and calibrated: actual check/grant, execute submission, consume and
second-gate observations distinguish coordinator refusal from worker rejection.
Default-off flags require command diagnostics and matched rebuilt workers. New
isolated SDK75/ROS41/host364 checks pass; the installed baseline remains fixed.
No tuning or new N5 run; a prospective cohort with the matched new baseline is
next, while command34's historical branch remains unrecorded.

The [prospective matched-build cohort](evidence/m3-loaded-start-tracing-2026-11-09/README.md)
now passes N0 8/8 and N5/2903 129/129 with21 skipped slots. All137 starts join
actual grants/consume/gates to closed successful journals; N5 minimum gate
headroom587ms, no rejection recurrence. New command48 records a later clock
qualification deadline than admission. ARP tracing retains9 drops and2 delayed
reply windows; telemetry remains unqualified. No tuning/rebuild/old-baseline
replacement; host374 PASS, matched SDK75/ROS41 reused. Next predeclare broader
seed coverage; original34 and earlier UNKNOWNs remain unresolved, PR2 draft.

The [predeclared additional-seed cohort](evidence/m3-start-broader-seeds-2026-11-09/README.md)
stops at N5/1701:117/118 successes,32skips, intent118 unresolved;4211 stays
NOT_EXECUTED. N0 passes8/8. Complete start traces show117 successful worker
starts;118 instead has source clock deferral and a deadline-dropped pending input
before any recorded SDK handoff. Closed sender retains UNKNOWN/reconcile_required;
no expiry or replay is inferred. Host376 PASS, exact matched builds/settings fixed,
no tuning/retry. Next diagnose sender clock qualification and journal reconciliation.

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

The [window-accounting follow-up](evidence/m3-window-accounting-2026-11-05/README.md)
now fences source publication and takes stable, drained snapshots through local
`/robot/set_publishing` and `/bridge/get_metrics` services. Fresh-session startup
excludes warmup sensor/FEC history. Owner epochs detect resets; six conservation
equations account for every sample, and age histograms use window deltas. These
services are local ROS measurement controls, not additional bridge wire messages.

The phase-preserving simulator achieves 199.96/50.00 Hz in the latest five-minute
N0: 75,011 produced, 72,372 observed, 2,639 classified losses (mostly outbound
pacing replacements), zero unaccounted samples, 150 confirmed commands/effects.
The short N5 smoke has two confirmed commands and one unresolved; it does not
qualify command completion under congestion. Command summaries include a bounded
post-cutoff result drain, identified per row. CPU/capture totals still cover the
whole observation rather than the exact sample window. DDS comparison, N3,
N4 command-phase barriers and the full duration/seed matrix remain pending.

A sensor-only DDS development baseline is available separately:

```sh
python3 tools/run_m3_dds.py --smoke
python3 tools/run_m3_dds.py --profile N0
python3 tools/run_m3_dds.py --profile N1 --seed 2903 --smoke
```

It uses the same pinned M3 image, simulator, profile readbacks and capture checks,
with direct typed Best Effort/Volatile/KeepLast(1) DDS on a shared domain inside
an internal Docker network. Explicit static peers establish discovery without
relying on Docker multicast delivery. No host networking or published ports are
used. Source pause/resume checkpoints fence publication; observer counts partition
pre-callback losses, invalid, stale, clock-rejected and accepted samples.
Discovery endpoints verify publisher Best Effort/Volatile QoS; discovered history
and depth can be unknown, so the depth-one configuration is also retained locally.

This runner is explicitly sensor-only: it sends no measurement-rate commands and
does not qualify Reliable command behavior. Source control files contain fence
counts/timestamps, never sensor payloads. Age is a shared-VM realtime-header
estimate, with bracketed monotonic clock checks; it is not the SRT conservative
clock-interval bound. The runner checks common boot/time namespaces; observed clock steps disqualify
age estimates while preserving sensor count accounting. Capture totals include discovery/control traffic;
fragment frames are counted separately without RTPS payload attribution. Default
SRT capture handling still rejects fragmentation. CPU/wire windows, equivalent
security/command workloads and the full matrix remain pending; these DDS results
support harness validation, not a performance advantage claim. See the
[DDS sensor evidence](evidence/m3-dds-sensors-2026-11-05/README.md).

The journaled DDS command coordinator now has a separate development acceptance
runner:

```sh
python3 tools/run_m3_dds_commands.py
```

`dds_command_node` uses Reliable/Volatile/KeepLast(64) fixed control frames and one
bounded journal worker thread per endpoint. It shares the SDK `CommandJournal`
and ROS rate handler with SRT. New intents commit before send; duplicates and
recovered intents query instead of resending. A common-VM namespace proof,
acknowledged nonce-derived session, 1.5 s lease and mutex-protected start claim
fence receiver execution. Lease expiry rotates the link nonce, including when
both processes survive. The SRT SDK, ticket/start fence and wire/IPC formats are
unchanged.

The [DDS command evidence](evidence/m3-dds-commands-2026-11-05/README.md) records
four distinct intents/four effects: two confirmed successes and two UNKNOWNs from
a lost handler reply and a receiver crash. Sender SIGKILL/reopen issued QUERY
with zero replayed old COMMANDs. Both journals agree after recovery. Eighteen
ROS GTests, nineteen Python tests and the original M2 regression passed. A callback
admission drop remains visible; Reliable middleware is not guaranteed application
queue admission. This is common-VM command acceptance with changing sensor rates,
not the complete steady M3 comparison. Combining the steady sensor/command
workload, qualifying cross-host clocks/security and aligning CPU/wire windows
remain next.

The combined steady DDS workload is now available:

```sh
python3 tools/run_m3_dds.py --commands
python3 tools/run_m3_dds.py --commands --profile N1 --smoke --skip-build
python3 tools/run_m3_dds.py --commands --profile N4 --smoke --skip-build
```

It keeps the source at 200/50 Hz and offers absolute 200 Hz intents every two
seconds, with one pending intent and no replay. NOT_READY/BUSY are explicit
non-admissions. At cutoff it stops new intents, observes pending results for at
most eight seconds, freezes the command population and takes a final device
fence. Command effects can advance during drain; sensor counts must stay fixed.
Rows identify post-cutoff results, and unresolved outcomes remain separate.

A long run exposed an ordinary mutex-contention drop in the DDS callback. Incoming
frames now serialize short validation/copy critical sections; a genuinely full
64-slot inbox still records a drop. Local service admission keeps try-lock/BUSY.
The queue, lease, deadlines and no-replay rules are unchanged. The capture parser
also accounts for valid four-byte terminal IP fragments without requiring a UDP
header there; SRT fragment rejection remains the default.

The final five-minute N0 confirms 150/150 commands with 150 effects and no SDK
inbox drops, at actual 199.978/50.002 Hz. It produces 75,026 samples and receives
75,025, with one pre-callback IMU gap. Its age estimates are unqualified after an
observed clock step; received samples are not relabeled as network losses. N1 has
one non-admission; N2/N4 each retain an unresolved intent; N5 times out during
cold-start readiness under congestion. These remain qualification limits.
See [combined evidence](evidence/m3-dds-combined-2026-11-05/README.md). Nineteen ROS
GTests and 27 Python tests passed, plus sensor-only and crash/lost-reply regressions.
Full seeded durations, DDS readiness, clock/security equivalence and matched
CPU/wire windows remain open; no performance advantage is claimed.

The readiness follow-up separates ephemeral HELLOs from ordered command traffic:
Best Effort/Volatile/KeepLast(1), a dedicated 100 ms liveness thread and independent
replay cursors; controls remain Reliable/Volatile/KeepLast(64). Expired sessions
rediscover with an empty target before requiring mutual current-nonce ACKs.
Readiness includes journal and local ROS handler eligibility. Matched endpoint,
HELLO, lease and eligibility diagnostics make startup failures observable. Both
DDS peers must rebuild; SDK wire v1, private IPC v3 and SRT remain unchanged.
Workers stop before ROS context shutdown, and the nested handler context outlives
the joined worker. The original five-second shutdown check remains enforced.

Two explicit lab options preserve the existing defaults:

```sh
python3 tools/run_m3_dds.py --commands --profile N5 --startup control-first --smoke --skip-build
python3 tools/run_m3_dds.py --commands --profile N5 --dds-profile udp1200 --smoke --skip-build
```

Control-first holds source publication until command readiness, then warms up
and measures with the same fences; impairment and the N5 competitor stay active
throughout. It does not qualify joining an already-streaming system. The separate
1200-byte transport experiment removed IP fragmentation but still failed N5
startup. Simultaneous startup and the system transport remain defaults. Completion
under N2/N5 varies; unresolved intents still block new work without replay.
See the [readiness evidence](evidence/m3-dds-readiness-2026-11-05/README.md) for
final runs, fault repeats, failed experiments and remaining M3 gates.


The follow-up five-minute N0 confirms 150/150 commands and 150 effects at actual
199.976/50.002 Hz, with 75,025 samples produced and 75,022 received (three IMU
gaps before callbacks). Its shared-VM age checks pass. Both closed journals agree
on all 150 results. Twenty-three actual ROS GTests, 30 Python tests, three
consecutive crash/lost-reply fault runs, sensor-only and a full M2 rebuild pass.
N4 regains readiness after lease expiry at both peers; an unresolved intent stays
unreplayed. Final N2 retains one unresolved intent despite both peers being ready;
N5 simultaneous startup still fails with partial/asymmetric discovery. These
remain M3 gates; control-first is an explicit limited startup variant.

The [completion diagnosis](evidence/m3-dds-completion-2026-11-05/README.md) now
records why a command can remain unresolved despite live peers. Session checks
report rejection reasons and the last stale COMMAND; receipt-matched NOT_FOUND
responses and Reliable publish-call duration are counted separately. Workload
rows retain the last local status/error instead of hiding that information behind
a pending row. A five-second observation age or NOT_FOUND never manufactures a
terminal result or permits replay. Three short N2 seeds exercise these diagnostics;
they do not replace the full impaired qualification matrix. The freshness cutoff,
start gates, workload and default DDS configuration remain unchanged.


DDS command protocol v2 now supports receiver-backed expiry sealing. A
`SEAL_EXPIRED` request can only close an unacknowledged intent in its original
live sender/process/session, strictly after the stored deadline. An existing
receiver record is returned unchanged; an absent ID is durably recorded as
EXPIRED before replying, without dispatching. A later COMMAND cannot start that
ID. After restarts or session rotation, old intents remain QUERY-only. Both DDS
endpoints must rebuild; the SDK, SRT, wire v1 and IPC v3 are unchanged.

The three short N2 probes now have zero unresolved intents: 76 successes and two
authoritative expiries, kept separate. The five-minute N0 confirms 150/150 with
150 effects. All 32 actual ROS GTests, 33 Python tests, DDS fault acceptance and
a full M2 rebuild pass. N4 cross-session uncertainty and N5 simultaneous startup
remain open. See [expiry-seal evidence](evidence/m3-dds-expiry-seal-2026-11-05/README.md).
The extra DDS reconciliation semantics/costs still need SRT comparison parity;
M3 remains incomplete.


An explicit `paced-sensors` DDS lab profile now reaches simultaneous N5 readiness
with telemetry already streaming:

```sh
python3 tools/run_m3_dds.py --commands --profile N5 --dds-profile paced-sensors --smoke
```

Only the two sensor writers use asynchronous publication and a shared
1600-bytes/50-ms controller. Controls retain their QoS and default publication
mode. A standalone native provider preflight verifies the applied settings in
an isolated container. Source production stays at 200/50 Hz; fewer sensor updates
reach callbacks. The profile changes egress policy and is not a lossless result.

The five-minute N5 probe confirms 150/150 commands with 150 effects; three smoke
seeds each confirm 8/8. The long run produces 75,025 samples and receives 19,128,
all passing its shared-VM age estimate gate. System and UDP-1200 still fail cold
readiness. The default remains system. The N5 runner validates whole-run offered
competition and checks process liveness; matched-window delivery remains open.
35 Python checks, native positive/negative checks, paced fault acceptance and
N0/sensor regressions pass. Production compiled sources and binaries are unchanged.
See [paced-profile evidence](evidence/m3-dds-paced-sensors-2026-11-05/README.md).
SRT pacing/reconciliation cost parity, clock/security and CPU/wire/matrix gates
remain open; M3 stays in development.


### Shared endpoint measurement windows (2026-11-06)

Both M3 runners now sample Linux endpoint process trees every 250 ms, including
source, bridge/control workers and the test observer/sampler. They report two
common phase definitions: source-enabled publication and the broader resume
request through command drain/stable final sensor checkpoint. Startup/shutdown
are excluded. Existing SRT whole-run resource summaries retain their old scope.

CPU uses observed inner/outer tick deltas without interpolation; sampled summed
RSS can double-count shared pages and is neither PSS nor a hard peak. Process
identity changes, read errors, regressed counters, reaped-child work or sampling
gaps invalidate CPU qualification. Unobserved short-lived children remain outside
this accounting. Capture/competitor processes are excluded, but their host load
still affects the workload.

Windowed Ethernet accounting requires a common realtime clock envelope from both
endpoints. It is conditional on no hidden clock steps, at most 1000 ppm relative
drift, bounded calibration gaps/read widths and capture timestamp quantization.
Packets are separated into certain-inside, uncertain-boundary and outside bins.
Rejected calibration produces no windowed wire totals; whole-run capture gates
still apply. These are phase costs including coordination, not isolated transport
or source-population byte attribution.

See [window evidence](evidence/m3-window-measurement-2026-11-06/README.md).
M3 remains in progress; clock-qualified wire comparison is still open.


Clock follow-up: calibration now runs independently on scenario polls (25-ms
minimum spacing), while process scans remain at 250 ms. Current runners require
the dedicated clock files and reject calibration gaps over 100 ms. The 1000 ppm
model is unchanged; finite sampling still cannot rule out hidden clock steps.
A regression demonstrates a 150-us step accepted by 250-ms samples but rejected
by 50-ms samples. Legacy process-clock reanalysis remains explicitly labelled.

A standalone read-only native/Python clock diagnostic is available; see its
[recipe and evidence](evidence/m3-clock-diagnosis-2026-11-06/README.md). It compares
libc/direct-syscall realtime with Python and checks raw/boottime offsets, without
setting clocks or requiring network/capabilities. A finite diagnostic pass does
not qualify a later workload. VM clock control and a monotonic packet-timestamp
path remain possible follow-ups, subject to evidence.


### Experimental kernel-monotonic packet observer

`--monotonic-capture` on either M3 runner adds a passive AF_PACKET socket observer
inside each owned endpoint. It timestamps observations with `bpf_ktime_get_ns`
in the kernel and accounts UDP frame lengths over the existing source-enabled
and fenced-observation phases, independently of realtime clock drift. The
realtime capture path and its rejection gates remain intact.

```sh
python3 tools/run_m3.py --profile N0 --smoke --monotonic-capture
python3 tools/run_m3_dds.py --commands --profile N5 --dds-profile paced-sensors --smoke --monotonic-capture
```

Normal runs build the standalone observer using the pinned image's g++/libbpf.
Development `--skip-build` requires that binary. The flag adds CAP_BPF only to the
owned endpoint containers; default runs retain their original capabilities.
No privileged container, host interface, tc/XDP hook, clock setting or new image
is needed. Zero time-namespace offsets, capture coverage and zero recorder loss
are required. A bounded ring and 128-MiB output cap fail closed on exhaustion.

These are kernel socket observation times and skb frame lengths, not physical
link transmission/delivery or sensor-population overhead. Capture processes are
excluded from endpoint CPU, while kernel observer work may be charged to endpoint
tasks; the added observer changes host load. Results therefore identify this
capture variant explicitly. See [implementation and evidence](evidence/m3-monotonic-capture-2026-11-06/README.md).


### Container resource scope and observer study

M3 phase summaries now include read-only `container_cgroup` CPU and charged-memory
observations alongside the narrower endpoint-process totals. This scope includes
capture and competitor processes; work accounted outside the container is still
excluded. Inner/outer observed CPU deltas are not exact physical bounds. Sampled
charged memory includes cache/kernel memory and is not RSS/PSS or a hard peak.
Missing/changed cgroups and invalid counters reject resource qualification without
changing command execution gates.

`python3 tools/m3_observer_study.py --out .local/m3-observer-study/new-run`
preregisters and executes balanced sequential N0 observer on/off blocks, then
three five-minute paced N5 repetitions. It reuses the installed development build,
freezes sources and retains failures. See the [study design and evidence](evidence/m3-observer-study-2026-11-06/README.md).
Results describe this shared emulated VM; they do not establish isolated observer
cost or controlled SRT/DDS performance.


### Tap/offload scope correction

Controlled Linuxkit/veth probes place the egress socket tap after the tested
netem drop/delay and the receive tap before the tested ingress drop. The older
`pre-qdisc` scope label is corrected; historical artifacts keep their original
text and require this qualification when interpreted.

Capture artifact v2 records GSO/VLAN metadata and MTU. One segmented UDP send can
appear as one large skb while delivering eight datagrams, so `frame_interpretation`
is separate from observation qualification. Opt-in runners snapshot interface
features read-only; old v1 metadata remains explicitly unknown. Physical frame
bytes/delivery are still outside this accounting.

PCAP mode is now immediate, with ordered load-stop/drain. Captured/file counts
and kernel-drop gates remain required; filter-counter population reconciliation
is tracked separately. Unreconciled PCAP populations withhold realtime window
summaries. The independent native observer retains its own loss/coverage gates.
See [tap/offload evidence](evidence/m3-tap-offload-2026-11-06/README.md). The earlier
observer-cost study applies to v1/buffered mode; v2/immediate costs need separate
qualification.


The observer-study helper now pins immediate PCAP mode, v2 records on opted-in
runs, a common VM boot, and selected installed binary hashes. Mixed measurement
variants are rejected. `--skip-long-n5` explicitly omits long N5 repetitions;
`--impairment-seconds 60` appends short SRT/DDS N1/N2 development probes. See the
[v2 study evidence](evidence/m3-v2-observer-impairments-2026-11-06/README.md).
These shorter probes do not satisfy the full duration/three-seed matrix.


The immediate PCAP fixture now requests a 32,768-KiB buffer while preserving full
snapshots and enabled offloads. On the pinned veth/libpcap setup this yields 512
fixed packet slots and a 64-MiB allocation per capture, versus 64 slots/8 MiB for
the earlier 4,096-KiB request. A controlled reader-pause experiment verifies the
capacity difference; kernel-drop rejection remains strict. Capture configuration
is recorded and included in study comparisons. The failed smaller-buffer study
is retained in the [v2 evidence](evidence/m3-v2-observer-impairments-2026-11-06/README.md).

The [v2 observer and short impairment evidence](evidence/m3-v2-observer-impairments-2026-11-06/README.md)
retains the failed smaller-buffer study and the controlled buffer diagnostic.
A fresh twelve-case plan passed with zero PCAP kernel drops and native recorder
losses: 299 confirmed commands/effects. DDS N2 skipped five command slots and
observed a 10.87-second maximum terminal-status latency. These short probes do
not complete the duration/seed matrix or establish isolated observer CPU cost.

The [DDS status-timeline follow-up](evidence/m3-dds-status-timeline-2026-11-06/README.md)
separates receiver finish from late sender result observation and adds bounded
status-poll history. Three further 60-second N2 seeds ended with 82 successes/
effects and two receiver-backed expiries without dispatch; no unresolved intents.
Terminal observation still reached 8.46 seconds. Analyze a closed combined DDS
run with `python3 tools/m3_dds_result_timeline.py RUN --out FRESH_OUTPUT.json`.
The tool requires common-VM/zero-offset proof and checkpointed journals; timestamp
stages are observations before commits, not execution or delivery guarantees.

The [full-duration default DDS N2 cohort](evidence/m3-dds-n2-full-2026-11-06/README.md)
executes all three seeds for 600 seconds each: 830 successes/effects, 12 expiries
without dispatch, one BUSY admission rejection and 57 skipped slots, with no
UNKNOWN or unresolved intents. All capture integrity gates pass. One seed's age
estimates fail clock qualification, so the N2 age gate and full M3 acceptance
remain open. Sources and installed binaries are unchanged from `eb46aba`.

The [full-duration SRT N2 cohort](evidence/m3-srt-n2-full-2026-11-06/README.md)
completes all three 600-second seeds with 900 confirmed commands/effects and no
uncertain, expired or skipped intents. Six journals agree; source-fenced balances
and twelve cgroup windows replay exactly. The largest measured publication-age
upper bucket is 168 ms against the 250-ms gate (bridge-ingress origin). Capture
recorder gates pass; realtime packet windows remain unqualified. Runtime code is
unchanged. These separate SRT/DDS cohorts do not establish transport superiority.

The [full-duration SRT N1 cohort](evidence/m3-srt-n1-full-2026-11-06/README.md)
completes all three 600-second seeds: 900 confirmed commands/effects, no uncertain
or skipped intents, maximum measured publication-age upper bucket 119 ms against
the 250-ms gate. Six journals and all source/cgroup replays agree. All 83 host
Python tests pass. Main M3 captures now retain sixteen 16-MB files (256 MB nominal)
and record this configuration; a controlled overwrite probe preserves the strict
file-integrity gate. Compiled binaries/policies are unchanged. Realtime packet
windows and full M3 acceptance remain unqualified; full DDS N1 is next.

The [full-duration default DDS N1 cohort](evidence/m3-dds-n1-full-2026-11-06/README.md)
completes three 600-second seeds: 890 successes/effects, two expiries without
dispatch and eight skipped slots, with no UNKNOWN or unresolved intents. Six
journals agree and twelve cgroup windows replay exactly. One seed fails age
qualification on clock steps; realtime packet windows remain withheld.
The [execution matrix](evidence/m3-dds-n1-full-2026-11-06/execution-matrix.json)
now covers all four SRT/DDS N1/N2 duration/seed cohorts. This closes execution
coverage, not the age/security/comparison gates or full M3 acceptance. Runtime
sources and binaries are unchanged from `e3c5c70`.

Current-capture [paced DDS N5 repetitions](evidence/m3-dds-paced-n5-v2-2026-11-06/README.md)
pass three 300-second runs with 450 confirmed effects. This is an explicit tuned
profile; default DDS N5 discovery remains open. The [separate SRT N5 plan](evidence/m3-srt-n5-v2-2026-11-06/README.md)
passes one run, then stops on real PCAP kernel drops and one unresolved intent;
its third seed is unexecuted. The SRT runner now enforces competitor liveness and
offered-load gates, with a deliberate competitor-stop negative test and 83 passing
host tests. Failed recorder data and command uncertainty are retained, not retried
or reclassified as success. Full SRT N5/M3 acceptance remains open.

Recorder development diagnostics are available through `tools/run_m3.py
--recorder-diagnostics` (opt-in; adds observer workload). Controlled pause/recovery
and separate 60-/30-second N5 cases are recorded in
[`evidence/m3-recorder-diagnostics-2026-11-06/`](evidence/m3-recorder-diagnostics-2026-11-06/).
The 60-second case retained an unresolved command despite zero capture drops;
the 30-second case verified bounded SRT poll histories with 12 successes.
All 88 host tests pass. These development cases do not replace the failed frozen
SRT N5 cohort or resolve historical intent 105; PR #2 remains draft and M3 incomplete.

Command handoff diagnosis found and fixed an unsent command being discarded
when clock qualification briefly failed. The transport now retains its reserved
ingress slot and original proof/deadline until qualification recovers, with
expiry/revocation/context guards preserved and no SDK-accepted command replay.
Opt-in `--command-diagnostics` records bounded handoff/lifecycle observations.
[Evidence and regression results](evidence/m3-command-handoff-2026-11-06/) retain
the pre-fix failure and separate post-fix 90-second N5 case: 32 successes/effects,
two recovered clock deferrals, zero unresolved commands or capture drops.
68 SDK CTests, 36 ROS-reported tests and 92 host tests pass. Full SRT N5/M3
qualification and historical uncertainties remain open; PR #2 stays draft.

The [subsequent full-duration N5 cohort](evidence/m3-srt-n5-fixed-2026-11-06/)
passed its first case and stopped at its second on one missing diagnostic record;
the third case was not run. Both executed 300-s cases completed all commands:
244 successes/effects total, no unresolved intents and zero packet-recorder drops.
The diagnostic gate remains strict. The trace buffer now uses independent bounded
writer lanes; focused native/ROS tests and a separate N0 smoke pass. A fresh full
N5 cohort is still required for that new trace configuration. M3 remains incomplete.

The [independent-trace N5 cohort](evidence/m3-srt-n5-spsc-2026-11-06/) retained
every trace and packet record but stopped on a live session change and one
unresolved command: 14 successes/effects, intent 15 UNKNOWN, other two cases not
run. New opt-in events now distinguish provider link-loss causes from session-
close decisions; controlled peer-close tests and a separate N0 smoke pass.
Five focused native tests, 36 ROS-reported tests and 93 host tests pass. Next is
cause-tagged reproduction of the reset; full N5 and M3 qualification remain open.

The [single cause-reproduction run](evidence/m3-n5-close-cause-2026-11-06/)
did not reproduce the live N5 reset: 133 successes/effects over 300 seconds,
complete traces and zero capture loss. It does not replace the earlier failures.
A new IPv4/IPv6 admission-loss regression confirms UNKNOWN is retained after the
original budget and peer NOT_FOUND, with no replay or effect. The natural reset's
initiator and full N5/M3 qualification remain open; production behavior is unchanged.

[Flow-isolated CONTROL analysis](evidence/m3-control-silence-2026-11-06/) now
shows roughly five seconds of missing old-flow traffic before each historical
session change, consistent with the pinned provider's idle interval. A native
one-way CONTROL silence test exercises provider loss followed by session close on
IPv4/IPv6. Both native tests and 98 host tests pass. The original operator-side
withholding mechanism remains unproven; no timeout, production behavior or failed
qualification verdict was changed.

For bounded development diagnostics, the ROS `provider_diagnostics` parameter
(default `false`) or M3 runner `--provider-diagnostics` records non-clearing
CONTROL provider counters and buffer gauges at a target 100 ms cadence. Read
brackets, socket generations, unavailable samples and queue/budget loss are
explicit. Sampling adds SDK lock/bookkeeping work. Counters omit some UDP packet
types and do not prove delivery. See the prospective
[diagnostic plan](evidence/m3-provider-diagnostics-2026-11-06/diagnostic-plan.json).

An experimental `--control-egress-fault operator|robot` runner option injects a
six-second CONTROL-only egress drop in owned containers. It requires N0 >=45 s
and command/provider/monotonic diagnostics. After a retained tc JSON validation
failure, one fresh planned run validated the corrected harness: provider send
counters grew with zero outgoing CONTROL tap observations during the injected
filter drop, and traffic resumed after removal. One command remains UNKNOWN;
this is diagnostic validation, with historical N5 cause and M3 still open. See
[validation and limits](evidence/m3-control-egress-validation-2026-11-06/README.md).

A subsequent 300-second N5 diagnostic records 126 successful commands/effects,
zero unresolved intents and four CONTROL egress gaps >=1 s. The longest is
4.237 s with increasing provider send counters. Exploratory capture analysis
finds an ARP reply about 20 microseconds before CONTROL resumes, suggesting
neighbor-resolution involvement for further testing. No reset recurred; the
historical cause remains open. [Evidence and limits](evidence/m3-n5-provider-liveness-2026-11-06/README.md).

Optional `--neighbor-diagnostics` and explicit `--neighbor-mode permanent` now
support a separate L2 fixture contrast. Dynamic N5 gaps overlapped sampled
INCOMPLETE states, while the permanent candidate still retained a 1.315-second
positive-counter gap. Historical ARP timing supports neighbor involvement, with
exact cause and remaining gaps open. Dynamic remains the default. [Comparison
and limits](evidence/m3-neighbor-contrast-2026-11-07/README.md).

Experimental `--control-qdisc-diagnostics` adds CONTROL tc PASS counters and
root-qdisc polling. A known-count probe qualifies the counter before tested root
loss and the native tap after it. The live N5 case recorded 129 successful
commands but no >=1s gap recurrence; robot PCAP failed filter/file population
reconciliation by two records. Defaults are unchanged. [Evidence and limits](evidence/m3-qdisc-stage-2026-11-07/README.md).

A finite paused-recorder test now distinguishes accepted-but-unwritten packets
from complete resume/drain capture. Optional `--capture-drain-check` checks stable
live counters before shutdown while preserving the final capture gate. A separate
60-second known child-loss test recovered with 22 successful commands and reconciled
PCAP; it does not repair historical failures or complete M3. [Evidence and limits](evidence/m3-drain-controlled-loss-2026-11-07/README.md).

The explicit N3 source selector has passed [two finite synthetic probes](evidence/m3-sensor-selector-2026-11-07/README.md), including parity sharing a selected source sequence. Authenticated FEC recovery and ROS N3 qualification remain pending; PR #2 stays draft.

[Finite authenticated SENSOR FEC cases](evidence/m3-sensor-live-2026-11-07/README.md) now demonstrate one-packet repair and a separately planned two-loss observation. The original two-loss counter-gate failure is retained; ROS N3 publication/age qualification remains open.

[Finite ROS N3 attempts](evidence/m3-ros-sensor-2026-11-07/README.md) retain two failed baselines: capture stability under live CONTROL, then one accounted sender BUSY drop. ROS injected-loss cases remain unexecuted; actual admission/handoff identity correlation is next.

[Bounded sample handoff diagnostics](evidence/m3-sample-handoff-2026-11-07/README.md) now correlate all 19 samples in one finite observer run across ROS admission, SDK metadata and captures. Earlier failed baselines remain unchanged; actual SDK identities can now guide the pending ROS loss cases.

[Traced ROS one-loss recovery](evidence/m3-ros-traced-loss-2026-11-07/README.md) now passes with exact SDK-to-payload correlation. The second fixture stopped before arming on an8-captured/10-filter capture discrepancy; no two-packet ROS fault ran and the failed evidence is preserved.

[A qualified filter-before-bind recorder candidate and finite ROS two-loss case](evidence/m3-capture-startup-2026-11-07/README.md) now pass:17 of19 admitted samples are observed, with exactly the two selected IDs absent. A controlled libpcap filter-transition probe reproduces a counter-offset class; historical failures and tcpdump defaults remain unchanged.

[Late-repair ordering](evidence/m3-ros-late-repair-2026-11-08/README.md) now records an explicit receiver replay rejection after newer samples were published. The original slow-source attempt remains failed; the passing finite burst verifies ordering, with full-rate multiroute N3 still open.
