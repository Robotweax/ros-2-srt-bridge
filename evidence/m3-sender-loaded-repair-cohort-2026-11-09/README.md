# Actual sender clock deferral captured after harness repair

**Both predeclared slots passed. N5 captured one natural sender deferral and
recovery for new intent3, which completed successfully on its original budget.**
There was no tuning, forced command expiry, replay of historical118, retry or
duration extension. The earlier harness-failed cohort remains failed; this is a
new experiment authorized and frozen after its repair.

[Plan](PLAN.md), frozen source
`b97b86b431e1894facbe87c9398b7bb35525594b`. The exact calibrated sender-visibility
SDK/ROS install, previous runtime baselines, provider and three observer binaries
remain unchanged. The repaired packet-parser binding now has successful
end-to-end N0/N5 evidence. No implementation or runtime build occurred here.

| Declared slot, once each | Command outcomes | Skips | Harness / strict / durable |
|---|---|---:|---|
|N0/1701/15s|8 successes /8 attempts,8 effects|0|PASS / PASS / PASS|
|N5/1701/300s|128 successes /128 attempts,128 effects|22|PASS / PASS / PASS|

No unresolved, UNKNOWN, expired or unadmitted attempts in these new runs. N5/4211
remains unexecuted under its earlier stopped plan. These observations are not a
full matrix, mitigation, performance improvement or completed M3 qualification.

## New intent3: exact clock cause and successful recovery

Source origin68844935156ns, original deadline73844935156ns, route100;
session `c94521da9a9eb944e88538aa085e1fa0`, sender epoch
`8ae70e106826687169b46fd889ffe32b`. The request counter3 and all contexts are
fresh. See the complete original-request records and closed journal proof in
[`sender-N5-1701-deferrals.json`](analysis/sender-N5-1701-deferrals.json).

| Stage | Recorded monotonic time / observation |
|---|---|
| Durable sender admission |68849256364ns; local_queued, revision0|
| First deferred evaluation, point45/detail1 |68855687781ns, SessionError13, **ClockError2/expired**|
| Probe snapshot at deferral |anchor62373601819ns, offset[-3388254,2663371]ns, observed=true|
| Recovery evaluation, point45/detail2 |69240784239ns, ClockError0; new probe anchor69240717739ns|
| Pending release branch, point46 |outbound queued (value4), same origin/deadline|
| One SDK handoff, point25 |69240809072ns|
| Receiver admission / dispatch commit arguments |69246895322ns /69258420281ns|
| Receiver closed result |succeeded4/reason0/revision3, valid generation3|
| Sender closed result |matching succeeded4/reason0/revision3, valid generation3|

At the deferral evaluation, probe age was **6482085962ns (6.482085962s)** against
the unchanged5s maximum, an excess of1482085962ns. Offset width at the probe was
6051625ns; using the unchanged1000ppm drift assumption and the implementation's
outward rounding gives a drift-expanded width of19015797ns, below the unchanged
200000000ns bound. The actual recorded error and these independent checks
identify **probe-age expiration**, rather than an over-wide interval, at this
check. The recorded prior/post qualification deadlines at deferral are0/unavailable;
no historical deadline is invented from them.

Recovery was recorded **385096458ns (385.096458ms)** after the deferred evaluation.
The new observed probe was66500ns old at recovery, expanded width14348457ns;
the recorded clock deadline74240717739ns is later than the command deadline.
The original command deadline nevertheless stays73844935156ns, leaving
**4604150917ns (4.604150917s)** at recovery. Clock renewal does not renew the
command budget.

During the observed pending interval, journal replies and caller events retain
local_queued/revision0. Following recovery, journal/event observations include
accepted/revision1 and succeeded/revision3. Successful observe_remote replies
without an attached entry are explicitly absent snapshots, not missing-journal
claims. All49 sender observations and75 original-request records are retained.
Exactly one outbound release and one SDK acceptance are joined to the original
proof; there is no input/outbound drop observation for this new intent. Matching
closed journals supply success authority. The trace does not supply an
end-to-end receipt or permission to replay.

The first deferral is emitted once, not for every check. Its two clock records
bracket the observed deferral/recovery; they are not a continuous clock history.
The cause of the6.482s probe-update gap remains unproven. No unique ARP, qdisc,
provider, probe-generation or scheduler cause follows from this capture.

## All attempts, starts, path observations and telemetry

All 136 attempts are joined by original identity/session/owner/route/origin and
deadline. All136 recorded start groups invoke the handler and close succeeded;
no unavailable start or active-window context-loss observation. In N5, minimum
actual consume slack899.657540ms, second-gate slack899.657040ms; original mapped
command budget at consume remains at least1229.803969ms. These are observations,
not latency guarantees. Full all-attempt/start/sender joins are in `analysis/`.

N5 packet tracing records operator6 driver-start ARP replies/0drops and robot13
driver-start/17actual qdisc drops, with zero other/consumed frees or pending/lost/
ambiguous lifecycle populations. All33 positive reply-counter windows are retained.
Across22 robot windows missing a source reply hook inside the outer read envelope,
the per-cookie joins retain17 distinct qdisc-drop lifetimes and five later queued
driver-start replies (cookies6,16,23,24,29). Maximum surviving queue residence is
124.545667ms. Carry-out is not a drop; counters/taps do not provide request nonce
mapping or physical-wire receipt authority.

All three >=1s CONTROL gaps are retained: operator4.118100169s and1.084114958s,
robot1.138184376s. They are not assigned as the unique cause of intent3's probe
age. SENSOR75026 produced/27663 observed, accept-to-receiver gap43709 and391
receiver rejections; six accounting residuals are0. Telemetry stays unqualified,
and this gap is not automatically WAN loss. Source targets remain about200/50Hz.

## Preservation, validation and limits

Host390 tests passed before live. Exact SDK77/ROS41 binary qualification was
reused, with no rebuild or tests/builds/heavy analysis during live capture. Closed
analysis verifies frozen source, complete traces, all attempts, original budgets,
immutable journals and packet/window populations; no raw report is overwritten.
The two analysis/archive scripts in `validation/` are post-closure read-only work.

All303 new raw hashes and471 prior raw hashes were checked. Complete raw PCAP,
native/provider/SQLite/sample artifacts remain local, selected public copies and
exact omissions are recorded in `public-disposition.json`. Both owned networks,
their containers/observer rules and credentials are removed; root configurations
and interface features match before/after. Runtime inventories and historical
identity preservation are recorded separately.
The two-line public live-status log trims trailing whitespace only, with raw and
public hashes recorded in `validation/display-normalization.json`.

The new workload's numeric counter118 has a different session, source/owner epoch
and origin in a fresh journal; it never loads the old proof or journal.
**Historical118 remains UNKNOWN/reconcile_required and its exact ClockError is
still unavailable.** The new expired-lease observation cannot classify old118,
34,98 or12. No command deadline-drop reconciliation was observed here; the known
transport/journal policy gap is unchanged.

Next diagnose the probe-renewal gap for this captured intent3 using its retained
owner/CONTROL context before considering further instrumentation. Any new cohort
needs its own prospective plan; no forcing expiry or silently resuming4211.
PR2 remains draft, M3/full qualification open, Intrinsic/M4 untouched.
