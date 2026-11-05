# Reliable DDS command journal development acceptance

The separate `dds_command_node` transports fixed-size command/query/status/error
frames over Reliable/Volatile/KeepLast(64) DDS. It supports the known rate-command
route 100 and budget 5,000 ms. Each endpoint has one dedicated thread owning the
same installed SDK `CommandJournal` (SQLite FULL durability, ownership lock and
bounded storage). The robot thread invokes the extracted `RosRateBackend` shared
with the SRT worker, retaining the same request ID, payload hash, generation and
UNKNOWN outcome handling. ROS callbacks enqueue into 64 fixed task slots; they
do not access the journal or invoke handlers. A 64-entry status cache and
64 receipt correlations remain bounded. This is a common-VM development baseline,
not complete M3 acceptance or a replacement production transport.

Session HELLOs contain independently generated process/link epochs and a digest
of the locally read Linux boot ID/time-namespace offsets. Both endpoints require
matching namespace digests, mutually acknowledged derived session IDs, monotonic
sequence/freshness checks and a 1.5 s lease. Expiry changes the local link nonce;
old Reliable traffic cannot revive that session. Sixty-four retired remote link
nonces prevent rollback; exhausting that bound fails closed rather than forgetting
old links. These fields are not cryptographic peer authentication. DDS encryption,
cross-host clock mapping and security cost equivalence remain unqualified.

A new intent is durably admitted on the sender before its only application-level
COMMAND send. Duplicate/recovered intents query or return known journal state;
they are never sent as a new command. The receiver durably admits, prechecks,
commits DISPATCHING, and claims start under the same mutex used for lease/epoch
changes and stop. The claim checks live session, process/source epochs and the
common-VM monotonic deadline. Journal I/O and handlers never hold that mutex.
Revocation after a start claim cannot undo an already-started handler. A missing
handler reply remains UNKNOWN; committed status is recovered through QUERY.
This DDS coordinator uses the journal API directly in its dedicated thread; it
does not bypass or alter the SRT worker's opaque ticket/start-fence machinery.

Final runs:

| Directory | Local run | Result |
| --- | --- | --- |
| dds-acceptance | .local/m3-dds-commands/20261105T175009991487Z | Duplicate/conflict, delayed reply, receiver and sender SIGKILL, query recovery passed |
| m2-regression | .local/m2/20261105T175011079038Z | Original SRT M2 scenario and ROS tests passed |

Both final manifests match the current source inventory (132 DDS / 81 M2 files).
The DDS run rebuilt the ROS packages; its command binary, simulator binary and
installed SDK archive hashes are recorded. Eighteen actual ROS GTests passed
(seven codec, seven DDS session, four schedule); colcon reports 21 including
three wrappers. Nineteen existing Python harness/accounting tests passed.
No SDK source or SDK wire/worker IPC format changed. SRT's ROS handler was moved
to a shared header without behavior changes; the original full M2 regression
validates its lost-reply and worker-crash behavior after that extraction.

See [results](RESULTS.md) and `journal-inspection.json`. After container cleanup,
read-only SQLite `quick_check` passed on both DDS journals. Both contain exactly
four IDs with matching payload hashes, revisions and terminal outcomes; raw
journals stay ignored locally. `raw-artifacts.json` retains sizes/hashes of raw
captures and journals. Captures were complete with no tcpdump kernel drops;
DDS fragment frames have separate frame-byte accounting. Neither SRT transport
traffic nor unaccounted frames was observed.

The final sender snapshot records one application callback admission drop after
restart. That counter includes try-lock/slot admission failure; the frame kind is
not attributed. Reliable middleware does not imply guaranteed application queue
admission. All four controlled intents still produced one effect each, and the
drop is not hidden or labeled physical WAN loss. The worker also sends HELLOs;
a blocking handler/journal operation can delay its outgoing heartbeat and cause
conservative lease rotation. No availability or throughput qualification follows.

`development/` preserves an earlier passing version and a test failure where the
fault injector's response delay remained enabled for the final intent: its
UNKNOWN was correct, and the final test explicitly resets delay before new work.
Historical manifests retain hashes recorded at invocation and are not current-
source validation. Complete steady sensor+command load, impairment/seed/duration
matrix, deterministic N3 faults, N4 command barriers, matched CPU/wire windows
and clock/security equivalence remain pending. No performance advantage claimed.
