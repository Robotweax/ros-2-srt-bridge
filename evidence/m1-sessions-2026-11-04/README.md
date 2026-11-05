# M1: route contracts and native sessions — 2026-11-04

Implemented canonical route manifests and an event-driven bridge Session class.
The current core protocols are tested over real installed SRT CONTROL/SENSOR
sockets for IPv4 and IPv6. This is still M1: there are no ROS bridge nodes,
production I/O owner, bounded queues, reconnect campaign or durable command journal.

## Reproduce

After M0 has built/installed the qualified dependency and development image:

```sh
python3 tools/run_m1.py --native
```

The runner resolves the immutable Linux amd64 image and verifies the installed
SRT archive's SHA-256 against [the M0 baseline](../../baselines/dependencies.json).
It builds five standalone core contracts in Debug and with ASan+UBSan, then builds
the default root project and runs its complete 47-case matrix. Each attempt gets
a separate `.local/m1/` directory. Source fingerprints, commands and outcomes are
in [run.json](run.json), with `${PROJECT}` replacing the local absolute path.

| Gate | Result | Evidence |
| --- | --- | --- |
| Standalone Linux Debug | 5/5 contracts pass | [JUnit](debug.xml) |
| Standalone Linux ASan + UBSan | 5/5 contracts pass | [JUnit](asan-ubsan.xml) |
| Full installed-SRT root build | 47/47 cases pass | [JUnit](native.xml) |
| macOS arm64, minimal wire/clock build | 2/2 contracts pass | [Host log](native-host.log) |

The 47 cases comprise five core contracts, the 40 original profile tests and
two native session tests. Linux runs use Docker Desktop amd64 emulation. The
upstream SRT source/library and M0 dependency pins were unchanged; the complete
upstream SRT test suite was not rerun. This is loopback evidence, not M3 network
impairment or robotics/runtime qualification. Both logical native endpoints run
in one harness process. Peer-epoch restart tests recreate session state; they do
not qualify OS process crashes or journal recovery. Nothing was committed or pushed.

## Canonical manifest

`RouteManifest` validates 1–8 unique nonzero IDs and returns an immutable sorted
contract plus SHA-256. The RWRM-v1 encoding uses network byte order:

- Header: ASCII `RWRM`, u16 version 1, u16 reserved 0, u32 route count.
- Each route: u32 ID; u8 kind/direction/QoS/enabled; u32 payload limit, budget-ms,
  rate-Hz and maximum inflight; u16-length-prefixed ASCII type name and type hash.

Names are bounded to 128 bytes. Sensor hashes are `RIHS01_` plus 64 lowercase hex
characters; command schema hashes are `SHA256_` plus 64 lowercase hex characters.
Local topic names and local publish/subscribe endpoint roles do not enter the
shared digest. Enabled permissions, directions, limits and QoS do enter it.
The maximum canonical object is 1,828 bytes. The
[golden bytes](../../tests/protocol/routes-v1.hex) and
[digest](../../tests/protocol/routes-v1.sha256) were independently packed with
Python `struct` and hashed with `hashlib`, then checked against the C++/OpenSSL
implementation. Tests also cover ordering, policy changes, duplicate IDs, invalid
hashes, unsupported QoS/directions and limits.

This core validates type/hash syntax and agreement. Actual installed ROS type
support is still the future ROS adapter's responsibility. Native session tests
use a synthetic four-byte sample and a placeholder RIHS01 route hash; they do not
transmit an IMU or claim ROS/CDR correctness.

## Session contract

The single-owner Session object is neither copyable nor movable. It emits bounded
management messages and explicit close/flush actions rather than owning sockets
or invoking callbacks. The I/O owner must apply those actions and discard sends
whose local socket generation is obsolete.

- Security evidence must identify the exact channel with GCM, enforced encryption
  and SESSIONAUTH v2. Native tests read the installed provider's socket options
  and require both key directions to become secured within two seconds before
  session creation. Session authentication version follows from the qualified
  provider/ACP1-off baseline, not from a fabricated public version getter.
