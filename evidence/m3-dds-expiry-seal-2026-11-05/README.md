# Receiver-backed DDS expiry sealing

DDS command protocol v2 adds SEAL_EXPIRED, a non-executing reconciliation request.
Both DDS endpoints must rebuild; every incoming frame, including HELLO, must
carry protocol_version 2. There is no version downgrade. SDK wire v1, worker IPC
v3, SRT and the CommandJournal implementation/schema remain unchanged.

The sender can issue a seal instead of a read-only QUERY only when its retained
entry is LOCAL_QUEUED/revision 0 with no acknowledged receiver admission, owned
by this sender process, in the original still-live session, and strictly past
the persisted five-second start deadline. It carries the original ID, hash,
command metadata, origin and deadline. Fresh packet/session checks still apply.
A local observer timeout or bare NOT_FOUND is never an expiry proof.

The receiver's dedicated journal worker validates the fresh peer/session and all
metadata, including the fixed budget and overflow bounds. No disk operation holds
the session mutex. It then:

- Returns the existing matching record unchanged, including ACCEPTED, DISPATCHING,
  SUCCEEDED or UNKNOWN. Deadline passage does not rewrite admitted history.
  Conflicting metadata returns an error.
- If the ID is absent, uses the unchanged SDK admission operation strictly after
  the saved deadline. The FULL-synchronous journal commit creates only
  EXPIRED/START_DEADLINE at revision 1, with no dispatch timestamp or valid result.
  It replies with STATUS only after commit. Storage/capacity errors are not proofs.
- Never calls begin_dispatch or the handler on the seal path. A later COMMAND
  encounters the same durable ID/hash tombstone and cannot start. Duplicate seals
  return the record without another admission or effect.

This absence proof is restricted to the original session's receiver lifetime:
the owned journal is retained without record eviction. After sender restart,
receiver restart or link/session rotation, the original intent is QUERY-only.
An absent entry in a new context remains uncertain. If a tombstone was committed
before a lost reply/restart, ordinary QUERY can recover it. Invalidation during a
seal commit cannot start anything; an old-session reply cannot qualify a new one.

Only a validated receiver STATUS makes the sender journal EXPIRED. The service
never republishes an old COMMAND; Reliable DDS may still retransmit packets. The laboratory's fixed cadence may offer a new ID
after terminal expiry, retaining the generation because the expired intent did
not execute. This is a new scheduled intent, not an automatic service retry.
UNKNOWN still pauses work. Deadlines, the 1.5-second packet/lease checks, queue
bounds, start claims, result validation and command cutoff/drain remain unchanged.

Protocol-v2 metadata is recorded in the runners. Separate seal sent/received,
inserted/existing/rejected counters distinguish reconciliation from executable
COMMANDs and read-only QUERYs. Existing-record counts can include real success
or uncertainty; they are not expiry counts. Diagnostics are cumulative snapshots.

Eight new GTests exercise actual SDK journals: exact deadline exclusion, bad
metadata/context, durable absence sealing, duplicate/late COMMAND fences,
existing accepted/dispatching/success/UNKNOWN, conflicts, sender eligibility,
lost reply followed by owner restart/QUERY, and failed storage. All 32 actual ROS
GTests (36 including wrappers), 33 Python tests and full DDS crash/lost-reply
acceptance pass. A workload test checks that expiry does not advance generation
and that a new ID can later succeed. See RESULTS.md and journal-inspection.json
for live evidence and scope.

The recorded C++ build precedes only runner metadata and Python test edits;
all compiled inputs match the final source. Final run inventories and the reused
binary hash match, and installed Python bytes are verified. Previous evidence is
immutable. Raw captures/journals remain local, with hashes and sizes recorded.

This is a DDS development protocol extension. Equivalent reconciliation semantics
and costs on the SRT comparison path remain a new explicit gate. It does not
qualify M3, cross-host clocks, DDS cryptographic authentication/encryption, matched
CPU/wire costs or hardware performance. N2 probes are short, N4 uses mid-window
outage rather than precise command-phase barriers, and N5 discovery remains open.
Intrinsic/M4 is unchanged.
