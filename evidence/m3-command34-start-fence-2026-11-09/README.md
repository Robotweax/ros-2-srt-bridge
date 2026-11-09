# Command34 start-fence diagnosis — 2026-11-09

The strongest supported explanation is clock qualification lapsing at the
post-dispatch start stage, with the original command budget still available.
The original trace does **not** identify whether the coordinator refused the
start check or the worker rejected a grant. No tuning, runtime rebuild, command
replay or new N5 cohort was performed. Original N5 remains FAILED121/122.

## Historical timeline and controls

Source5544747, run `.local/m3/20261109T075543179775Z`, intent34, request
`22000000000000000000000000000000`, route100. Matching closed sender/receiver
journals retain terminal6/reason1 = **REJECTED/context_lost**, revision3,
invalid result, one SDK handoff and receiver dispatch. This is not EXPIRED7/3,
UNKNOWN8, evidence of a transport reset or journal-only nonexecution proof.

Common VM/zero-offset clock proof is verified inside that original run. Times
below are relative to its source origin1372503476959ns:

| Observation | Relative ms |
|---|---:|
| Sender admission mutation |3.739333|
| Receiver COMMAND admission evaluation, clock qualified |13.700375|
| Receiver admission mutation |16.556291|
| Last observed admission clock deadline |27.181747|
| Receiver dispatch mutation |27.628416|
| Receiver REJECTED/context_lost finish mutation |36.911291|
| Sender observes durable rejection |936.653917|
| Workload observes result |1104.808125|

Journal mutation timestamps are captured **before** SQLite commit; dispatch is
not handler invocation, and these numbers do not measure fsync or scheduling.
The admission clock margin is13.481372ms. Dispatch is0.446669ms past that last
observed clock deadline. Rejection is recorded9.282875ms after dispatch, with
**4872.252696ms** of the mapped original command budget remaining. The ~1.105s
workload latency is not the rejection time or original5s budget exhaustion.

All122 attempts were rejoined, not only34. It is the only command dispatched
at/after its last logged admission clock deadline and has the smallest margin.
The next-smallest margin is201.803998ms (successful command45). Neighboring33/35
have3995.740791/3855.305999ms and succeed. All121 successes and the rejection,
122 distinct original contexts,28 skipped slots and121 effects remain recorded;
there are no unresolved/UNKNOWN outcomes or active context/link-loss trace events.

A QUERY immediately before the deadline still logs clock error0 and that same
deadline. Later QUERYs log clock error2 (`ClockError::expired`) and no deadline;
the first such observation is after receiver finish. QUERY age_error is not a
COMMAND freshness result. These observations support a clock-lapse explanation,
but do not prove the clock state at an unlogged start check or grant.

[Full immutable correlation, all122 attempts and QUERY observations](historical-analysis.json).
N0's8/8 result and all other prior outcomes remain in the
[original packet-tracing evidence](../m3-arp-packet-tracing-2026-11-09/README.md).

## What the source can and cannot distinguish

The exact live decision sources are unchanged and hashed in the analysis.
Three post-dispatch paths share the same durable6/1 outcome:

1. Coordinator `endpoint.cpp`: post-dispatch start submission/check fails;
   `decline(error,true)` submits worker `finish(REJECTED,context_lost)` for a
   non-budget error. Execution need never be submitted to the child.
2. Worker `runtime.cpp`: `Pool::consume` returns expired, revoked or invalid while
   the original command deadline remains; commit6/1 before calling the handler.
3. Worker: consume succeeds, then the second pre-handler grant-deadline gate
   elapses while the original command budget remains; commit6/1.

The ROS rate backend cannot return6/1. Its deadline result is7/3; its other
explicit failures use different states/reasons. A durable dispatch record still
cannot distinguish paths1–3. Existing point34 `receiver_worker_result` covers
peer admission/expiry/GET completions, **not execute completion**. Its value0 is
a JournalError success, not evidence that handler execution was submitted.

