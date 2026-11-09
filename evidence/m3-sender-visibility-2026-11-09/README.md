# Targeted sender clock and reconciliation visibility

Default-off sender diagnostics now expose the actual owner clock state at first
deferral and recovery, the pending-input release branch, worker journal replies,
and the local event enqueued to the caller. They add observations only: no clock
policy, command budget, timeout, queue capacity, proof claim, journal transition,
worker IPC or wire format changes. No intent118 replay or forced command expiry.

Enable ROS parameter `sender_diagnostics:=true` together with
`command_diagnostics:=true`. The development runner accepts `--sender-diagnostics`
only with `--command-diagnostics --runtime-layout sender-visibility --skip-build`.
The new layout explicitly selects `install/bridge-sender-visibility` and
`install/m3-sender-visibility-ros`, validates their binary manifest and both older
baselines. Default selection remains unchanged. The runner also requires positive
new release/journal/event records, so an ignored parameter cannot pass the gate.
**No runner cohort was executed here.** Seed4211 remains unexecuted under the
earlier stopped plan.

## Observation contract

| Point | Observation | Meaning and limit |
|---|---|---|
|45 sender_clock|First deferral (detail1) or envelope creation after deferral (detail2)|Actual post-check ClockError, observed-probe bit, probe anchor and signed offset interval; evaluated time and original origin/deadline. No additional clock check.|
|46 sender_pending_release|1 stale drop,2 make rejection,3 queue rejection,4 outbound queued,5 pending mailbox flush|Original input context and deadline before proof transfer/reset. A release branch observation, not SDK delivery or an endpoint receipt.|
|47 sender_journal|WorkerOperation in detail, JournalError in value, worker token|Returned journal entry with explicit availability, stored state/reason/revision, owner/session and original deadline; absent entries stay absent, including session invalidation replies.|
|48 sender_event|Local JournalError in value; received peer ControlErrorCode in detail, or0|Event actually enqueued to the caller, with explicit entry availability. This is not evidence that an external client polled or consumed it.|

Points45–48 carry `sender_trace_version:1`. `terminal_state/terminal_reason` are
reused serialized field names: for47/48 they describe the observed stored state,
including nonterminal local_queued. They do not label every reply as terminal.
`journal_revision` is the observed durable revision, not the trace sequence.
Coordinator generation fields are its current published transport snapshot;
entry session/owner/origin/deadline come from the journal entry when available.

For45, `clock_previous_deadline_ns` is the optional qualification deadline before
the existing make_control call; `clock_deadline_ns` is the post-check optional
deadline. Either can be0 when unavailable. Neither is a reconstructed deadline.
An expired probe retains its observed anchor/offset, while an unobserved mapper
is explicitly distinct. Compare the recorded interval with the declared build/run
clock assumptions; wall/monotonic capture alignment samples are not probe data.
The first deferral is emitted once per pending command; recovery is emitted only
if it subsequently creates an envelope. This is not a check-by-check history.

For46, `evaluated_ns` is populated only where an existing evaluation timestamp is
available;0 explicitly withholds an exact drop/flush decision timestamp. Generic
clock fields on46–48 remain unused. Legacy point29 is unchanged and its zero
clock fields still do not identify ClockError for historical intent118.

The fixed two-lane lossy trace retains its capacity and counters. The POD event
is larger in the new build, even with the new flag disabled. Enabled tracing adds
observer work. No timing/performance comparison or mitigation claim follows.
No new callback, owner I/O, journal RPC, coordinator receipt channel or decision
is added. In particular, transport dropping an input still does not update the
journal; this change makes the separate observations visible without changing
reconciliation policy.

## Calibration and validation

The [plan](PLAN.md) preceded the edits and calibration. Separate SDK and ROS
build/install prefixes preserve the old baseline and the matched start-trace
runtime. The provider checkout/archive is unchanged at pinned commit
`52be7c86ee1f303cbb0c8718c364217e4dd97a36`.

| Check | Result |
|---|---|
|SDK/native suite, separate build|77/77 PASS|
|ROS suite, matching SDK install|41/41 PASS|
|Host parser/harness/regression suite|387/387 PASS|
|Fresh IPv4 enabled / disabled commands|Both succeed, one effect and one SDK handoff each|
|Fresh IPv6 enabled / disabled commands|Both succeed, one effect and one SDK handoff each|
|Enabled sender records, each family|1 release,5 journal replies,3 caller events; no trace loss|
|Disabled new records|0 in both families|
|Original N5/1701 retained raw artifacts|303 unchanged|
|Fresh calibration artifacts|20 hashes checked;4 complete operator logs copied publicly|

[`calibration.json`](calibration.json) joins the new records to the closed,
immutable-read sender/receiver journals. Four fresh random identities were used;
none is intent118. All preserve the original5s command budget and close succeeded
with result generation1. Fresh SQLite and owner files remain local with hashes
and explicit public disposition in `local-artifact-hashes.json`; no files were
opened through application recovery by the archive script.

No clock45 record occurred in these healthy controls. The native fixture
separately checks ClockMapper snapshots for unobserved, qualified, expired and
wide-interval states using deterministic virtual timestamps, with no command
submission by that fixture. It checks signed JSON and legacy serialization
isolation. Host guards reject malformed clock states, invalid availability,
missing observations, capture loss, invalid release branches and wrong runtime
selection. These are contract checks; **an actual sender deferral/recovery and
deadline-drop reconciliation capture with this new build remains outstanding**.
Existing SDK regression fixtures retain their own synthetic failure coverage;
no new network fault, pause, short lease or command-expiry experiment was added.

See `validation/` for complete build/test logs and the read-only archive script,
with exact raw log hashes and whitespace-only public normalization recorded,
`binary-verification.json` for both preserved inventories and selected new
binaries, and the source hash inventories. The C++/CMake build inputs remained
fixed after the SDK test inventory. The scenario's Python layout choice was
extended during that suite, before the separate ROS build; it does not affect
the SDK calibration. No heavy builds/tests overlapped calibration capture.

Next: predeclare a bounded prospective loaded cohort on this separately calibrated
build, with the existing start/packet/provider observations. This requires a new
plan and must remain separate from stopped seed coverage. Historical118 remains
UNKNOWN/reconcile_required, its exact ClockError unavailable; old34/98/12 remain
unchanged. No expiry, nonexecution or replay authority follows from these local
observations. PR2 stays draft, M3/full qualification open, Intrinsic/M4 untouched.
