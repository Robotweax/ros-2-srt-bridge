# M1: automatic endpoint and revocable handler starts — 2026-11-05

The Linux command endpoint now coordinates journal admission, ticketed sends,
ACCEPTED, dispatch commits, handler start authorization, result persistence and
query-first recovery automatically. A shared atomic fence resolves handler start
against revocation. The explicitly enabled handler changes a simulated process-local
rate/generation; this is not yet a ROS or hardware bridge. M1 remains open for
general ERROR wire responses and final acceptance/packaging work.

## Reproduction and results

After M0, from the project directory:

```sh
python3 tools/run_m1.py --native
```

| Gate | Result | Evidence |
| --- | --- | --- |
| Linux amd64 Debug core | 14/14 pass | [JUnit](debug.xml), [log](debug.log) |
| Linux amd64 ASan + UBSan core | 14/14 pass | [JUnit](asan-ubsan.xml), [log](asan-ubsan.log) |
| Root with installed SRT | 64/64 pass | [JUnit](native.xml), [log](native.log) |
| Combined native ASan + UBSan | 8/8 pass | [JUnit](transport-sanitized.xml), [log](transport-sanitized.log) |
| Minimal macOS arm64 core | 4/4 pass | [Log](host-minimal.log) |

[Run manifest](run.json) retains commands, immutable image/installed-SRT identity
and tested source SHA-256 fingerprints; `${PROJECT}` replaces the host path.
Fingerprints were checked against the final code, and JUnit contains no failed,
errored or skipped cases. Each endpoint family passes 147 checks; each start-fence
family passes 324. The core execution contract passes 5,146 checks, including 5,000
start/revoke races. All raw attempts remain under `.local/m1/`.

Linux tests run in the unchanged M0 development image under Docker Desktop amd64
emulation, with network disabled. Bridge and spawned worker code is instrumented
in the sanitizer builds; the prebuilt SRT archive and system libraries are not.
The full upstream SRT suite was not rerun. No commit, push or Intrinsic change was
made. The minimal host regression used:

```sh
cmake -S . -B build/m1-minimal-20261105 -G Ninja -DBUILD_PROFILE_PROBE=OFF -DBUILD_MANAGEMENT_CODEC=OFF -DCMAKE_BUILD_TYPE=Debug
cmake --build build/m1-minimal-20261105 --parallel 2
ctest --test-dir build/m1-minimal-20261105 --no-tests=error --output-on-failure
```

This host run does not qualify the Linux worker/endpoint on macOS.

## Atomic start contract

A fresh successful receiver DISPATCHING commit can mint a move-only DispatchTicket.
GET, duplicate dispatch, sender records and failed commits cannot mint one. A
bounded owner request binds this proof to the original command envelope and a
current Session/freshness check. An ordinary CommandCheck remains an observation,
not permission to execute later.

The worker and owner separately map a private sealed memfd with 64 fixed slots.
Seals prevent mapping growth/shrink; the pool is not a sandbox against malicious
local code. Each slot binds a generation, request ID, payload hash and deadline.
Only lock-free 64-bit atomics are permitted on the qualified platform. The native
shared-memory layout is private to this build, not a network ABI. Private IPC is
version 2 and passes IPC plus execution-pool descriptors; higher descriptors are
closed before exec. Network envelopes and command schema identity are unchanged.

The owner grants PREPARED -> GRANTED after checking the durable dispatch proof.
The worker consumes GRANTED -> RUNNING by compare/exchange, which is the handler
entry linearization point. Revocation competes through the same word. If revocation
wins, the handler cannot apply an effect. If start wins, RUNNING is preserved and
the handler may finish after session loss. Revocation occurs before owner socket
close/publication of the lost context. Request/hash/generation checks and proof
lifetimes prevent stale or repeated consumption. A failed pool never recycles a
leftover RUNNING slot.

Grant lifetime is the minimum of original local deadline, current conservative
command freshness and ClockMapper qualification (probe age and drift-width limit).
The child checks it without relying on a later network-owner tick. Subsequent
probes do not extend an issued grant. A grant lost while the command budget still
exists yields REJECTED/CONTEXT_LOST before effect; an elapsed command budget yields
EXPIRED/START_DEADLINE. No result is reported as SUCCEEDED before its journal commit.

CONTROL scope now binds SID and CONTROL generation. SENSOR adds SENSOR generation.
A SENSOR-only generation change no longer invalidates commands, status or grants;
CONTROL or clock loss still revokes unstarted work. This replaces the earlier
transport batch's conservative invalidation of all work on any channel change.

## Automatic coordinator

