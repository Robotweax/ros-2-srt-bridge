# SRT request admission diagnostics

Diagnostic source and two-slot plan frozen at
`b8f5418db0d68322220c9c6e38165c6d955ee1f9`. Both slots passed once; the earlier
unresolved seed4211 command did not recur. **No historical failure is resolved,
no production behavior fix or full N5/M3 acceptance is claimed.** PR2 stays draft;
Intrinsic/M4 untouched. [PLAN.md](PLAN.md) was committed before the live cohort.

## Change

Default-off command diagnostics now expose three bounded observations on existing
producer lanes, with no I/O/allocation in those producers:

| Point | Observation | detail | value |
|---|---|---|---|
|32 control_admission|transport admission after decode, before forwarding/rejection handling|original COMMAND6/QUERY8|SessionError|
|33 peer_error_received|sender coordinator consumes an ERROR already correlated by transport|original COMMAND6/QUERY8|ControlErrorCode|
|34 receiver_worker_result|receiver admission/query worker completion|original COMMAND6/QUERY8|JournalError|

All three retain original request sequence and request/session/route identity.
32 additionally records original source origin, exact local admission evaluation
time, post-evaluation clock state/deadline and returned AgeResult error. The age
error is meaningful at COMMAND freshness decisions, not QUERY or identity
rejections. 34 retains the worker entry owner when present. 33 does not invent an
original origin from an ERROR. Extra clock/origin fields on unrelated observations
are zero/unused. Existing trace points remain readable; strict schema checks cover
new points. Error correlation requires matching session, route, request, original
sequence and COMMAND kind; QUERY errors and other contexts cannot be substituted.

No outcome depends on these traces. Receiver admission and worker completion are
not dispatch/execution authority. Full/drop counters remain explicit. Wire format,
SDK/provider, start budget, clock assumptions, lease, timeout, journal transitions,
expiry seals and accepted-command replay policy are unchanged. Observation
workload and fixed trace-event size increase only for opted-in diagnostics; this
is not an overhead-equivalence measurement against the old run.

## Validation and live result

Full final Release validation: SDK70/70, ROS41/41, host267/267 before/after live,
syntax/diff checks pass. Real IPv4/IPv6 tests cover success, missing query,
capacity/payload conflicts, COMMAND versus QUERY peer-error sequences and a
receiver-only150ms clock qualification deadline with the existing one-second probe
cadence. The controlled expiry produces SessionError13, ClockError/AgeResult
expired2 and matching COMMAND peer error5 at the original sequence, with one
handoff and zero effects. It validates diagnostics, not the historical N5 cause.
The first build was interrupted(exit137) to add the returned AgeResult error;
its partial log is preserved separately, never counted as passing validation.
Final source was rebuilt and the entire validation suite completed before live.

| Slot | Seconds | Confirmed / attempted | Effects | Skipped | Verdict |
|---|---:|---:|---:|---:|---|
|SRT N0 seed4211|15|8/8|8|0|PASS|
|SRT N5 seed4211|300|124/124|124|26|PASS bounded progress|

Original [execution.json](execution.json) exits0; no retries/additional seeds.
Every success has matching closed journals, one SDK handoff, original5s sender
start budget, a dispatch within the saved receiver deadline, and new receiver
COMMAND admission plus worker-completion observations. Source hashes match frozen
b8f5418. Active measurement windows contain no context-change/invalidation/session-
action/link-loss events; setup replacement/shutdown events remain in original
traces. Receiver32/34 counts19/19 for N0 and1006/1006 for N5 include COMMAND/QUERY;
all completed diagnostic populations have zero drops. No live admission rejection,
peer error or receiver clock-rejection correlation occurred in this cohort.

Intent7 did encounter a pre-SDK sender clock deferral. It remained unsent for
957.679ms from the deferral observation to its one SDK handoff, then passed
receiver admission and completed successfully on the original5s budget. This
exercises existing unsent-command retention; it is not recovery/replay of the old
unresolved intent12. Separate closed proof:
[deferred-intent-audit.json](deferred-intent-audit.json).

N5 sensor produced/observed totals75036/19012 retain explicit delivery gaps and
zero conservation residuals. Terminal observation latency maximum4918.647ms is an
observed distribution maximum, not a start/execution or future latency bound.
These results do not establish continuous2s command service, sensor delivery
qualification, full N5 or transport superiority. The prior three-seed cohort's
4211 failure and its UNKNOWN/missing-receiver uncertainty remain authoritative
within that original run, with no replay or nonexecution inference.

## Provenance and remaining work

[summary.json](summary.json), [source-verification.json](source-verification.json),
[runtime-verification.json](runtime-verification.json) and [cleanup.json](cleanup.json)
retain outcomes, sources, rebuild/live hashes and owned namespace cleanup. Only
bridge_node, endpoint.a and transport.a changed from the prior runtime, as expected
for these diagnostics; all eight runtime hashes remain unchanged across live
slots and post-run, and the provider pin is unchanged. Both tcpdump listeners
were ready before apps; capture population/drain and provider/trace footer gates
pass. No tests/builds overlapped live windows. Owned containers/networks removed.

Raw PCAPs, journals, provider samples and resource inputs remain local with hashes
in [local-artifact-hashes.json](local-artifact-hashes.json). Public selected run
reports omit provider sample arrays/adjacent deltas; bridge selected logs omit only
PROVIDER_STATS sample lines. Original workload reports/logs stay unchanged.
[public-selection.json](public-selection.json) records original and derived hashes
and exact omissions; trace/footer evidence remains. Only host build/progress
display copies normalize trailing whitespace, with hashes in validation/.

Next freeze bounded controlled receiver clock/future-age rejection coverage to
separate the observed error boundaries from progress behavior while preserving
UNKNOWN and no replay; then a finite instrumented multi-seed N5 cohort if justified.
Do not lengthen qualification deadlines or interpret a successful4211 nonrecurrence
as a fix. Loaded ROS/N5 discovery remains a separate open diagnostic; N3, matched
clock/security/resources and full M3 gates remain outstanding.
