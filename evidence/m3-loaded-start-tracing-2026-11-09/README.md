# Prospective loaded start tracing — 2026-11-09

The matched-build cohort passes once per slot, without tuning: N0/2903/15s8/8
successes; N5/2903/300s129/129 successes with21 skipped offer slots. All137
attempts have complete original-context start/grant/consume/gate observations,
matching closed journals and effects. **No start rejection recurred.** This is
neither a fix for historical command34 nor completed M3 qualification.

[Prospective plan](PLAN.md), frozen live source
`a508d0e13ca8384c0e0b0bc97f1fa663c124bcbf`. No retries/additional seeds or faults.
PR2 draft, M3 incomplete, Intrinsic/M4 untouched.

## Matched build selection and fixed settings

New explicit `--runtime-layout start-trace --skip-build` selects the previously
calibrated `install/bridge-start-trace-qualified` SDK and
`install/m3-start-trace-ros` ROS prefixes. It does not copy over, symlink or rebuild
the old installation. Hash checks cover every recorded matched SDK/ROS/test
binary and all SDK archives, plus preservation of the old installed baseline.
The real ROS setup resolves all three packages to the selected prefix; the
bridge embeds the expected matched listener worker path. Both peers execute the
selected node/simulator paths, while the ROS worker is its co-installed sibling.
The default `baseline` layout and all production timing/profile defaults remain.

[Preflight](preflight.json) reuses the exact previously qualified SDK75/ROS41
binaries. Host374 tests pass before live (new path/hash/worker/setup guards and
all-attempt context/deadline joins). No runtime or native observer rebuild.
Nonbaseline layouts require --skip-build, unknown layouts/changed or incomplete
manifests fail, and baseline/default launches keep their original paths.

N5 retains512kbit TBF,16-packet netem child,128Kbit competitor, dynamic neighbors,
200/50Hz source targets,2s offered commands,5s command budgets,5000ms provider idle
and8s result drain. Existing command/both-provider/native-v2/UDP-PCAP/drain/
neighbor/CONTROL-qdisc/reply/packet diagnostics remain; calibrated start tracing
is explicitly enabled. No ping, neighbor flush, permanent entry, synthetic ARP,
flood, injected fault, queue/rate/priority/clock/budget/timeout change.

Readiness precedes producers. Stop/drain/detach precedes native close. No tests,
builds or heavy analysis overlap live. Exact selected binaries and all measured
source stay fixed before/after both cases; original baseline remains untouched.

## Command outcomes and actual start deadlines

| Slot | Success/attempt | Skipped | Expired / UNKNOWN / unresolved | Strict success | Durable progress |
|---|---:|---:|---|---|---|
|N0/2903,15s|8/8|0|0/0/0|PASS|PASS|
|N5/2903,300s|129/129|21|0/0/0|PASS|PASS|

Both harnesses exit0; matching journal/device audits record8 and129 effects,
zero unadmitted attempts and no active transport context/link-loss events. Each
start group is `worker_handler_invoked`: owner grant, queued execute, consume1,
second gate passed, returned4/0 and matching closed original sender/receiver
success. There are no missing/cross-generation/foreign-context starts, unavailable
worker observations, failed execute submissions or coordinator declines.

| Actual per-attempt headroom | N0 minimum | N5 minimum |
|---|---:|---:|
|Grant deadline minus consume time|4926.940ms|587.291ms|
|Grant deadline minus second-gate time|4926.868ms|587.290ms|
|Original mapped command deadline minus consume time|4926.940ms|4825.899ms|

All attempts/groups are retained, not selected by closeness to a boundary. N5's
actual consume slack spans587.291–4945.632ms. In121 of129 starts, the granted
limit equals the owner's recorded clock qualification deadline. In122 starts
the grant is below the original mapped command deadline; this alone is not an
exclusive clock-cause bucket because the fresh command check can also cap it.

The minimum N5 admission-clock margin is386.035498ms on **new-cohort command48**.
Its owner records a later qualification deadline, and the actual consume slack
is4827.250313ms. This is a directly observed example of a refreshed clock deadline
between admission and start, not permission to substitute one for the other.
No dispatch crosses its last logged admission deadline in this cohort. The
historical13.481372ms condition on original command34 was not reproduced.
Numeric workload IDs in separate runs are distinct intents with different
original contexts; no old command was replayed or retrospectively resolved.

