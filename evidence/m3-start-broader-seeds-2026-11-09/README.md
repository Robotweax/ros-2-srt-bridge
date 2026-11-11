# Broader matched start-trace seed coverage — 2026-11-09

The extension stops at its first failure as predeclared: **N5/1701 fails with117
successes over118 attempts and one unresolved intent. N5/4211 is NOT_EXECUTED.**
N0/1701 passes8/8. There is no retry, tuning or replacement case. This is not a
completed three-seed matrix; the earlier matched2903 pass remains separate.

The unresolved intent118 is localized before SDK handoff: source clock-unqualified
deferral followed by a deadline-dropped pending input, with zero recorded original
SDK handoffs and no receiver COMMAND/start. Closed sender truth remains
**UNKNOWN/reconcile_required**. Diagnostics do not authorize expiry, nonexecution
or replay. All117 recorded worker starts succeeded, so this is not a recorded
worker start-fence rejection.

[Predeclared plan](PLAN.md), frozen live source
`58081d142ae30b52cf4bb07532b68cb3b9f3375b`. PR2 stays draft, M3 incomplete,
Intrinsic/M4 untouched.

## Fixed scope and outcomes

The only new execution option is Python slot selection
`--coverage additional-seeds`, requiring matched start/packet tracing. Defaults
retain the original focused2903 slots. Source, matched SDK/ROS binaries, observers
and preserved old baseline are verified before/after. Exact existing SDK75/ROS41
qualification is reused; host376 tests pass before live. No build/install swap.

| Declared order | Outcome | Skips | Status |
|---|---|---:|---|
|N0/1701/15s|8 successes /8 attempts,8 effects|0|PASS|
|N5/1701/300s|117 successes /118 attempts,117 effects,1 unresolved|32|**FAIL**|
|N5/4211/300s|No run|—|**NOT_EXECUTED: prior failure**|

Both executed original harnesses exit0 with capture/observer integrity gates
passing. The independent strict-success and durable-progress gates fail for N5,
and the outer cohort exits1. There are no unadmitted attempts or active transport
context/link-loss trace events. The workload audit's terminal-UNKNOWN count is0
because118 never produces a terminal workload observation; the closed sender
journal nevertheless retains UNKNOWN8/reconcile_required2. These are distinct
scopes, not a zero-uncertainty result.

All settings remain: dynamic neighbors,512kbit TBF/16-packet child,128Kbit
competitor,200/50Hz targets,2s command offers,5s command budgets,5000ms provider idle
and8s result drain. Existing provider/command/native-v2/UDP-PCAP/drain/neighbor/
CONTROL-qdisc/reply/ARP-packet/start diagnostics remain enabled. No injected
fault, ping/ARP stimulus, flush, permanent entry or policy/rate/queue/clock/
priority/budget/timeout change. No tests/builds/heavy analysis overlap live.

## Unresolved original intent118

[Full request events, original context and journal proof](analysis/unresolved-intent.json)
retain its session/source epoch/owner/route/payload hash and original five-second
budget. Source origin is341341538487ns, deadline346341538487ns.

| Original-source stage | Observation |
|---|---|
|Sender admission|Point5, local_queued1, matching original journal context|
|Volatile transport admission|Point6, SubmitResult::queued0|
|Clock deferral|Point29, SessionError::clock_unqualified13,16.960125ms after origin|
|Pending input drop|Point21, reason deadline5,2.624127ms after original deadline|
|Original SDK handoff|0 point25 records; complete command trace|
|Receiver COMMAND admission / start|No matching COMMAND32 or40–44; no closed receiver entry|
|Closed sender|UNKNOWN8/reconcile_required2, revision0, invalid result|

The source `inputs()` path retains the original proof/origin/deadline when
`make_control` returns clock-unqualified, then checks the original deadline on
later iterations and releases the expired pending input. The branch is visible
without changing code or timeouts. Its generic trace fields do not contain the
exact ClockMapper error/interval/probe state; point29's default clock_error0
must not be interpreted as a qualified clock observation.

Receiver QUERYs are a different kind:158 query-admission and158 query-worker
observations,48 peer-error observations, including NOT_FOUND3. The workload
retains64 of158 status observations and explicitly records94 omitted history rows
and45 NOT_FOUND status observations. Their populations are not subtracted or
forced into one-to-one packet/response correspondence. After the budget, queried
absence still does not provide an authoritative terminal outcome.

