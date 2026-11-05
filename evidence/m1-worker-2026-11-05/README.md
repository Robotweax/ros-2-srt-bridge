# M1: supervised journal process and durable sender tickets — 2026-11-05

Journal work now runs in a supervised Linux process, outside the network owner.
A newly committed sender admission can mint a one-use transport ticket. Bounded
owner checks support asynchronous pre/post-DISPATCHING freshness observations.
No handler starts from these observations: automatic coordination and final
revocable start authorization remain required before M1 is complete.

## Reproduction and results

After the qualified M0 build, from this project directory:

```sh
python3 tools/run_m1.py --native
```

| Gate | Result | Evidence |
| --- | --- | --- |
| Linux amd64 Debug core | 13/13 pass | [JUnit](debug.xml), [log](debug.log) |
| Linux amd64 ASan + UBSan core | 13/13 pass | [JUnit](asan-ubsan.xml), [log](asan-ubsan.log) |
| Installed-SRT root build | 59/59 pass | [JUnit](native.xml), [log](native.log) |
| Transport + worker integration under ASan + UBSan | 4/4 pass | [JUnit](transport-sanitized.xml), [log](transport-sanitized.log) |
| Minimal macOS arm64 build | 4/4 pass | [Log](host-minimal.log) |

[Manifest](run.json) retains commands, immutable image/SRT archive identities and
source fingerprints. `${PROJECT}` replaces the host path. Source hashes and JUnit
counts were verified with no failed, errored or skipped cases. The core worker
contract includes 5,000 seeded IPC mutations; its total assertion count varies
with the number of requests accepted before IPC backpressure. Each native worker
transport case passes 302 checks. Linux runs use the unchanged M0 image under
Docker Desktop amd64 emulation, with network disabled. Bridge code and spawned
worker executables are sanitizer-instrumented in the sanitizer configurations;
the installed SRT archive and system dependencies are not. No commit or push was
made. The full upstream SRT suite was not rerun.

The minimal host regression used:

```sh
cmake -S . -B build/m1-minimal-20261105 -G Ninja -DBUILD_PROFILE_PROBE=OFF -DBUILD_MANAGEMENT_CODEC=OFF -DCMAKE_BUILD_TYPE=Debug
cmake --build build/m1-minimal-20261105 --parallel 2
ctest --test-dir build/m1-minimal-20261105 --no-tests=error --output-on-failure
```

## Process and IPC contract

`RobotweaxBridge::worker` supervises `robotweax-journal-worker` using posix_spawn,
including when SRT owner threads are already running. There is no application
fork of the threaded parent. Spawn actions retain standard streams and a private
IPC descriptor, closing higher descriptors before exec. The child exclusively owns
the journal connection; the parent performs no storage operations.

The qualified platform is Linux/glibc in the pinned Ubuntu image. The worker is
not a qualified macOS implementation. One external coordinator owns all supervisor
methods, including stop and join; it must service poll to observe readiness,
replies and child exit. Atomic ticket liveness is shared with the network thread.

IPC uses 2,048-byte SOCK_SEQPACKET frames, an explicit version/header, big-endian
fields, strict lengths/padding and fixed outstanding storage for 64 correlated
requests. Socket backpressure can report BUSY before all 64 slots are used.
Requests cover admission, get, dispatch commit, result commit, context invalidation,
remote status observation and sender eligibility. The child uses its current
monotonic time at operation start, so IPC queue wait cannot renew a deadline.
It performs journal operations only; no application handler runs in either owner
or journal process.

## Durable ticket and transport checks

Only a successful newly inserted sender LOCAL_QUEUED response can mint a move-only
`DurableCommandTicket`. Duplicate admission, GET, receiver admission, EXPIRED and
write/sync failure do not mint tickets. Proof records bind request, route, command,
peers, process epoch and original context. Application code cannot construct a
proof through the public API.

