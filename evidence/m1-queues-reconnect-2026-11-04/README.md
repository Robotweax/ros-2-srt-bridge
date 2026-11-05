# M1: bounded queues, bandwidth and reconnect planning — 2026-11-04

Added fixed-storage outbound queues, estimated bandwidth admission and a
cancellable reconnect timer state machine. The real IPv4/IPv6 socket harness now
uses the queues/budget and applies Session invalidation actions. The production
I/O owner and durable command journal remain unimplemented; M1 is not complete.

## Reproduction and results

After M0:

```sh
python3 tools/run_m1.py --native
```

| Gate | Result | Evidence |
| --- | --- | --- |
| Core Linux amd64 Debug | 8/8 contracts pass | [JUnit](debug.xml) |
| Core Linux amd64 ASan + UBSan | 8/8 contracts pass | [JUnit](asan-ubsan.xml) |
| Full installed-SRT root build | 50/50 cases pass | [JUnit](native.xml) |
| Minimal macOS arm64 build | 4/4 contracts pass | [Host log](native-host.log) |

The immutable image and installed SRT archive match the M0 baseline. Linux
execution uses Docker Desktop amd64 emulation; there are no host qdisc changes or
external endpoints. The full upstream SRT suite was not rerun. Commands and
source fingerprints are in [run.json](run.json), with `${PROJECT}` replacing the
host project path. No commits or pushes were made.

## Fixed-storage queue contract

CONTROL owns up to 64 complete encoded messages/256 KiB in FIFO order. COMMAND
occupancy is limited to 56 entries/224 KiB, preserving eight entries/32 KiB for
management, STATUS and QUERY. Reservation does not bypass FIFO or remove SRT
head-of-line blocking. Full admission returns BUSY without altering queued data.

SENSOR has eight fixed latest-only slots, one per configured route. Replacing a
sample is counted. Oversize, expired, duplicate/out-of-order and disabled/unknown
routes are rejected. Selection is round-robin among eligible routes; eligibility
enforces `ceil(1 second / max_rate_hz)` after SRT acceptance. Rebind does not reset
rate history. A sample with less than one full millisecond remaining is discarded;
its SRT TTL is the remaining whole-millisecond budget. A separate fixed slot holds
idempotent BIND retries. It is cleared on SENSOR/CONTROL invalidation.

The tested `sizeof(OutboundQueues)` is 307,512 bytes, including fixed packet
buffers and metadata. This excludes its separately bounded manifest allocations
and temporary bounded Protobuf parsing for BIND. It is not an allocation-free
claim. CONTROL byte accounting includes each 96-byte envelope.

Applying Session actions invalidates channel generations and flushes the required
samples/CONTROL messages. IDs of discarded queued COMMANDs are returned, allowing
the future journal layer to resolve them. This is volatile queue admission only:
no journal commit, ACCEPTED, execution result or safe resend is implied.
The native harness transmits only management and synthetic samples, not commands.

Tests cover exact full-size reserve exhaustion, FIFO, payload ownership, latest
replacement, multiple-route fairness, TTL edges, rate/rebind gates, stale socket
generations, flush/stop, discarded request IDs and a 50,000-event seeded overload
trace. The trace independently tracks CONTROL order, count and bytes while SENSOR
storage stays at one sample for its route.

## Estimated bandwidth contract

A shared total token bucket and a SENSOR sub-bucket bound estimated admission.
SENSOR is also prevented from consuming the reserved CONTROL burst. CONTROL can
use the total bucket; the future owner must give queued CONTROL first opportunity.
There is one outstanding permit. SRT acceptance commits it; backpressure refunds
it exactly once. Incorrect/duplicate refunds cannot mint credits. Clock regression
invalidates further admission. Reconnect does not reset the budget object.

The model uses IPv6/UDP/SRT/GCM DATA overhead of 80 bytes. SENSOR also pays
287 bytes per sample, one quarter of maximum authenticated 4-source FEC parity
for the qualified 1,024-byte payload. CONTROL includes 80 bytes per 1,024-byte
fragment and one nominal retransmission allowance (a factor of two).

These are estimates, not actual wire caps: sustained ARQ, ACK/NAK, handshake,
key exchange and already buffered kernel/SRT traffic can exceed them. M3 must
measure and calibrate actual traffic. The synthetic overload tests use 64,000 B/s
estimated total, 16,000 B/s CONTROL reserve, 16,384-byte total burst and 8,832-byte
CONTROL burst reserve. No production bandwidth recommendation is inferred.
Tests cover exact fractional refill deadlines, reserved CONTROL progress after
SENSOR saturation, refunds, invalid configs/times and ten seconds of synthetic
load bounded by initial burst plus elapsed total credits.

## Reconnect timer contract

The plan is single-owner and performs no waits or networking. Base backoff grows
from 250 ms to 5 s; deterministic seeded ±20% jitter is clamped to that same range.
Each attempt is bounded to three seconds, and each campaign to exactly 60 seconds.
The I/O owner receives connect/close/wake decisions and must apply them.

Attempt IDs do not reset on a new campaign. Completion and connection-loss events
must name the current ID. Old or cancelled callbacks are ignored before timestamp
validation. Late success cannot bypass either attempt or campaign deadline.
Transient failure schedules a retry; permanent failure remains FAILED until
explicit activation. Cancel closes pending/connected ownership and suppresses
later timers/completions. A fresh connection-loss campaign starts only for the
current connected generation. Seeded decorrelation is not cryptographic identity.

The 1,000-seed tests verify delay bounds, deterministic replay, monotonic IDs,
no overlapping attempts, exact cutoff, explicit reactivation gates, stale loss/
completion callbacks, late success, cancellation and timestamp overflow/regression.
These are deterministic state tests, not an OS-level worker shutdown qualification.

## Native integration scope

Both logical endpoints run in one harness process over real protected loopback
SRT sockets. CONTROL/SENSOR messages enter the bounded queues; send attempts
reserve and resolve budget credits around the actual nonblocking SRT call. The
harness applies queue invalidation when Session reports SENSOR/CONTROL loss and
stop. It retains the prior delayed-binding-ack and old-session rejection tests.

A queued sample deliberately waits 260 ms against its 250 ms budget, expires and
never enters SRT. Three other synthetic samples publish with source sequences
1, 3 and 4. Rebind/full reconnect preserve the source counter; the skipped 2 is an
explicit local expiry. The old-session fault injection deliberately bypasses the
sender gate to test receiver rejection. Explicit socket teardown remains bounded
to two seconds by the native tests; process deadlines are 30 seconds.

The harness budget is generous (1,000,000 B/s with a 131,072-byte burst); it does
not simulate network congestion or prove whole-stack overload behavior. M0's SRT
backpressure cases and the separate budget/refund tests cover those components.
No ROS/CDR, journal, real device, network impairment or performance claim follows.

## Retained attempts and remaining work

The first queue compile caught a misleading-indentation error in the test fixture;
its [log](attempts/queues-first.log) is retained. All raw attempts remain under
`.local/m1/`. Current tests and source fingerprints match the passing revision.

Next: SQLite command journal, typed parameters/status and crash/disk-fault tests;
then a production I/O owner applying these plans/actions, with bounded thread-safe
callback ingress and cancellable worker lifecycle. The five-second bridge shutdown
requirement still needs that integrated lifecycle test. M2/Intrinsic remain later.
