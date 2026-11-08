# Instrumented N5 matrix: command rejected during receiver clock expiry

The frozen matrix **FAILED**, with a request-correlated recurrence in its first
N5 slot. The cohort stopped there and skipped the remaining seeds. No retry or
production fix. This identifies the observed rejection-to-stall path in this new
run; the reason clock qualification expired and the unique cause of an older run
are not established. PR2 remains draft, M3 open, Intrinsic/M4 untouched.

Plan and source frozen at `a2425d0da77a116e875f2465f12c0f46e039e7da` before live:
[PLAN.md](PLAN.md). [execution.json](execution.json) preserves original verdicts;
cohort exit1. One control and one N5 run executed once. No new builds, auxiliary
observers, clock/budget policies, replay rules, provider or DDS-default changes.

| Slot | Seconds | Confirmed / attempted | Unresolved | Skipped slots | Verdict |
|---|---:|---:|---:|---:|---|
|SRT N0/4211|15|8/8|0|0|PASS|
|SRT N5/4211|300|18/19|1|131|FAILED progress|
|SRT N5/1701|not run|—|—|—|NOT_EXECUTED after failure|
|SRT N5/2903|not run|—|—|—|NOT_EXECUTED after failure|

## The captured rejection

Intent19 has one SDK handoff. The receiver transport records COMMAND admission
SessionError13(clock_unqualified), ClockError2(expired) and AgeResult2(expired).
The sender records COMMAND peer error5(clock_unqualified). Both observations match
request `13000000000000000000000000000000`, session
`870cc3691d096ff7cf5d3829e31ef24e`, route100 and original wire sequence152.
This is a COMMAND rejection, not an ambiguous QUERY error or future_sample case.

The original source timestamp100602934087ns and receiver evaluation103410112589ns
are2.807178502s apart on the verified shared VM monotonic namespace. The saved
sender deadline105602934087ns still has2.192821498s remaining. These are fixture
clock comparisons, not PCAP arrival times or a general cross-host age guarantee.
The expired mapper reports clock_deadline_ns0; that is an unavailable qualification
deadline, not the actual last-probe deadline or a measured expiry instant.

The receiver rejects before forwarding this COMMAND to its journal worker; there
is no receiver COMMAND worker-result observation for this ID. Subsequent QUERY
worker results report NOT_FOUND. This matches the production transport's rejection
branch, which queues an error and continues without retaining the command. The
sender retains its durable intent; it does not resend an SDK-accepted command.
Without a receiver record, later queries cannot recover a durable command result.
Read-only original correlation and closed proof:
[closed-failure-analysis.json](closed-failure-analysis.json).

## Live versus closed uncertainty

The original safety/accounting harness reports PASS; the frozen stricter command-
progress gate reports FAILED. Neither verdict is rewritten. The fixture confirms
18 successes/effects and1 unresolved attempt, blocking131 later offered slots.
No terminal UNKNOWN response was observed live: last status remains LOCAL_QUEUED,
revision0, with QUERY/NOT_FOUND and expired original budget. There are1263 polls,
150 NOT_FOUND status observations, and1199 omitted historical polls (first/last32
retained). The early retained clock-error poll is consistent with the matched
COMMAND error above; closed receiver-side traces now remove the prior request-kind
ambiguity for this new occurrence.

After shutdown the sender journal is UNKNOWN/reconcile_required/revision0, invalid
result, original5s source budget; the receiver journal has no matching entry.
That closed state can reflect cleanup invalidation and does not establish a live
UNKNOWN transition. Complete trace populations show no active-window session-
change/invalidation/session-action/link-loss event. NOT_FOUND, elapsed budget,
missing receiver records and ephemeral diagnostic traces do not authorize replay
or a durable negative outcome. Earlier UNKNOWNs remain unresolved in their own runs.

## A bounded receiver-retention candidate

A later QUERY samples receiver ClockState none0 with a future qualification
deadline192.868500ms after the rejection, while1.999952998s remains in the original
sender budget. QUERY's default age_error1 is unused, not an age-check failure.
This is a sampled qualification observation, not an exact recovery timestamp,
COMMAND freshness/dispatch proof, or proof that a hypothetical fix would succeed.
See [later-qualification-observation.json](later-qualification-observation.json).

This motivates separately designing bounded receiver retention during temporary
clock gaps, tied to the original immutable command/context/deadline. Evaluate
fresh revalidation and forwarding once, without sender replay or renewed budget.
Explicitly cover late expiry, context loss, queue capacity, shutdown and uncertainty
before changing production behavior. Do not treat ephemeral rejection/error data
as a durable absence seal. Why qualification expired under this workload remains
a separate diagnostic question; this cohort establishes the observed boundary.

## Integrity and scope

- All executed capture population/drain and command/provider footer gates pass.
  All trace observations have zero drops, with verified lifecycle populations.
  Both tcpdump listeners were ready before applications; no filter-before-bind,
  packet-arrival latency, overhead-equivalence or physical-wire claim.
- Every confirmed success has matching closed journals, original5s sender budget,
  dispatch before the saved receiver deadline, one SDK handoff and exactly one
  original request/session/route/origin/sequence receiver admission/worker pair.
  New host negatives reject stale/wrong-context/duplicate observation evidence.
- Host269 tests pass before/after live; syntax/diff pass. Prior SDK71/ROS41 remain
  prior validations; no SDK/ROS rebuild or install. All8 runtime hashes match the
  prior focused diagnostic cohort and stay unchanged during/post-live. Provider
  pin unchanged. Owned containers/networks removed; no tests/builds overlap live.
- N5 sensors produced75032, observer24417, with zero conservation residuals and
  explicit delivery gaps. Command-progress failure/safety integrity do not qualify
  telemetry, full N5/M3, hardware clocks, resources, security or superiority.
- Raw PCAPs, journals, resources and provider samples remain local with hashes.
  Public selected reports omit provider sample arrays/adjacent deltas; selected
  bridge logs omit only PROVIDER_STATS samples. [public-selection.json](public-selection.json)
  enumerates original/derived hashes and exact omissions; diagnostic/capture
  footers remain. Original workload evidence is unchanged. Only host validation/
  progress display copies normalize trailing whitespace/blank EOF lines.

[summary.json](summary.json), [source-verification.json](source-verification.json),
[runtime-verification.json](runtime-verification.json), [cleanup.json](cleanup.json)
and validation/ retain the complete closed cohort and provenance.