Original118 has no recorded provider acceptance, unlike historical intents98/12
with one SDK handoff. These failure scopes must not be merged. Neither a missing
receiver entry nor source diagnostic evidence seals a journal expiry or makes
replay safe. The117 effects belong to independently audited successes; the
unresolved intent remains uncertain. Original command34's missing start branch
also remains unchanged.

## All start histories and deadline margins

[All118 N5 attempts](analysis/srt-N5-1701-starts.json) include the unavailable start
for118 rather than dropping that row. The117 complete starts all have original-
context grant/execute/consume1, second-gate pass, handler invocation and matching
closed4/0 success. Minimum actual consume slack38.302831ms; second-gate slack
38.302581ms. Minimum original mapped command budget at consume1341.413163ms.
There is no observed coordinator decline, consume failure or second-gate lapse.

The smallest logged admission-clock margin among observed starts is62.201540ms.
A later owner clock deadline is recorded for new-cohort intent87; its actual
consume headroom4852.908414ms remains separate from admission. These are this
cohort's records, not retrospective grants or outcomes for older intents.
[All N0 starts](analysis/srt-N0-1701-starts.json) likewise join8/8 successes.

## Packet windows and telemetry

N5 full-span packet lifecycles: operator7 driver starts/0drops; robot9 driver
starts/18 actual QDISC_DROP, with zero pending/ring/map/read loss, collisions,
unknown frees or bulk ambiguity. Native source/peer reply counts equal driver
starts. Maximum surviving robot root residence126.729ms.

All32 positive reply steps within source publication (operator6/robot26) are
retained. Twenty-two robot windows lack a source tap reply inside the wider read
envelope:18 distinct dropped lifecycle IDs and4 queued IDs3/11/17/19 reaching
driver after the window. Drops come from actual per-cookie kernel reasons, never
counter subtraction. No per-request nonce mapping, physical-wire delivery or
unique cause for source clock qualification is inferred.

Four >=1s CONTROL gaps remain: operator4.200145/1.306023s and robot1.089744/
1.237644s. All responder mappings/root contexts and per-cookie window membership
are preserved; a gap/root counter or missing tap is not a unique ARP/probe/clock
cause. [Primary windows](analysis/srt-N5-1701-arp.json),
[all positive steps](analysis/srt-N5-1701-steps.json),
[packet joins](analysis/srt-N5-1701-packets.json). The reused step helper's legacy
POSTHOC text label does not change this cohort's prospectively declared selection.

SENSOR75053 produced/25216 observed, accept-to-receiver gap43926/rejected2760,
six conservation residuals0. Telemetry remains unqualified. Extra observer work,
seed variation and the distinct binary baseline prevent performance, mitigation
or superiority claims from this comparison.

## Provenance and next work

[Execution](execution.json), [all statuses including skipped4211](summary.json),
[closed source verification](closed-verification.json),
[matched binaries/old baseline](binary-verification.json).
All measured source, matched binaries/provider/observers remain fixed. Exact
previous SDK75/ROS41 checks are not claimed as new tests here; host376 is new.

[303 new raw hashes](local-artifact-hashes.json),
[exact public selections/omissions](public-disposition.json),
[cleanup](cleanup.json), [validation](validation/results.json).
All1020 prior raw hashes from four evidence sets rechecked. Two owned networks/
containers and credentials removed, roots/features unchanged. Complete packet,
native, provider, SQLite and sampler streams remain local by hash. Public bridge
selections preserve all target118 events as well as start/context records;
other omitted lines/fields are counted. No original data/verdict is rewritten.

Next investigate sender clock qualification and pending-input/journal
reconciliation for this observed pre-SDK deadline-drop path, using authoritative
one-use proof/journal semantics. Do not force expiry, replay or tune clocks/
timeouts. Seed4211 remains unexecuted under this stopped plan and requires a new
prospective decision before any later cohort. Historical34/UNKNOWN98/12 and
fullM3/N3/N5/default-loaded-DDS/clock/security/resources/hardware/comparison gates
remain open. PR2 draft, Intrinsic/M4 untouched.