- HELLO/WELCOME validate the configured peer ID, complete route digest, limits,
  fresh listener session ID and both process epochs. `random_identity()` uses
  checked OpenSSL CSPRNG output for production epochs, sessions and binding IDs.
- Both endpoints initiate one outstanding time probe at a time. Responses must
  match local t1 and current connection/session/epoch/domain. Expired, unsolicited
  or replayed replies cannot qualify the clock. Probe timeout is two seconds;
  initial HELLO/clock/READY completion has a three-second deadline.
- CONTROL admission starts after mutual READY and qualified local clock evidence.
  Unknown/expired freshness blocks samples, even if transport state remains active.
  A contradictory clock interval closes both channels and requests sample flush.
- SENSOR binding retries every 200 ms for at most three seconds. Every new caller
  SENSOR connection has a fresh nonzero 16-byte binding ID; the CONTROL
  SENSOR_BOUND acknowledgment echoes that exact ID. CONTROL_READY has no binding ID.
- Incoming sample gates cover connection generation, active binding/session,
  peer epoch/domain, enabled route, configured payload/budget, strictly increasing
  sequence and conservative upper age bound. Admission applies at the supplied
  time; deferred publication requires another freshness check at publication.

Required `sensor_binding_id` is field 3 in BIND and READY. This closes the delayed
CONTROL-acknowledgment ambiguity across SENSOR reconnects. The initial unpublished
v1 schema has been refined; old prototype BIND/ack payloads without this ID are
rejected. There is no downgrade to an uncorrelated binding.

Route-0 transmission sequence is shared across both channels. Its receive
watermarks are channel-specific because independent channels can reorder. The
unit tests preserve CONTROL ordering while allowing BIND to overtake CONTROL_READY;
the first BIND is not accepted, and a later fresh-sequence retry succeeds.

## Failure and recovery coverage

Deterministic tests cover peer/manifest/limit/crypto mismatches, pending-probe
limits, unmatched and late replies, clock invalidation, sample replay/oversize/
staleness, late handshake/BIND acknowledgments, old socket events, terminal stop
and explicit reactivation after permanent failure. Transmit sequences survive
SENSOR and CONTROL reconnects. Receive watermarks survive reconnect for the same
peer epoch and reset for a new peer boot; stale-epoch data remains rejected.

The native harness actually transfers encoded envelopes/Protobuf payloads over
GCM+SESSIONAUTH sockets with IPv4/MSS 1500 and IPv6/MSS 1280. It withholds a binding
acknowledgment, replaces SENSOR, sends the old acknowledgment and verifies it
cannot activate the replacement. It then rebinds SENSOR, closes CONTROL, observes
SRT's error event, applies session invalidation and establishes a fresh session.
Three synthetic samples retain increasing sequence numbers. A previous-session
bridge frame deliberately sent through the new protected channel is rejected.
Explicit socket teardown must complete in two seconds; each native CTest case
has a 30-second process limit.

Earlier failed attempts were retained in `.local/m1/` and portable examples are
in [attempts](attempts/). They include a digest output-pointer compile mismatch,
fixtures that reused a socket generation or incorrectly reordered CONTROL, and
a native harness that checked key confirmation too early. Those issues were
corrected; none is omitted from the current passing gates.

## Remaining M1 work

Bounded latest-only SENSOR/CONTROL queues and management reserves, bandwidth
admission, cancellable reconnect scheduling (250 ms–5 s with jitter, 60 s campaign),
production socket/epoll ownership and local diagnostic counters remain open.
The SQLite command journal must still implement admission/dispatch/result commits,
UNKNOWN/CONTEXT_LOST behavior, capacity limits and crash/disk-error injection.
ROS adapters, typed SetMeasurementRate execution and the simulator are M2.
