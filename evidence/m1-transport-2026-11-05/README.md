# M1: threaded transport owner — 2026-11-05

`RobotweaxBridge::transport` now owns sockets, epoll, Session, bounded queues,
bandwidth admission and reconnect timers on a dedicated thread. Two production
transport instances establish protected IPv4/IPv6 sessions without the test
manually advancing Session or calling SRT. No user callback, journal I/O or handler
runs on the owner. M1 remains open for journal/handler worker integration.

## Reproduction and results

After M0, from the project directory:

```sh
python3 tools/run_m1.py --native
```

| Gate | Result | Evidence |
| --- | --- | --- |
| Linux amd64 Debug core | 12/12 pass | [JUnit](debug.xml), [log](debug.log) |
| Linux amd64 ASan + UBSan core | 12/12 pass | [JUnit](asan-ubsan.xml), [log](asan-ubsan.log) |
| Root with installed SRT | 56/56 pass | [JUnit](native.xml), [log](native.log) |
| Threaded transport with ASan + UBSan | 2/2 pass, 427 checks per family | [JUnit](transport-sanitized.xml), [log](transport-sanitized.log) |
| Minimal macOS arm64 build | 4/4 pass | [Log](host-minimal.log) |

[Run manifest](run.json) records commands, immutable image and SRT archive identity,
and tested source fingerprints. `${PROJECT}` replaces the host path. Fingerprints
were verified against the final code; JUnit counts were checked with no failures,
errors or skips. The evidence date uses the client timezone, Europe/Berlin; raw
run IDs are UTC. Linux runs use Docker Desktop amd64 emulation, network disabled,
and the unchanged M0 dependency baseline. The transport/protocol code is sanitizer
instrumented; the installed static SRT dependency is not. No commit or push was
made. These are bridge root tests, not a rerun of the full upstream SRT suite.

The minimal host regression used:

```sh
cmake -S . -B build/m1-minimal-20261105 -G Ninja -DBUILD_PROFILE_PROBE=OFF -DBUILD_MANAGEMENT_CODEC=OFF -DCMAKE_BUILD_TYPE=Debug
cmake --build build/m1-minimal-20261105 --parallel 2
ctest --test-dir build/m1-minimal-20261105 --no-tests=error --output-on-failure
```

This also verifies that a fresh root build with the profile probe disabled keeps
transport disabled by default and needs neither SRT nor the management dependencies.

## Owner and mailbox contract

One thread owns every transport socket/provider call, including startup, accept,
connect, negotiated-option verification, send/receive, close and epoll release.
A process-local reference count keeps the provider alive across multiple owners.
Numeric endpoints avoid DNS work. CONTROL and SENSOR use the M0-qualified channel,
GCM, SESSIONAUTH, encryption, payload, buffer and MSS settings. Sockets use
nonblocking send/receive and zero linger. Listener session IDs and Caller binding
IDs are freshly generated. Each Caller channel has its own reconnect plan with an
independently randomized jitter seed. A permanent Session failure stays failed.

The loop caps receives, sends and ingress work per iteration. Its epoll timeout
is ten milliseconds; no application callbacks or storage operations run there.
Clock probes start during synchronization and recur every second. The protocol
still enforces its own handshake, binding, probe and reconnect deadlines.

External sample submission takes an owned bounded copy, preserving the caller's
monotonic ingress time. There are eight latest-only route slots. QUERY/STATUS
submission has 64 fixed FIFO entries. Submit uses try-lock and reports BUSY for
contention or full storage; QUEUED means volatile mailbox admission only.

Receive CONTROL has 64 fixed FIFO entries. The owner stops reading before the
mailbox is full and disables IN readiness while full; pending frames stay in SRT.
This preserves ordering and bounded application storage, including management
head-of-line blocking. Receive SENSOR remains latest-only per route, and poll
rechecks its conservative local deadline. Deferred consumers must still check
freshness immediately before publication.

Work carries a token containing the Session ID and both connection generations.
The owner rechecks it when consuming ingress; reconnect invalidates pending work
and receive mailboxes. A SENSOR generation change also invalidates pending CONTROL
work conservatively. Persisted outcomes must therefore remain queryable. These
tokens fence stale transport work; they do not prove durable admission or authorize
a handler.

## Integration and lifecycle checks

Each family exercises two actual owners over protected loopback SRT:

- SENSOR payload ownership, route checks, finite ingress age and future rejection.
- QUERY/typed STATUS roundtrip with request identity and matching rate result.
- Eighty queries filling the 64-entry receive mailbox, then all eighty drained in
  FIFO order without loss or duplication.
- A sample received but left unpolled beyond its deadline, then rejected at poll.
- More than five seconds in the same session with successful samples, requiring
  periodic clock renewal beyond the configured probe lifetime.
- Listener shutdown/recreation on the same ports with a new process epoch; Caller
  reconnects both channels, retains source sequence and rejects old sample/status
  tokens.
- Four concurrent sample producers during stop, post-stop admission rejection,
  idempotent join, and stop while connecting/retrying an absent peer.
- Peer identity mismatch leading to a permanent protocol failure without automatic
  reactivation.

Every tested stop must finish within five seconds, with running false and Session
stopped. This qualifies the transport lifecycle in this environment. It does not
bound arbitrary filesystem calls or application handlers, which are not connected
to the owner yet. No ROS/CDR publication, real device, network impairment, physical
wire bandwidth or latency guarantee follows.

## Retained attempts and remaining work

The [first compile](attempts/transport-first-build.log) caught a missing local
identity helper and an indentation diagnostic. Initial startup tests also caught
missing generated Session/binding IDs and probe scheduling restricted to an already
active session. Those [attempts](attempts/transport-identity-fix.log) are retained,
alongside the subsequent passing probe and mailbox runs. The final complete run
includes all fixes and matches the manifest fingerprints.

The API deliberately has no COMMAND submission method until durable sender tickets
exist. Received CONTROL messages are input for a future worker, never permission
to execute. STATUS submission is for a trusted worker after its journal commit;
the typed codec alone is not a durability proof. The existing synchronous journal
harness and crash tests continue to run separately.

Next: bounded journal/handler workers, conservative deadlines across handoffs,
authorization before and after DISPATCHING commit, cancellation/session-loss
fencing, ERROR/BUSY/CONFLICT mapping and complete bridge shutdown qualification.
M2 ROS and M4 Intrinsic remain later milestones.
