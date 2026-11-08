# Qualified receiver expiry is durable and cannot dispatch

A fully validated received COMMAND can now commit EXPIRED/start_deadline and send
STATUS after the journal commit when a qualified age interval proves the original
budget has elapsed. The expiry-only path never dispatches, resends or renews the
source budget. Controlled direct/retained late-delivery cases pass. The planned
live N0 and300s N5/4211 slots also pass:8/8 and136/136 successes,0 expired/unresolved.
Live expiry was not exercised; native cases validate it. Telemetry delivery remains
poor and full N5/M3 stays open; PR2 draft, Intrinsic/M4 untouched.

Plan frozen at1f11963; implementation/build/live source
`a866505` (full identity in [execution.json](execution.json)). One full validation,
one two-slot live cohort, no retries or new seeds. Historical FAILED/UNKNOWN
cohorts remain unchanged. [PLAN.md](PLAN.md) separates all-success from the new
success-or-verified-expiry metric before measurement.

## Proof and journal-only path

A conservative age interval's upper bound exceeding budget only proves that a
command is unsafe to start. It does not prove expiry. The new helper requires:

- Normal authenticated connection, structural/payload/route/identity/budget and
  replay-sequence admission already succeeded before freshness evaluation.
- A qualified AgeResult none0 and ordered interval whose **lower bound is strictly
  greater than the original budget**. Straddling/equality intervals do not qualify.
- Positive representable latest possible converted deadline:
  `evaluated_ns - (age_lower_ns - original_budget_ns)`, strictly in the past.

This latest-bound deadline is evidence that expiry is certain. It may be later
than the conservative earliest-bound deadline used for fresh execution; it never
becomes an execution window. An internal expiry_only flag routes the original
immutable frame to a dedicated endpoint completion path. Existing journal
admission inserts an already-expired entry (revision1, no dispatch/result payload),
and only its committed record may produce terminal STATUS. The completion path
cannot dispatch even if an existing record is returned. Existing records retain
authority; capacity/storage/context failures do not fabricate expiry.

Initial qualified stale arrival and revalidation after bounded receiver retention
use the same proof. A straddling interval can wait within existing FIFO/resource/
context limits. Invalid/future/unqualified clocks, timeout, NOT_FOUND, absent records
and conversion underflow do not prove expiry. Lack of proof preserves uncertainty.
No wire/protobuf/provider/clock-configuration or sender replay change; sender
source timestamp/deadline and existing receiver64/56 bounds remain unchanged.

Trace39 records original context/sequence, qualified lower/upper age bounds,
evaluation, original budget and latest expiry deadline. Trace34 independently
observes the worker result; durable records, not traces alone, authorize the
outcome. Source sender records retain their original source deadline. Expiry-only
receiver deadlines are never used to grant handler execution.

## Controlled validation

Full Release/Werror SDK72/72, ROS41/41 and host273/273 pass before live; host273
also passes afterward. Proof tests refuse straddling/equality, invalid/future,
inverted and underflow cases. Existing retention/resource-expiry/context/shutdown,
Session negative and worker/journal regressions pass.

A test-owned loopback UDP gate delays original500ms-budget COMMANDs650ms in real
SRT IPv4 and IPv6, once per mode/family:

| Mode | Durable expiry | Expired command SDK handoffs | Dispatch/effect for expired ID | Restart wire QUERY/duplicate reconciliation | Later fresh ID |
|---|---|---:|---:|---|---|
|Qualified direct late arrival|yes|1|0/0|EXPIRED retained, no replay|SUCCEEDED|
|Clock gap then retained revalidation|yes|1|0/0|EXPIRED retained, no replay|SUCCEEDED|

The shorter budget is the original native fixture budget, not a production policy
change. Four immutable closed journal-pair audits each contain EXPIRED plus a later
fresh SUCCEEDED intent. Expired records have reason start_deadline, invalid execution
result payload, matching hashes/revisions and receiver dispatched_ns0 with past
deadline before admission. Original source500ms budget remains exact. Retained
native cases observe one deferral and one lower-bound expiry proof. Trace populations
have zero drops. The gate is shared with existing transport tests; unchanged tests
still exercise its behavior. [native-audits.json](native-audits.json),
[native-binaries.json](native-binaries.json), [SDK-LastTest.log](validation/SDK-LastTest.log).

## Fixed live cohort and two separate metrics

| Slot | Confirmed / attempted | Verified expired | Unresolved | Skipped | All-success | Durable-outcome completion |
|---|---:|---:|---:|---:|---|---|
|N0/4211,15s|8/8|0|0|0|PASS|PASS|
|N5/4211,300s|136/136|0|0|14|PASS|PASS|

Cohort exits0. Every success has matching closed journals, original5s sender budget,
receiver dispatch before its saved deadline, one SDK handoff and unique original-
context/origin/sequence receiver gate/worker proof. New `--progress-gate durable-outcomes`
accepts only verified SUCCEEDED or qualified durable EXPIRED with no dispatch and
matching records. UNKNOWN, failed/rejected/nonadmitted/unresolved attempts fail it;
effects must equal successes. Default all-success gate is unchanged. No expiry in
this live run means its two metrics coincide; native expiry validation cannot be
presented as live expiry coverage. FullN5/all-offered-slot cadence or latency SLA
is not established by either metric.

Live intent5 exercises both sides of clock retention: source pre-SDK defer-to-handoff
trace gap2.235969917s, receiver defer-to-resume gap604.138208ms, original origin to
fresh receiver evaluation2.860698626s. Qualified age interval is
[2.851650879s,2.883293135s], within original5s budget; the saved conservative deadline
and dispatch remain valid. Exactly one SDK handoff, one resume and durable success.
These are recorded stage intervals, not exact clock recovery or physical-wire times.
[retained-success-audit.json](retained-success-audit.json).

N5 sensor source75022/observer871, dominated by71187 in the SRT-accept-to-receiver
gap category; all six accounting residuals are zero. Source rates remain~200/50Hz.
Availability is poor despite command success. This category does not uniquely
identify physical packet loss, provider cause or clock behavior. Keep telemetry
delivery, broader N5 coverage and underlying CONTROL delay/clock expiry open.

## Provenance and remaining gates

Capture/drain/provider/trace populations pass with zero trace drops and no active-
window context-change/invalidation/session-action/link-loss events. Both tcpdump
listeners were ready before applications; no filter-before-bind or realtime PCAP
latency claim. No builds/tests overlap live. Four artifacts change from the prior
runtime: bridge_node, dds_command_node, endpoint.a, transport.a, including shared
code/header relinking. All8 rebuilt runtime hashes stay fixed during/post-live;
provider pin unchanged. No DDS profile/default change or new DDS N5 qualification
is claimed. Owned validation/run containers/networks are removed.

Raw PCAPs/journals/resources/provider samples remain local with hashes. Public
selected reports omit repetitive provider arrays/adjacent deltas; selected bridge
logs omit only PROVIDER_STATS samples. Original/derived hashes and exact omissions
are in [public-selection.json](public-selection.json); trace/capture/provider
footers remain. Validation console copies alone normalize trailing whitespace/blank
EOF lines. [source-verification.json](source-verification.json),
[runtime-verification.json](runtime-verification.json) and [cleanup.json](cleanup.json)
retain source, build and owned cleanup proof.

Next freeze broader instrumented N5 seed coverage with both verdicts explicit, and
investigate telemetry delivery separately. No old unknown is retroactively expired,
no retry/renewed budget, no complete M3, hardware-clock/security/resource or
transport-superiority claim follows from this bounded cohort.
