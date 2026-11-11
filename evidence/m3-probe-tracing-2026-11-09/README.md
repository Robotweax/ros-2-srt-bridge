# Calibrated default-off per-probe tracing

Per-probe tracing now records timer attempts, management queue results, SDK call
results and correlated request/reply admission at the existing decisions. It is
**off by default**, requires CommandTrace, and changes no probe scheduling,
one-pending-probe rule,2s reply admission,5s clock-age policy or command outcome.
No new loaded cohort, tuning, live forced-expiry case or historical118 replay.

[Plan](PLAN.md) preceded edits/calibration. Separate SDK/ROS prefixes preserve
the existing baseline, start-trace and sender-visibility installations and pinned
provider. All new fields are local diagnostics; queues, worker IPC, SRT envelopes
and ROS message schemas are unchanged. Matching SDK/ROS objects must be rebuilt:
the C++ observation signature and larger trace POD are not an interchangeable
prebuilt ABI. The new calibrated layout prevents mixing old installed objects.

## Records and correlation

Enable ROS `probe_diagnostics:=true` with `command_diagnostics:=true`. The runner
accepts `--probe-diagnostics --command-diagnostics --runtime-layout probe-tracing
--skip-build`. It rejects older layouts and requires positive versioned lifecycle
records from both endpoints. Sender/start diagnostics can also be enabled on
this layout. Defaults retain their original paths and disabled flags.

| Point | Observation | Key fields |
|---|---|---|
|50 probe_attempt|Existing begin_probe call/result|evaluation time, emitted management sequence/t1 if available, pending-before/after, SessionError|
|51 probe_queue|Existing management FIFO call/result|kind9/10, sequence, decoded outgoing t1/t2/t3, QueueError|
|52 probe_sdk|Actual send call bracket/result|same management sequence, begin/end, expected/returned bytes, SDK error;0 means local acceptance|
|53 probe_admission|Existing Session::receive result|validated decoded times, pending-before/after, actual mapper-call bit/result, clock snapshot|
|54 probe_pending_cleared|Existing tick clears a pending probe|old t1, pending-after0, evaluation and returned SessionError; reason distinguishes deadline/context|

All carry `probe_trace_version:1`, local owner/session/CONTROL generation and
kind9(TimeProbe)/10(TimeReply). `request_sequence` is the management envelope
sequence, not a SRT packet sequence. For these points, `entry_owner_epoch` means
the envelope source epoch; it is not a command-journal owner. Rejected envelopes
do not make that epoch authoritative. A clear after context termination can have
session0; it is retained without force-joining across lost context.

Queue and SDK observations correlate by owner epoch, session, CONTROL generation,
management sequence and kind. No new metadata is inserted in the queue or wire.
SDK observations deliberately do not decode the queued payload again: their
probe fields are unavailable until joined to51. SDK success is not delivery;
no SRT message number or physical-packet mapping is invented.

Cross-peer request/reply correlation uses the decoded t1, validated source epoch
and session, then checks the exact echoed t2/t3 against the peer's reply queue.
For a received reply, `evaluated_ns` is the existing local admission t4. For a
request, the existing response uses its admission time for t2/t3. These are
application timestamps, not UDP tap times.

The optional stack observation output is populated only after the existing
identity/replay/schema checks. Invalid early frames have explicit unavailable
fields. The mapper-submitted bit is set only when the original clock.observe
call actually runs, independently of whether its result qualifies the clock.
Its real ClockError is retained; no extra clock check or protobuf decode is added.

An unmatched/late reply returns the original SessionError15. The pending snapshot
distinguishes no pending, mismatched t1 and a still-pending age>=2s without adding
a new decision. Natural clearing by tick appears at54; clearing/replacing an old
probe inside begin_probe is visible in50's before/after values. Busy attempts are
retained separately from emitted probes. Neither creates a command expiry.

The transport lane retains fixed capacity/drop accounting. Repeated SDK
EASYNCSND observations for a front probe are suppressed after the first until
its final result; this is not a retry count. Missing tails, failed queues,
unavailable fields and dropped observations do not imply nonexecution, delivery
or a fabricated timeout. The reader refuses incomplete/misjoined qualification.
Trace memory is larger even when disabled; enabled timing/atomic work is an
observer intervention, so no performance comparison or mitigation follows.

## Calibration

| Validation | Result |
|---|---|
|Full isolated SDK/native suite|79/79 PASS|
|ROS suite linked to the new SDK install|41/41 PASS|
|Host parser/harness/layout guards|396/396 PASS|
|IPv4 enabled and disabled fresh commands|Each1 effect, one SDK command handoff, matching closed success|
|IPv6 enabled and disabled fresh commands|Each1 effect, one SDK command handoff, matching closed success|
|Enabled probe capture, each family|4 attempts,8 queues,8 SDK results,8 admissions,0 pending-clears|
|Actual qualified mapper renewals|4 per enabled family,8 total, exact reciprocal joins|
|Disabled new probe observations|0 on both endpoints/families|

Each enabled capture waits for two normal qualified replies per endpoint using
the unchanged periodic mechanism. All four emitted probes per family have one
local SDK acceptance, peer request admission, reply queue/SDK acceptance and
matching initiator admission. These are actual decoded echoes, unlike the
length-compatible encrypted candidates in the historical intent3 analysis.
No trace loss occurred. [`calibration.json`](calibration.json) retains all joins
and immutable closed journal selections; eight complete trace files are public.

Session-only virtual-time guards exercise busy admission, successful observation,
wrong echo, late reply and early validation failure/reset of unavailable fields.
They submit no command. Established SDK failure fixtures remain regression tests;
no new live pause, fault, short lease or command-expiry experiment was added.
Healthy new captures did not witness SDK would-block, late-reply rejection or
natural pending-clear branches. Their live calibration remains unavailable;
contracts and the existing virtual decisions cover these distinctions here.

Build/install prefixes: `build/m3-probe-tracing`, `install/bridge-probe-tracing`,
`build/m3-probe-tracing-ros`, `install/m3-probe-tracing-ros`. SDK capture finishes
before ROS build/host work; no heavy work overlaps calibration capture. The
source/binary manifests and complete build/test logs are in this folder. Raw
build/CTest log hashes and whitespace-only public normalization are recorded.

All24 fresh raw artifacts and774 earlier raw artifacts are checked. Synthetic
SQLite/owner files stay local by hash, with immutable selections published; the
archive never opens application recovery. Preserved runtime inventories and the
provider archive are fixed, provider checkout clean. Owned calibration/test
containers use network-none and are removed; no qdisc/neighbor policy is changed.

Next: a separately predeclared loaded cohort can use this calibrated layout to
capture actual busy/late/timeout/recovery paths. The earlier intent3,118,34,98
and12 retain their original evidence and verdicts. Historical118 remains UNKNOWN;
these new traces cannot recreate its missing probe echoes. PR2 stays draft,
M3/full qualification open, Intrinsic/M4 untouched.
