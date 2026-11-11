# Thirty-second N3 matrix: missed source-slot gate retained

**Audited cohort FAIL: five passing cases, sixth failed; three later executions
are outside the intended stop boundary.** Frozen plan/source `b5ae42c` required
zero skipped source slots, alongside1% cadence and capture/freshness gates.
The original harness reported nine PASS/exit0 because it checked average cadence
without checking skipped slots. Do not use that original PASS as qualification.
The raw verdict/log stays unchanged; [execution-matrix.json](execution-matrix.json)
and [post-capture-guard.json](post-capture-guard.json) record the audit separately.

The30s two-loss2903 source trace records IMU counter5605 (trace sequence7006)
with3 skipped5ms slots, begin17.451971ms after its scheduled due time. Its publish
bracket is73.708us; the preceding IMU publish bracket is60.125us. This locates a
late source invocation, not a uniquely identified OS/DDS/observer cause. Average
IMU rate199.910322Hz stays inside1%, explaining why the old gate missed it.
Three later4211 cases actually ran, so they are not labelled NOT_EXECUTED; their
individually passing measurements are supplementary, excluded from this cohort's
qualification. No retry, source tuning or replacement cohort was launched.

## Measured cases

| Case | Audited scope | Source / SDK / received | Published / observed | IMU skipped slots | Max upper age, ms |
|---|---|---|---|---:|---:|
|baseline-1701|PASS|7515 / 7256 / 7256|7253 / 7252|0|29.772140|
|one-loss-1701|PASS|7514 / 7269 / 7269|7268 / 7268|0|30.655877|
|two-loss-1701|PASS|7514 / 7258 / 7256|7252 / 7251|0|28.731403|
|baseline-2903|PASS|7514 / 7278 / 7278|7275 / 7274|0|29.516652|
|one-loss-2903|PASS|7514 / 7272 / 7272|7272 / 7272|0|28.303716|
|two-loss-2903|FAIL|7511 / 7232 / 7230|7229 / 7225|3|35.182399|
|baseline-4211|Outside stop boundary|7515 / 7256 / 7256|7256 / 7252|0|33.779850|
|one-loss-4211|Outside stop boundary|7515 / 7255 / 7255|7253 / 7251|0|30.108994|
|two-loss-4211|Outside stop boundary|7514 / 7255 / 7253|7252 / 7252|0|28.166515|

Every executed case has six conservation balances0, stable session/epoch/
generations, qualified clocks/QoS, both source rates within1%, accepted-publication
upper age below250ms (global max35.182399ms), complete diagnostics and independent
native/full-PCAP source/parity identity/population checks with zero observer loss.
Publication and observer differences remain explicit local stages, not a lossless
source-delivery claim. All other source-slot skip counts are0.

All three one-loss cases select actual SDK8 (joint counter2), one classifier drop,
source absent at both taps, parity present, accepted receiver decision and original
typed payload/stamp observed before classifier removal. All three two-loss cases
select actual SDK7/8 (IMU/joints) in the same four-source/one-parity row, one drop
each, receiver gap exactly2 with no extra rejection, selected sources absent at
the drained typed cutoff and later fresh progress on both routes. Passing these
fault subgates does not repair the source-slot failure of the planned cohort.
N0 base/base+1 seeds are independent starts, not random-loss coverage.

## Fix, provenance and cleanup

`verify_window` now refuses skipped or unavailable per-route source-slot evidence
even when average cadence passes. New regression guards cover positive3/1 skips,
boolean/unavailable evidence and a missing route. The existing cohort stop tests
remain; no runtime source/admission/queue/clock/TTL/provider policy was changed.
Host401 passed before live; host402 passed after this post-capture guard. SDK81/
ROS41 qualification is reused, not re-run: Python-only runner/scenario selection
uses the exact matched `sender-reconcile` installations and checks both ROS package
prefixes. The generic scenario parser also now accepts this installed prefix.

All111 frozen Python source hashes verified before the guard edit, all runtime/
archive/observer hashes and the complete earlier-baseline chain stayed fixed.
The changed guard's original Git blob matches the frozen source hash; its later
hash is separate. The source window retains its30..31s bound, source7750/sender15501 allowances
and unchanged10000/75000 hard limits. Identity and measurement captures remain
separately closed phases.
No test/build/heavy analysis overlapped live capture. Provider unchanged.

All901 new raw files are retained/hash-inventoried locally. [gates.json](gates.json)
publishes compact cadence/accounting/fault/trace/capture/shutdown and provenance
selections; raw source/sample/typed/resource/packet streams, full feature/inspect/
environment reports and journals stay local. Full feature readbacks are replaced
by explicit equality and canonical hashes in the public gate selection. Eighteen
closed fresh journals are immutable-decoded empty: no COMMAND workload or old
intent was opened/replayed. All18 owned containers,9 networks and9 credentials
were removed; all controlled children exit0 without timeout/forced kill.

## Delivery decision

The30s N3 matrix remains **open**, with five qualified prefix cases and a concrete
source scheduling gate failure. Do not relax its zero-skip requirement or rerun it
automatically. Any changed scheduling allowance needs a prospective qualification
contract; it cannot reclassify this run. Keep the source-slot failure separate from
sensor transport repair/freshness results. The next ordered work is loaded DDS
endpoint-discovery confirmation/comparison using retained RTPS fragmentation
findings and existing defaults, followed by consolidated M3 acceptance decisions.
No further packet/ARP archaeology is required by this result.

No full-duration N3, loaded DDS, physical sensor-age, cross-host, security/resource
parity or superiority acceptance follows. PR2 stays draft/M3 open/Intrinsic-M4
untouched. No tuning, forced expiry, historical118 replay or resumption of the
old stopped N5/4211 plan. Earlier failed/UNKNOWN outcomes retain their scope.
