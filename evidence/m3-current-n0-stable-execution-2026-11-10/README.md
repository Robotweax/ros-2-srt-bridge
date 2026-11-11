# Stabilized-lifecycle N0 seed1701/300s — PASS

**One authorized fresh case PASS. Driver0, no failures/retries/tuning.**
Exactly N0-combined-1701/300s ran on freeze98a357e418c2 and the unchanged matched
SDK/ROS build with stabilized launch/readiness/trace/lifecycle assessment. All
strict combined, per-launch shutdown, final-operator observer and cleanup/integrity
gates pass. Other28 N4/N1/N2/N5 cases remain disabled; completed N3 not rerun.
M3 stays open, PR2 draft, M4 untouched. No merge or next case is queued.

## Measurement and command results

Scenario measured300.005754387s; source-enabled fence300.111622428s, within the
unchanged300..301s gate. IMU199.998918784Hz and joints50.001395743Hz satisfy the
original1% cadence gate. No threshold, queue/rate/clock/crypto/wait/filter/budget,
source/helper/gate or native build change during this case. No tests/builds overlap
measurement; prior offline PASS results retain their original scope.

150 attempted commands,150 confirmed successes and150 effects. Zero UNKNOWN,
unresolved, not-admitted or skipped slots. Each has exactly one SDK handoff and
matching closed sender/receiver durable journal proof. Maximum adjacent intent
spacing2023.399626ms is an observation, not a new latency guarantee. Original
command deadline/admission/reconciliation semantics remain in force.

## SENSOR accounting and freshness

75,028 source samples,72,513 SDK accepted/received,72,497 bridge publications and
72,464 typed observations. All six accounting balances are0. The2,564 unobserved
source samples are explicitly accounted: upstreamDDS26, admission118, ingress
replacement1, outbound replacement2370, receive replacement16 and observerDDS33.
No SRT-accept-to-receiver gap is recorded in this source-fenced window. That is
not a general WAN loss claim or lossless/continuous availability guarantee.

All72,497 counted publication ages are covered by checkpoint histogram deltas.
Modeled histogram upper maxima47msIMU/38msjoints; exact in-window modeled upper
maxima46.665179ms/37.079002ms, below unchanged250ms gate. Unknown/stale/other receive
rejections0. These are modeled ingress/publication bounds, not physical sensor or
typed-observer arrival ages. All checkpoint pending slots are0; continuous queue
high-water and hard total-process/SDK memory caps were not measured.

Both peers' PCAP populations independently reconcile at156,712 UDP records each,
zero kernel drops/unaccounted frames and valid integrity. Native kernel-monotonic
captures independently close complete with156,757operator/156,758robot records,
zero reserve/copy failures. Different capture filters/populations are not assumed
to have identical raw counts; declared source-window/native interpretation gates
pass. CONTROL/SENSOR provider and command trace footers are complete with no
reported drops/exhaustion. Clock namespace, typed/isolation and source fences pass.

## Complete observed lifecycle

Four distinct readiness records cover operator, expected wrong-hash negative
robot, warmup robot and final robot. The intended identity helper path/SHA/private
module, token/PID/start_ticks/PPid and zero-capability/NNP checks pass. Negative
test exits1 as expected; it is not a positive shutdown qualification.

All three positive bridge launches have separate retained identities, child
outcomes and51 stage records each. Warmup robot exits0 before final robot launch.
Per-token/time/identity binding, required stages and unchanged socket gates pass;
all six locally traced srt_close returns are0. Final operator slots explicitly
close two listeners; robot final slots are already invalid while their earlier
locally traced data closes also return0. No general leak-freedom or unlogged
close-result claim. Warmup evidence is never deleted, spliced or reused as final.

Signal-to-reap: operator241.640125ms, warmup robot322.600958ms and final robot
369.551792ms. Simulator also exits0/unforced. All four owned children pass the
original5s shutdown gates. Normal child/catalog/role-compatibility identities
match the declared final launches; no emergency cleanup occurs.

Native ARM64 observer is ready before final shutdown. Final operator identity,
clock/capability/exec/filter/lifecycle/worker checks pass. Footer5 bounded samples,
76successful kernel-stack reads,0unavailable and no budget exhaustion. Coverage
includes4 samples within the child wait and1 post-signal sample; worker exit is
confirmed only by registered identity/ENOENT after join, not inferred exit code.
No userspace/GDB or diagnostic-overhead equivalence claim. Original historical
operator hang remains unexplained and is not retrospectively proved fixed.

## Cleanup, archive and acceptance boundary

Both lab containers, native observer, network and observer volume are removed/
absent; credential deleted. Capture/provider/trace closure, normal cleanup and
independent final Docker metadata pass. Frozen source/inputs/harness/assessor,
current14/preserved13/full earlier chain/provider/native87 and preparation public
hashes verify unchanged. All prior raw/public indexes verify, including all three
failed N0 attempts and old/new N3 cohorts. Nothing is relabelled or credited from
an old prefix or diagnostic run.

112new closed raw artifacts/233,284,411bytes are hash-indexed. Public evidence
includes exact authorization/preflight/driver/cohort, full strict assessment,
command/scenario result, catalogs/unique readiness/identity/stage/child records,
observer readiness/exec/stacks/final-state, capture/provider proofs and integrity/
cleanup. Full raw captures/journals/logs stay local and hash-bound.

This closes the single current-build instrumented N0 seed1701/300s coverage case.
It does not complete M3, qualify hardware/physical ages or uninstrumented overhead,
erase historical failures or authorize any remaining case. All28 later campaign
cases stay disabled; separate preparation/authorization is required for new scope.