CommandEndpoint owns transport, one journal/handler process and a coordinator
thread. Peer IDs, role, epoch and the declared rate-command schema are checked
before starting its transport. The receiver must explicitly enable the simulated
rate handler. The coordinator alone consumes CONTROL and check replies; no journal
operation or handler runs on the network thread.

There are 64 callback inputs, 64 local events, 64 tracked IDs and 64 pending lost
sessions. One command workflow runs at a time, stricter than the per-route limit.
Admission callbacks try-lock bounded storage; QUEUED is volatile admission only.
Sender commit precedes send, receiver commit precedes ACCEPTED, dispatch commit
precedes final grant, and result commit precedes terminal STATUS. Pre-dispatch
rejection/expiry is also persisted. Wrong-route queries conflict.

Context loss schedules journal invalidation. Tracked requests are queried after
reconnect and while a result is missing. Repeated Execute with an existing ID reads
its stored state and queries when needed; it does not resend COMMAND. Status
revisions and payload identity remain enforced by the journal.

The simulated device begins at 200 Hz/generation 0, applies an absolute rate only
when its expected generation matches, and counts effects. That device state resets
with its worker process. Durable results remain historical proofs, not promises
about current device state after restart. UNKNOWN is never automatically replayed.

## Boundary and lifecycle evidence

The core test covers exact 64-slot exhaustion, stale slot generations, wrong ID/hash,
one-use consumption, expiry, dead-worker refusal, an independently mapped child
process and 5,000 two-thread start/revoke races with exactly one winner.

Each IPv4/IPv6 start-fence case runs real protected transport owners and separate
journal processes. Seven scenarios cover normal execution, revocation before
consumption (zero effects), revocation after RUNNING (one completed effect), crash
after effect before result commit (UNKNOWN on reopen), expired command budget
(zero effects), SENSOR-token independence and clock-qualified grant expiry while
periodic clock renewal continues (zero effects). Raw execute requests and ticket
reuse are rejected; GET cannot supply a new dispatch proof.

Each automatic endpoint family covers:

- Successful rate/generation changes, withheld direct result recovered by QUERY,
  duplicate-ID suppression, payload conflicts and failed generation preconditions.
- Wrong-route and explicit local status queries.
- A result committed before its reply, worker termination, new receiver epoch and
  full reconnect; the sender recovers SUCCEEDED without sending COMMAND again.
- A paused running handler, both endpoints restarted with new epochs, and repeated
  client ID; query-first reconciles UNKNOWN without another effect or send.
- A handler RPC timeout closing admission/transport and reaping the child.
- Four concurrent producers filling a paused sender's 64-entry callback mailbox;
  excess inputs report BUSY, network ownership continues, stop finishes within five
  seconds, and unresolved local work remains pollable without fabricated outcomes.

Stop begins admission closure and unstarted-grant revocation. The existing worker
protocol allows two seconds grace, then SIGKILL, under one four-second join deadline.
Combined endpoint tests require fully stopped coordinator/transport and reaped child
within five seconds. After stop, bounded input/tracking storage supplies local
context-loss notifications; these do not prove that a previously used request ID
never affected a device. Known durable terminal results are retained. An
uninterruptible kernel/device I/O timeout is still reported as shutdown_timeout,
not a claimed successful join. SIGSTOP and injected errors are not physical power-cut
or damaged-storage qualifications.

## Retained attempts and scope still open

[Initial compile diagnostics](attempts/coordination-first-build.log) and subsequent
endpoint compile/fixture attempts are retained. Early endpoint tests incorrectly
selected the provisional sender UNKNOWN as if it were the peer's recovered UNKNOWN;
the fixture now waits for the peer reason. Another fixture assumed CONTROL readiness
implied SENSOR binding; it now waits explicitly for full transport readiness when
asserting SENSOR state. Production CONTROL still works independently of SENSOR.

The [transient IPC test](attempts/ipc-backpressure.log) assumed kernel BUSY remained
BUSY on the very next call. Child draining can clear it without parent polling;
the test now checks the fixed outstanding limit without that timing assumption.
The [short-clock sanitizer attempt](attempts/short-clock.log) used a 500 ms probe
lifetime that could expire during instrumented child startup, correctly rejecting
the command before the intended grant test. The final fixture uses 1.5 seconds and
still verifies issued-grant expiry despite later one-second probe renewal. Earlier
clock-scope attempts also preserve the distinction between clock-lease loss and
actual command-budget expiry. Final logs and fingerprints include all fixes.

M1 remains incomplete: ERROR/BUSY/CONFLICT/NOT_FOUND is currently surfaced locally,
not as a general wire response. A query for a missing peer record can remain tracked
without a remote error response. Such an error must never masquerade as durable
receiver acceptance or device nonexecution proof. Final M1 acceptance/packaging
comes next; M2 ROS/CDR/real simulator and M4 Intrinsic remain later.