`transport.cpp` bounds a granted start by the fresh command check, original
journal deadline and **current** clock qualification deadline. `Pool::grant`
stores that minimum. A clock update between logged admission and start can
change the actual deadline. Consequently the admission sample cannot be used as
the historical grant, and the available data cannot prove expiry versus revoke,
invalid proof or second-gate lapse. Reason name `context_lost` alone cannot prove
a session/socket/worker restart. No ARP causality or exact scheduler/fsync cause
is inferred from the clock-margin association.

## Controlled checks without installed-runtime changes

[Plan](PLAN.md) precedes the checks. A standalone diagnostic compiles the
unchanged production `execution_pool.cpp` into an isolated local binary. No
installed SDK, ROS, worker, provider or observer is rebuilt. Supplied historical
timestamps are **counterfactual inputs**, not a live-clock mapping or a command34
replay. Synthetic IDs/hash in the probe are independent of live command payloads.

All9 assertions pass:

- One nanosecond before a supplied grant deadline starts; at/after it expires,
  while the original command budget remains available.
- At command34's recorded dispatch time, a grant using the old observed clock
  deadline expires; a fresh replacement grant at the **same timestamp** starts.
- Revocation and invalid identity remain distinct `Pool::consume` results.
- Successful consume just before the deadline can still meet the second
  pre-handler deadline gate afterwards.
- At the original command deadline, the original budget really is elapsed.

This demonstrates why the missing actual grant/consume observations cannot be
reconstructed from the final6/1 status. [Inputs](probe-input.json),
[probe output](validation/probe.log), source `tools/start_fence_probe/main.cpp`.

Three **existing built** tests run once each, with their existing60/90s timeouts,
in the pinned image with `--network none`, fresh synthetic loopback journals:

| Existing check | Result |
|---|---|
| execution_contract |PASS,5146 assertions|
| execution_start_ipv4 |PASS,324 assertions|
| execution_start_ipv6 |PASS,324 assertions|

No test source/configuration/default was changed. Existing phase6 pauses before
consume and allows its test-only1.5s clock lease to lapse; phase1 revokes the
start fence through session loss. Both yield6/1 with zero effects in the test
assertions. Phase4 exhausts the original command budget and yields7/3 with zero
effects. Running completion/crash-recovery cases retain their prior semantics.
These are distinct controlled causes of shared outcomes, not a historical
reproduction or permission to relax any clock policy. The simulated test handler
is not a new ROS end-to-end validation.

[Controlled outcomes and immutable journal selections](controlled-checks.json).
Probe times are not compared to the current VM's clock or test journal epochs.
All14 existing installed/observer/test binary hashes remain identical before and
after; the separate probe is the only new binary. All497 original raw artifact
hashes still match; no original database or verdict was changed.

## Validation and next work

`m3_start_fence_diagnosis.py` verifies original hashes/common clock, joins both
journals and original admission identity/context, refuses mixed/unknown outcomes
and leaves actual grant, consume result and execute submission explicitly null.
All350 host tests pass, including9 guards for enum confusion, context mismatch,
missing/unqualified admission, timestamp ordering, valid-result contradictions,
and a later admission/possible refreshed grant. The full SDK72/ROS41 suites remain
prior validation; only the three focused existing execution tests were rerun.

[Binary preservation](binary-verification.json),
[497 original hashes rechecked](original-evidence-verification.json),
[66 new local artifact hashes](local-artifact-hashes.json),
[explicit public selections/omissions](public-disposition.json).
All controlled Docker runs use automatic removal and network-none isolation;
closed controlled SQLite streams and the isolated probe binary remain local by
hash. There is no new network impairment, priority, neighbor, budget, idle,
operation-timeout or clock-policy change. PR2 draft, M3 incomplete, Intrinsic/M4
untouched; historical UNKNOWN intents98/12 remain unresolved.

The next useful observation is a bounded, default-off start-stage trace containing
post-dispatch check error/evaluation/clock and granted deadline, execute submission,
slot/generation, worker consume result and both gate timestamps. It must preserve
one-use fences and outcome authority and be calibrated before any new cohort.
That would distinguish coordinator decline from worker consume/second-gate lapse
on a future occurrence. Those fields are absent from command34's original run;
no exact historical branch claim or tuning fix is justified yet.
