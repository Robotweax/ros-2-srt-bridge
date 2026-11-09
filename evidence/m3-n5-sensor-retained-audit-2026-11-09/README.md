# Retained N5 SENSOR audit: scoped freshness supported, queue peaks unavailable

**The retained300s N5/1701 run supports the publication-authorization freshness
gate and bounded bridge storage design.** It does not qualify continuous sensor
availability, a hard SDK/process memory peak, all seeds or the later
sender-reconcile build. No new experiment, runtime process, build, tuning, journal
recovery or replay was started. Original reports/verdicts remain unchanged.

The audit uses the entire latest frozen probe cohort (`1fdf7cb`), its15s N0 control
and300s N5 case on the exact prior probe-tracing binaries. All303 original raw
hashes verify before/after; six frozen source Git blobs match the captured source
inventory. Existing installed/preserved binary chains verify unchanged.

## Complete publication-age population

The result comes from **RPC checkpoint histogram deltas**, not the last received
periodic diagnostic snapshot. Every counted publication is included: both route
histogram populations sum to the publication-counter delta, and all six pipeline
conservation balances are zero. Empty, qualified same-owner/session/generation
checkpoints fence the interval. The source window is300.147813012s.

| Route | Publications | p50 /p95 /p99 upper-age bins, ms | Rounded maximum, ms | Exact maximum upper bound, ms |
|---|---:|---|---:|---:|
|IMU|22,990|106 /134 /144|179|178.324341|
|Joints|4,760|113 /141 /152|183|182.559637|

All27,750 counted publications have modeled upper age below the unchanged250ms
limit. Histograms round up to1ms. Exact maxima are attributable to this window
because each ending cumulative maximum exceeds its beginning maximum. The N0
control covers3,647 publications (IMU2,898/joints749), upper-age maxima15.027489/
29.017728ms, also within the gate.

These are bridge-ingress to the authorization/metric observation immediately
before the ROS publish call, under the original conservative ClockMapper model
and common-VM namespace proof. They are not physical sensor sampling ages,
packet-transit times or typed-observer arrival ages. No complete per-SAMPLE
trace exists in these logs, so the audit supplies aggregate publication coverage,
not a newly reconstructed per-message source/receiver/publication join. The
frozen source checks the deadline/context and refuses metrics above250ms before
publishing. No clock/budget rule was changed.

## Denominators and unknown age remain explicit

| N5 stage | Count |
|---|---:|
|Simulator samples produced|75,037|
|Typed bridge ingress|75,034|
|SDK SAMPLE handoffs|72,240|
|Decoded receiver SAMPLE decisions|28,290|
|Receiver rejections, all reasons|539|
|Of those: age unqualified/invalid|465|
|Of those: stale_sample|0|
|Other receiver rejections, reason not exposed|74|
|Accepted at receive|27,751|
|Receive-mailbox replacements|1|
|Bridge publications /typed observations|27,750 /27,750|
|Source samples unobserved|47,287|

Unknown-age rejections are excluded from publication percentiles because they
were rejected, and remain visible in this denominator table. Zero stale_sample
rejections is not a claim that every missing packet was fresh. The remaining74
rejections cannot be assigned an exact cause from these counters.

The47,287 source-to-observer difference balances as: upstream DDS3, admission103,
ingress replacement1/flush290, input rejection3, outbound replacement2,393/flush4,
SDK-accept-to-decoded-receiver gap43,950, receiver rejection539 and receive
replacement1. Other measured loss terms are0; every one of the six residuals is0.
The43,950 gap is not an exclusive WAN-loss count or a reason-specific FEC/retirement
outcome. Missing samples cannot be given age percentiles or inferred nonreceipt.
N5 intentionally permits reduction; high reduction alone does not fail freshness.
No minimum delivery cadence or continuous availability is proved here.

The whole diagnostic history records3,109 observations,8.596838713s of previous-
state-held clock-unqualified time and3.197252460s not-ready time over310.797630641s.
These include startup/tails/gaps and are not exact source-window outage durations
or time-correlated counts of failed publication authorization. They are not used
to discard a favorable segment or infer zero uninterrupted-clock failures.

## Bounds: supported structure versus unavailable peak measurement

The frozen transport/queue source has fixed8-slot arrays with one latest sample
per configured sensor route at each persistent ingress, outbound and receive
stage. This ROS manifest has two sensor routes; the command route cannot use
submit_sample. Replacements discard the older queued sample rather than grow
an unbounded FIFO. This is a structural bridge-slot bound; transient stack copies,
BIND, CONTROL, provider/FEC, RMW and kernel storage are separate populations.
All six sender/receiver occupancy fields are0 at both measurement checkpoints.
**No continuous bridge-queue high-water series was recorded**, so its measured
peak is unavailable, not0.

Reparsed SENSOR provider logs are complete/zero-exhaustion. Only fully source-
contained reads for the actual active owner/generation/socket are selected:

| Provider gauge | Sender,2,983 reads | Receiver,2,875 reads |
|---|---|---|
|Send-buffer packet gauge|0..59|0|
|Send-buffer byte gauge|59..26,679|0|
|Receive-buffer packet gauge|0|0|
|Receive-buffer byte gauge|0|35..196|
|Flight packet gauge|0..61|0|

These API gauges are sampled/smoothed, not hard peaks. A nonzero byte gauge with
packet gauge0 must not be treated as an empty receiver buffer. The earlier
robot-bridge-1 owner has no source-contained read; it is unavailable for this
window and is not stitched into the active robot-bridge-2 owner. Complete
observer records do not imply continuous sampling coverage or physical-wire
visibility.

Captured source requests FC256, SRT send/receive262,144bytes each and UDP send/
receive262,144bytes each with checked API returns. Those are configuration
requests, not retained normalized option readbacks, internal FEC allocator bounds
or a total process/RMW/kernel memory limit. The sampled source-window endpoint
RSS sums peak at297,828,352bytes robot and196,771,840bytes operator; they include
test observer/sampler and workers, exclude capture/competitor, can double-count
shared pages and miss between-sample/short-lived-child peaks. They do not prove
an allocation cap, absence of a leak or a security/resource-equivalent comparison.

## Decision and remaining scope

Close the **scoped publication-age assessment for this retained run**: full
publication histogram population, positive nonempty routes, bounded modeled
upper ages and explicit unknown/missing reductions are supported. Fixed latest-
only bridge storage is source-established; measured continuous queue peaks and
whole-stack hard memory bounds remain unavailable. Do not turn unavailable
memory/availability evidence into a new failure, a passing hard bound or another
automatic experiment.

The corrected offline auditor is covered by6 new guards and413 total host checks:
missing histogram coverage, unknown-age denominators, over-budget/inconsistent
maxima, changed/unqualified/pending checkpoints, empty routes, unchanged cumulative
maxima and old provider owner separation. These are offline fixture tests, not
new ROS/network experiments. `assessment.json` retains complete checkpoint deltas,
gauges and exact frozen-source/binary provenance. `input-manifest.json` links all
303 original hashes. Raw bytes were read/hashed only; no SQLite journal was opened.

N3 auditedFAIL and current default-DDS N5 cold-startFAIL remain. The old UNKNOWNs
and stopped N5/4211 retain their scope. M3 is still open/PR2 draft/Intrinsic-M4
untouched. Next is the comparison/acceptance statement with these explicit
limitations, not new tuning, an experiment or historical command replay.