[All N0 attempts](analysis/srt-N0-2903-starts.json),
[all129 N5 attempts, grants and slacks](analysis/srt-N5-2903-starts.json).
Trace timestamps/handler flags remain diagnostic; journal/effect authority and
original budgets are independently audited. Journal mutation timestamps are not
fsync or physical handler-start latency. Added tracing/new binary baseline can
change observer work, so this passing cohort does not establish mitigation,
performance improvement or the unique cause of any earlier failure.

## Packet and CONTROL-window findings

| Full tracer span, source | Driver starts | Actual QDISC_DROP | Pending |
|---|---:|---:|---:|
|N0 operator / robot|1 /1|0 /0|0 /0|
|N5 operator|8|0|0|
|N5 robot|8|9|0|

All native source/peer reply populations equal driver-start counts. Both roles
have zero ring/map/read loss, collisions, unknown frees or bulk ambiguity.
N5 surviving robot replies have ordered same-root enqueue/dequeue; maximum
residence96.984ms. This establishes source TX lifecycle stages, not physical-wire
or per-ARP-request/peer-tap nonce matching or the exact inner netem/TBF instruction.

All23 adjacent positive reply-counter steps inside source publication are retained
(operator7/robot16). Eleven robot outer read envelopes contain no source tap reply:
nine contain nine distinct kernel QDISC_DROP IDs; two contain queued IDs7/17 that
reach driver start after their windows. Their residence times are59.418/58.471ms,
with driver start11.659/14.076ms after window end. Every such step reports+1PIPE/
+1PASS; drops are proved by the actual per-cookie reason, not by subtraction.
No ambiguous old window is assigned a new cohort's identity.

One primary robot CONTROL gap>=1s remains:1.203180126s. Its opposite responder is
operator, with one reply created and reaching driver inside the gap and no scoped
reply drop created there. Whole-interface root counters and different windows
cannot uniquely explain that gap. All active-loss windows and >=1s gaps were
selected prospectively; there are no active link/context-loss events.

[All primary windows](analysis/srt-N5-2903-arp.json),
[all positive steps](analysis/srt-N5-2903-steps.json),
[packet lifecycles and carry-in/out joins](analysis/srt-N5-2903-packets.json).
The reused positive-step helper retains its historical POSTHOC text label; this
cohort's selection was explicitly prospective in PLAN.md, with no primary result
changed after capture.

## Telemetry and qualification limits

N5 source75029/observed10582, SDK-accept-to-receiver gap61599, receiver rejection128;
six conservation residuals are0 and actual sources remain~200/50Hz. These are
accounted diagnostics, not qualified SENSOR freshness/delivery or a provider
retirement diagnosis. A successful command cohort does not resolve that gap or
establish equivalence/superiority against DDS. No comparison to the old baseline
is attributed to tracing or any presumed improvement.

## Provenance and remaining work

- [Execution](execution.json), [summary](summary.json),
  [closed source verification](closed-verification.json),
  [matched runtime/observer preservation](binary-verification.json).
  All matched hashes equal the prior calibration; old installation remains fixed.
- [303 new raw hashes](local-artifact-hashes.json),
  [exact public selections/omissions](public-disposition.json).
  Full PCAP/native/provider/SQLite/sampler streams stay local by hash. Public
  bridge selections keep all40–44 and context events; omitted provider/other
  command rows are counted explicitly. Full all-attempt admissions and start
  groups remain in the closed analyses; selected run files list removed fields.
- All717 raw hashes from the three preceding evidence sets rechecked. Both owned
  networks/containers and credentials removed; root options/features unchanged.
  [Cleanup](cleanup.json), [validation scope](validation/results.json).
- Host374 is new validation here; SDK75/ROS41 are the previous qualification of
  these exact matched binaries. No rebuild or test run occurs during capture.

Next predeclare broader seed coverage with this matched baseline and retain
actual start-lease headroom. This run supplies positive coverage, not a recurrence
of the short-clock boundary. Historical command34 remains unclassified at its
unrecorded branch; UNKNOWN98/12 and fullN3/N5/default-loaded-DDS/cross-host-clock/
security/resources/hardware/comparison gates remain open. No tuning follows this
cohort. PR2 draft, M3 incomplete, Intrinsic/M4 untouched.