Transport validates peer/epoch/route/budget/context and consumes a ticket exactly
once after mailbox admission; BUSY leaves it usable. COMMAND ingress is limited to
56 of the 64 CONTROL slots, preserving eight for QUERY/STATUS. Queued command proofs
are bounded separately and checked for known worker liveness and deadline before
SRT submission. Stop and detected failure revoke the worker's tickets. An already
started send remains possible; this is durable intent, not execution success.
There is no automatic resend. Context-loss invalidation and query-first orchestration
still need the automatic coordinator.

The owner has 64 bounded command-check slots. Each returns Session/freshness and a
conservative deadline from the actual owner thread. Duplicate outstanding tokens
are rejected and results retain correlation. Context loss resolves pending checks
as obsolete. These replies describe a point in time. A session can be revoked after
a valid reply but before a handler starts; final start authorization must be
linearized against that revocation. No handler is enabled by the new protocol yet.

## Stop and recovery

Stop closes admission and immediately revokes sender tickets. The parent drains
replies during a two-second graceful-exit period, then sends SIGKILL if needed.
Join has one four-second deadline shared across repeat calls and destruction.
If the kernel has not reaped the child by then, shutdown_timeout reports failure;
a fallback reaper holds no supervisor/transport memory. This is not a guarantee
that uninterruptible kernel/device I/O ends within that deadline.

SIGSTOP barriers freeze the actual child before admission commit, after admission
commit, after dispatch commit, before result commit and after result commit. The
supervisor kills/reaps it within five seconds, then a new worker reopens the same
journal. Receiver outcomes are absent, REJECTED/CONTEXT_LOST, UNKNOWN, UNKNOWN and
SUCCEEDED respectively. Unanswered parent requests never become fabricated success
or proof of nonexecution. Write/FULL and sync failure tests ensure no ticket is
minted and the worker fails closed. These are process and injected-I/O tests, not
physical power-cut or failed-device qualification.

## Native integration scope

IPv4 and IPv6 each run two real transport owner threads and separate sender and
receiver journal processes. The test coordinator uses only the public asynchronous
interfaces; it never calls CommandJournal directly or manually advances Session.

A committed ticket sends one typed COMMAND preserving its original ingress time.
The receiver commits ACCEPTED before STATUS is sent, and the sender persists that
peer observation. Owner freshness checks occur before and after DISPATCHING commit.
A 64-check burst proves the fixed limit and correlation. Waiting beyond the command
deadline makes the post-commit check fail; CONTROL loss rejects the old context.
Restarting the receiver preserves the uncertain DISPATCHING state as UNKNOWN.
No handler/device effect is invoked in this path.

A separate sender journal process pauses after commit while eight QUERY exchanges
continue through the network owners. Its stop/recovery does not stop either owner;
the unacknowledged sender commit recovers UNKNOWN without a new ticket. Additional
checks cover ticket consumption, duplicate suppression and immediate stop revocation.
The older synchronous native command/effect/query harness remains in the root
regression; this worker integration does not replace its separate evidence.

## Retained attempts and next work

The [first compile](attempts/worker-first-build.log) caught inconsistent auto type
deduction. A [native fixture compile](attempts/worker-integration-first.log) caught
the same diagnostic in a separate declaration. The first worker test assumed a
missing executable always causes synchronous posix_spawn failure; the fixture now
also accepts asynchronous child startup failure. A [shutdown test](attempts/worker-integration-second.log)
caught ECONNRESET after killing a paused child with unread STOP; that reset is now
handled as expected shutdown, while unexpected resets still fail closed. Passing
focused checks and all raw attempts remain retained alongside the final run.

Next: automatic command coordinator, session invalidation/query-first flow, final
single-use handler-start grants with revocation fencing, supervised handler execution,
ERROR/BUSY/CONFLICT wire mapping and full bridge lifecycle. M2 ROS and M4 Intrinsic
remain later milestones.
