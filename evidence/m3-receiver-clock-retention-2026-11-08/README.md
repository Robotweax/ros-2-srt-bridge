# Bounded receiver retention: controlled recovery passes, N5 late expiry remains

The candidate now retains structurally validated COMMANDs during temporary receiver
clock qualification gaps and revalidates them before forwarding once. Controlled
recovery and failure cases pass. The planned live cohort **FAILED progress** on a
command already older than its original budget when it reached receiver admission.
That command was safely dropped, but its diagnostic START_EXPIRED did not create a
durable terminal result. N5/M3 remain open; PR2 draft, Intrinsic/M4 untouched.

[Plan](PLAN.md) frozen at f9101a1; implementation/build/live source
`4a510e75ad10e5e24a0786da227151a940ee8492`. One build/validation and one planned
N0+N5 cohort, no retries. Older failed cohorts and uncertainty remain unchanged.

## Implementation and boundaries

After normal connection/authentication, identity, route, payload and receive-
sequence validation, only soft clock unqualified/expired results can enter a
fixed FIFO. Future timestamps and hard/invalid errors do not qualify. Immutable
original envelope, payload, session/generation and source timestamp are retained;
receive admission is not repeated, so the consumed replay watermark is preserved.
Later COMMANDs queue behind pending ones while clock probes and other CONTROL
traffic continue. Ready+retained messages share64 logical slots, at most56 COMMANDs,
reserving8 for other messages. Overflow reports BUSY without evicting older work.

The FIFO adds fixed storage for56 frames; it does not allocate per retained message
or perform I/O in its producer. Up to8 entries are revalidated per transport loop.
The source timestamp and valid_for_ms are never renewed. A per-entry local resource
ceiling is checked when that FIFO entry reaches processing; it is not an execution
deadline or realtime release guarantee. Before forwarding, production
Session::check_command must freshly qualify the original age and derive the
conservative receiver deadline. A stale age drops with diagnostic START_EXPIRED;
resource-ceiling expiry with no trusted clock remains a clock diagnostic.

Original CONTROL context loss or shutdown discards retained work; sensor-only
replacement does not invalidate CONTROL. The existing mutex protects ready inbox
command counts; control_received now includes ready+retained occupancy. No wire,
provider, clock configuration, sender replay, source budget, journal transition or
absence-seal change. Lost/drop diagnostics do not fabricate a durable negative
outcome. New trace points35/36/37/38 record deferral, fresh resumption, drop and
capacity rejection with original metadata. Only a fresh resumption can substitute
for initial admission in the success/worker audit; it supersedes an earlier gate
sample to avoid double counting. Fixed storage and new processing are not claimed
overhead-equivalent to the previous runtime.

## Validation before live

Full Release/Werror SDK72/72, ROS41/41 and host271/271 pass before measurement;
host271 also passes afterward. No tests/builds overlap live windows. The queue
contract checks FIFO/original bytes, overflow, capacity, resource ceilings,
CONTROL versus SENSOR context, and future/hard-error exclusion. A direct Session
case requalifies after the original deadline and still returns stale_sample25,
AgeResult none0; no new budget is minted.

Real native SRT IPv4 and IPv6 each execute these four modes once:

| Mode | Original fixture budget | SDK handoffs | Forward/resume | Effects | Closed sender |
|---|---:|---:|---:|---:|---|
|Recover150ms receiver clock qualification with1s probes|5000ms|1|1|1|SUCCEEDED|
|Expire before the next probe|500ms|1|0|0|UNKNOWN/reconcile_required|
|Lose CONTROL with retained command|5000ms|1|0|0|UNKNOWN/reconcile_required|
|Shutdown with retained command|5000ms|1|0|0|UNKNOWN/reconcile_required|

The500ms case changes only its original test route/command budget, not production
policy. Recoveries have matching closed results and dispatch before the saved
deadline. Negative fixtures retain original context/budget and no result; QUERY/
NOT_FOUND never authorizes replay. Complete traces show one accepted SDK handoff
and zero dropped observations per native case. Eight immutable closed journal-pair
audits and original outputs are in [native-audits.json](native-audits.json) and
[SDK-LastTest.log](validation/SDK-LastTest.log). Existing direct Session expiry/
future-age rejection contracts still pass; transport retention is the new layer.

## Live cohort

| Slot | Seconds | Confirmed / attempted | Unresolved | Skipped | Verdict |
|---|---:|---:|---:|---:|---|
|N0/4211|15|8/8|0|0|PASS|
|N5/4211|300|21/22|1|128|FAILED progress|

The original safety/accounting harnessPASS remains distinct from stricter progress
FAILED/exit1. No additional seed or run was added. Every confirmed success has
matching closed journals, original5s source budget, timely receiver dispatch, one
SDK handoff and unique original-context admission/worker proof. Capture/drain,
provider and diagnostic populations pass, zero trace drops, no active context-
change/invalidation/session-action/link-loss event.

Intent22 received initial clock-expiry rejection13/AgeResult2 and was retained
(point35). Its original source timestamp550979548999ns and initial receiver
evaluation561138939587ns are10.159390588s apart on the verified shared VM clock:
already5.159390588s past its original5s sender deadline. After qualification,
revalidation returns stale_sample25 with ClockError/AgeResult none0; the frame is
dropped (point37) and the sender receives matched COMMAND START_EXPIRED6, original
wire sequence155. The defer-to-drop trace-record gap is274.626125ms, not an exact
clock recovery latency. No resume/COMMAND worker result occurs for this intent.
These stage timings include buffering/scheduling, not just network propagation;
the underlying late-arrival/clock-expiry cause is not uniquely localized.

The sender has exactly one SDK handoff and stays live LOCAL_QUEUED/revision0;
1252 polls include135 NOT_FOUND observations and1188 omitted historical polls.
After shutdown, sender UNKNOWN/reconcile_required may reflect cleanup invalidation;
receiver has no entry. START_EXPIRED is currently a peer diagnostic, not a durable
terminal status. Original deadline, closed absence and ephemeral traces do not
permit replay or manufacture a negative outcome. Observed effects21/attempts22
retain that uncertainty. See [live-late-expiry-audit.json](live-late-expiry-audit.json).

This differs from the preceding cohort's within-budget rejection. The new native
cases prove recovery within the original budget; this live command was already
late before retention began, so starting it would violate the required budget.
No counterfactual success is claimed for earlier runs. Telemetry75030/17058
produced/observed retains delivery gaps and zero accounting residuals, not full
sensor or N5 qualification.

## Provenance and next step

Only bridge_node and the transport library change from the prior runtime. All8
rebuilt runtime hashes stay fixed during/post-live; provider pin unchanged. Owned
containers/networks removed. Source, runtime, cleanup, build and test evidence are
retained alongside [execution.json](execution.json). Raw PCAP/journals/resources/
provider samples remain local with hashes. [public-selection.json](public-selection.json)
records original/derived hashes and omissions: provider arrays/adjacent deltas and
PROVIDER_STATS lines only; trace/capture/provider footers remain. Validation console
displays alone normalize trailing whitespace/blank EOF lines.

Next separately design a durable receiver expiry outcome for a fully validated,
provably stale command, without dispatch, replay, renewed budget or declaring
absence when clock/context cannot prove it. Preserve uncertainty where proof is
unavailable. Keep the strict all-success N5 verdict honest; any later terminal-
outcome/progress metric must remain distinct from deadline success. Investigate
the underlying CONTROL delay/clock-expiry cause separately. No full N5/M3, hardware,
clock/security/resource or superiority acceptance follows from this candidate.
