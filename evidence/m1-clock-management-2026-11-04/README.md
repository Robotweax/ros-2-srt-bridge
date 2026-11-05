# M1: bounded management and clock model — 2026-11-04

Implemented two more ROS-independent M1 components. The management codec uses
generated Protobuf code behind a bounded preflight validator. The ClockMapper
computes conservative age intervals from four timestamps and explicit clock
assumptions. No session/I/O integration or ROS publication path exists yet.

## Results and reproduction

Run the full core contract checks in the M0-qualified development image:

```sh
python3 tools/run_m1.py
```

Every attempt saves source fingerprints, commands, test inventories, logs and
JUnit files under a distinct `.local/m1/` directory. The runner requires exactly
`wire_contract`, `clock_contract` and `management_contract`, rejects missing or
skipped cases, and runs the contracts in Debug and with ASan+UBSan.

| Check | Result | Evidence |
| --- | --- | --- |
| Linux amd64 Debug | 3/3 contracts pass | [JUnit](debug.xml) |
| Linux amd64 ASan + UBSan | 3/3 contracts pass | [JUnit](asan-ubsan.xml) |
| Default root build, installed SRT | 43/43 cases pass | [JUnit](root-integration.xml) |
| macOS arm64, wire and clock only | 2/2 contracts pass | [Host log](native-host.log) |

The default root run includes the unchanged 40 installed-library profile cases.
Upstream SRT was not changed and its complete upstream suite was not rerun.
Linux execution is Docker Desktop amd64 emulation on Darwin arm64. The immutable
image reference matches the [M0 baseline](../../baselines/dependencies.json).
Protobuf compiler/library: Ubuntu package 3.21.12-8.2ubuntu0.4.

Per native contract in each Linux mode:

- Clock: 35,096 assertions, including 5,000 drift scenarios and subsequent probes.
- Management: 30,074 assertions, including 20,000 deterministic mutations.
- Wire: 22,576 assertions, including 20,000 deterministic mutations.

[run.json](run.json) contains the commands and fingerprints for the tested core
revision. `${PROJECT}` replaces the host absolute project path in the portable
copy. Current source fingerprints match that run. No bridge commit/push exists.
Earlier exploratory runs remain under ignored `.local/m0/` and `.local/m1/`;
no test failures occurred in this continuation.

## Management contract

The codec handles HELLO, WELCOME, READY, BIND, TIME_PROBE and TIME_REPLY.
Before the generated parser can allocate from peer input, the preflight pass
checks the 512-byte cap, known field IDs, duplicate fields, wire types, varint
bounds, exact 16/32-byte identities/digests and 1–64-byte peer IDs. Strings must
be valid UTF-8 without C0/C1/DEL controls or embedded NUL. Semantic validation
then checks fixed MVP limits, distinct nonzero boot identities, known READY
phases and representable/ordered timestamps. Local encoding applies the same
semantic rules and leaves output unchanged on a reported failure.

Version 1 deliberately rejects unknown and duplicate fields; it does not use
Protobuf's permissive unknown-field or last-value-wins behavior. Field ordering
is unrestricted. Scalar zero defaults remain legal, including a zero monotonic
time. Tests include generated-parser interoperability, independent timestamp
wire vectors, all kind-number assertions, field reordering, Unicode, malformed
varints, missing/wrong-size fields, input limits and seeded mutations.

This is structural/semantic validation. Local authorization, expected peer ID,
manifest equality, envelope boot/session bindings and allowed state transitions
must still be enforced by the session layer. COMMAND/STATUS/QUERY and ERROR
payloads remain to be specified with that layer and the command journal.

## Clock contract and assumptions

Each endpoint initiates its own probe, independently of its SRT Caller/Listener
role. t1/t4 are local, t2/t3 remote. The base offset is remote minus local:
`[t3 - t4, t2 - t1]`. This supplies each receiver with its own locally measured
receive timestamp and requires no path-symmetry assumption. Protobuf field
numbers are unchanged; their names now describe Initiator/Responder roles.

The mapper explicitly takes a relative drift bound, timestamp error bound,
maximum probe age and maximum full offset-interval width. It expands probe
bounds for drift/error, projects previous intervals and intersects consistent
new evidence. Event timestamps before and after the probe anchor are transformed
using rate bounds and outward integer rounding. Freshness uses the upper age
bound; unknown freshness has no substituted numeric age.

Broad or expired models deny freshness until qualified by newer evidence.
Epoch/domain mismatch, local time regression, inconsistent probes and arithmetic
overflow invalidate the model until an explicit reset. Entirely future sample
intervals are rejected without poisoning an otherwise valid model. All relevant
arithmetic is checked, including near signed/unsigned 64-bit limits.

The drift scenarios use exact synthetic clocks at -200, -1, 0, +1 and +200 ppm,
both offset signs, asymmetric delays, a 200 ppm configured bound and 1,000 ns
timestamp-error allowance. They test true-age containment before and after the
probe, updated interval intersections, expiration, clock jumps, restarts and
budget boundaries. These tests validate the model; they do not measure host
oscillator drift or qualify live network synchronization. Production assumptions
must be recorded and qualified on the eventual runtime.

The mapper is single-owner. Callers must correlate replies against outstanding
probes and validate message session/epoch/domain before age calculation. Reset
must flush old sample queues. Those integrations are pending, along with the
canonical route manifest, sessions, SRT I/O/reconnect, queues/scheduler and journal.

## Build dependencies

Full standalone core: C++20, CMake 3.20+, Protobuf compiler/library 3.21+.
`RobotweaxBridge::management` links the generated Protobuf implementation;
`RobotweaxBridge::core` contains wire/clock code and has no Protobuf dependency.
The minimal root build explicitly sets `-DBUILD_PROFILE_PROBE=OFF` and
`-DBUILD_MANAGEMENT_CODEC=OFF`; only wire/clock contracts run in that mode.
