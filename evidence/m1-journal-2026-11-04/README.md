# M1: durable commands and crash recovery — 2026-11-04

The core now has typed rate commands/status, durable sender and receiver journals,
and CONTROL session gates. The protected IPv4/IPv6 harness demonstrates a lost
result followed by query reconciliation across reconnect without a second effect.
M1 remains incomplete: the production I/O owner and supervised worker integration
are next. There is no ROS bridge node or real simulator/device handler yet.

## Reproduction and results

After M0, run from the project directory:

```sh
python3 tools/run_m1.py --native
```

| Gate | Result | Evidence |
| --- | --- | --- |
| Linux amd64 Debug core | 12/12 pass | [JUnit](debug.xml), [log](debug.log) |
| Linux amd64 ASan + UBSan core | 12/12 pass | [JUnit](asan-ubsan.xml), [log](asan-ubsan.log) |
| Full installed-SRT root build | 54/54 pass | [JUnit](native.xml), [log](native.log) |

[Run manifest](run.json) contains commands, image/archive identity and SHA-256
fingerprints of tested sources; `${PROJECT}` replaces the host path. Test counts
were checked against JUnit with no failed, errored or skipped cases. The two core
inventories are retained. Linux execution uses the immutable M0 development image
under Docker Desktop amd64 emulation, with network disabled. SQLite is the pinned
Ubuntu 3.45.1-1ubuntu2.8 package. No dependency upgrade, commit or push was made.
The full upstream SRT suite was not rerun; these are the bridge root tests.

## Command and persistence contract

`commands_v1.proto` defines bounded SetMeasurementRate and CommandStatus messages
with explicit state/reason enum values. Code preflights fields, lengths, duplicates
and varints before generated Protobuf parsing. An independent command golden and
10,000 seeded mutations are included. Route schema identity uses the generated
file descriptor SHA-256. Payload identity uses canonical network-order RWC1,
route, rate, start budget, expected generation and new generation.

Sender admission commits LOCAL_QUEUED before transmission. Receiver admission
commits ACCEPTED before returning it, and DISPATCHING before invoking a handler.
SUCCEEDED requires a matching rate/generation result and a durable result commit.
Same-ID/same-hash admission returns the original record without renewing its
budget. Different contents conflict. Peer identity and sender/receiver role are
bound in the database header. A second owner is rejected.

On reopen, receiver ACCEPTED becomes REJECTED/CONTEXT_LOST and DISPATCHING becomes
UNKNOWN. No handler is automatically replayed. Sender nonterminal states become
UNKNOWN/reconcile-required after restart or session loss. Matching remote results
can reconcile that provisional state; delayed status cannot downgrade a final
result. Monotonic timestamps from an earlier owner epoch are not reused as new
local timing evidence. Write/sync/storage errors poison the journal, including
reads, until reopen/recovery resolves the durable state.

Session gates check CONTROL direction, session, source epoch/domain, route,
request ID, sequence, schema and typed body. New COMMAND admission and dispatch
need qualified clock freshness. QUERY and STATUS can reconcile after the original
start budget or clock qualification expires, while still requiring the current
session. General ERROR/BUSY/CONFLICT wire encoding remains integration work.

## Capacity and storage behavior

The blocking journal API belongs on a future bounded worker. It uses one SQLite
connection, exclusive SQLite locking and an exclusive OS owner lock. WAL mode and
FULL synchronous mode are checked by reading their actual configured values.
SQLite documents the additional WAL commit sync under FULL in its
[synchronous pragma contract](https://www.sqlite.org/pragma.html#pragma_synchronous).
The single-connection policy also excludes the concurrent writer/checkpointer
pattern described in the [SQLite WAL documentation](https://www.sqlite.org/wal.html).
This is not a physical power-loss qualification of Docker or the host filesystem.

Defaults are 10,000 records and 64 MiB total logical file lengths: main database,
8 MiB WAL, 32 KiB SHM and 16 KiB rollback allowance. Filesystem allocation overhead
and the empty owner lockfile are outside this accounting. A custom VFS bounds
write/truncate, file size hints, chunk preallocation and SHM mapping. Unknown/temp
file paths are denied. The quota test drives an actual oversized SQLite
transaction to SQLITE_FULL and verifies rollback and bounded lengths.

Admission preallocates a fixed 512-byte record including outcome space, retains
eight database pages of headroom and never evicts an existing request. Every
mutation gets a preceding TRUNCATE checkpoint. At most 64 receiver commands are
active; at most one per route is DISPATCHING. Capacity tests show an existing
command can finish after further admissions are refused. These are fixed logical
storage limits, not a claim that a failing disk can always persist an outcome.

## Crash and native integration evidence

Crash tests fork a child, wait at an explicit barrier, send SIGKILL, wait for exit
and reopen its database. Five boundaries cover before admission commit, after
admission commit, after dispatch commit, after a separately fsynced simulated
effect but before result commit, and after result commit but before reply.
Recovery yields absent, rejected, unknown, unknown and succeeded respectively.
Duplicate requests do not cause another effect. These are process-crash tests;
write/sync failures are injected VFS errors, not a physical disk failure.

The native harness uses two logical endpoints in one process, protected real
loopback SRT sockets and separate sender/receiver databases. A rate change from
200 Hz/generation 0 to 100 Hz/generation 1 happens once. ACCEPTED travels over SRT;
the committed final result is deliberately withheld. After full CONTROL reconnect
and a wait beyond the five-second start budget, QUERY recovers SUCCEEDED and
reconciles the sender without redispatch. Both IPv4 and IPv6 pass. Existing
sensor binding, stale-session rejection and source sequences 1, 3, 4 remain covered;
sample 2 expires locally before transmission.

The harness checks freshness before and after DISPATCH commit synchronously.
It does not qualify asynchronous worker races or shutdown. No ROS/CDR command
service, real device, network impairment or throughput claim follows.

## Retained attempts and next work

The first compile attempt's [log](attempts/journal-build-first.log) is retained;
compile diagnostics were corrected before the passing run. Raw local attempts and
ignored database fixtures remain under `.local/` and `build/`; live DB fixtures
are not published as evidence.

Next: production socket/epoll ownership, bounded callback ingress, supervised
journal/handler workers, generation fencing across asynchronous commits and
session loss, timer/reconnect integration, ERROR mapping and integrated shutdown
within five seconds. M2 ROS demonstration and M4 Intrinsic integration remain later.
