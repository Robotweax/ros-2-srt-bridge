# M3 acceptance review — 2026-11-09

The [explicit-identity N0 freeze](evidence/m3-current-n0-bound-preparation-2026-11-10/README.md)
is prepared for exactly seed1701/300s. Freeze66f21a2916b9 binds the intended helper
path/SHA, verified harness, unchanged matched build and retained evidence. It is
execution-disabled: no grant or live run. Ten preparation and30 readiness/import
checks pass offline; prior511-test PASS retains its scope. No tuning/retry/rebuild;
other28 stages disabled, N0 unqualified, M3 open/PR2 draft/M4 untouched.


The [explicit identity-helper fix](evidence/m3-current-n0-identity-binding-fix-2026-11-10/README.md)
binds the intended frozen helper by exact path/SHA and checked source bytes in a
private module, independent of import order/cache. Snapshots retain helper origin.
All30 targeted and511 existing tests pass offline, including fresh parent/wrapper
imports with the actual ROS helper cached first. No N0 rerun/new freeze/grant,
tuning or retry; original inputs/builds/failures unchanged, other28 stages disabled,
N0 unqualified and M3 open/PR2 draft/M4 untouched.


The [corrected-readiness N0 attempt](evidence/m3-current-n0-corrected-execution-2026-11-10/README.md)
failed during launch registration before measurement: both roles hit missing
identity.ppid. Separate per-launch failure snapshots were retained. The runtime
import order exposes a three-field identity helper while the validator expects
ppid; offline tests used the richer evidence-local helper. No capability check,
observer or300s measurement was reached. One attempt, no tuning/retry; cleanup/
integrity verify. Other28 stages disabled, N0 unqualified, M3 open/PR2 draft.


The [new corrected-readiness N0 freeze](evidence/m3-current-n0-corrected-preparation-2026-11-10/README.md)
is prepared for exactly seed1701/300s, binding the verified launch-specific harness
and unchanged matched build. Freeze7b5c7d922206 is execution-disabled with no grant
or live run. Nine preparation and21 readiness tests pass offline; retained511
existing-test PASS keeps its original scope. Runtime/image metadata and retained
source/input/build/public/raw evidence verify. No tuning/retry/native rebuild;
other28 stages disabled, N0 still unqualified, M3 open/PR2 draft/M4 untouched.


The [launch-specific N0 readiness fix](evidence/m3-current-n0-readiness-fix-2026-11-10/README.md)
is implemented in a separate candidate harness and passes21 targeted plus511
existing offline tests. Unique per-launch token/path and PID/start_ticks binding
prevent stale negative-test readiness; failures retain the exact checked status
and identity brackets. Native builds, policy and workloads remain unchanged.
No live run, new campaign freeze or authorization; N0 FAIL preserved and other28
stages disabled. M3 open, PR2 draft, M4 untouched.


The [retained N0 capability diagnosis](evidence/m3-current-n0-capability-diagnosis-2026-11-10/README.md)
identifies a readiness identity defect: the deliberate wrong-hash robot bridge
and real bridge share one pre-exec marker, and the real start trusts existence
without matching the launch/PID. Stale readiness can trigger premature capability
checking. Exact failing capability values/transition remain unobserved. Diagnosis
only: no fix, tuning, retry, new test or experiment; N0 FAIL retained, other28
cases disabled, M3 open/PR2 draft/M4 untouched.


The [authorized current-build N0 attempt](evidence/m3-current-n0-execution-2026-11-10/README.md)
failed at robot startup capability attestation before the300s measurement began.
One attempt, zero retries/tuning; the failing /proc capability values were not
retained, so cause remains unresolved despite zero-capability pre-exec records.
Owned emergency cleanup and final absence/integrity checks pass; no N0 coverage
or clean shutdown is credited. All28 other unexecuted cases stay disabled;
fresh N3 remains9/9, historical failures preserved, M3 open/PR2 draft/M4 untouched.


The [current-build N0 preparation](evidence/m3-current-n0-preparation-2026-11-10/README.md)
binds the single predeclared N0-combined-1701 case (300s) to the unchanged frozen
14-entry matched build. Execution is disabled: no authorization file or live run.
All511 existing and8 targeted offline tests pass; retained N3 evidence and87 native
inputs verify unchanged. The combined shutdown/observer integration remains
prepared only. No tuning, rebuild, automatic retry or later-stage dispatch;
other28 unexecuted cases remain disabled and completed N3 is not rerun. All29
previously unexecuted cases remain unexecuted; M3 open, PR2 draft, M4 untouched.


The [fresh strict N3 cohort](evidence/m3-strict-n3-execution-2026-11-10/README.md)
passes9/9 on the frozen matched14-entry build with tracing and observer, in the
original seed-major order. Every30s case passes strict raw evidence, shutdown,
cleanup and integrity gates before advancing; zero failures/retries/tuning.
Historical N3 8PASS/1FAIL/unknown hang remains separate and unchanged. All29 later
campaign cases stay disabled; this cohort PASS does not complete M3 or queue a
merge. M3 open/PR2 draft/M4 untouched.


The [single explicitly authorized seed4211/30s shutdown diagnostic](evidence/m3-two-loss-4211-execution-2026-11-10/README.md)
passes on the frozen14-entry build: selected drops/restoration, strict SENSOR/
capture/accounting, observer lifecycle/socket stages and cleanup all pass. Both
bridges exit0/unforced within original5s waits. The historical hang is not
reproduced or explained, and the old N3 8PASS/1FAIL remains unchanged. No tuning,
automatic retry or further case; all29 remaining campaign stages stay disabled,
M3 open/PR2 draft/M4 untouched.


The [single authorized two-loss seed2903/30s shutdown diagnostic](evidence/m3-two-loss-2903-execution-2026-11-10/README.md)
passes on the frozen14-entry build: exactly one drop each for messages7/8,
verified selector restoration, strict SENSOR/capture/accounting, lifecycle/socket
and cleanup gates. Both bridges exit0/unforced under unchanged5s waits. No tuning,
4211 retry, additional case or historical FAIL relabeling; all29 campaign stages
remain disabled, M3 open/PR2 draft/M4 untouched.


The [explicit socket-disposition diagnostic](evidence/m3-socket-disposition-2026-11-10/README.md)
passes one new N0/seed1701/10s run on an isolated matched SDK/ROS build. All491
Python tests and the native trace contract pass. Robot explicitly reports four
already-invalid final slots; operator closes four traced handles with return0.
Lifecycle/stage/SENSOR/capture/cleanup gates pass. Old failures and original
N3 8PASS/1FAIL remain unchanged; no tuning/two-loss4211 or stage advancement,
all29 remaining campaign cases disabled, M3 open/PR2 draft/M4 untouched.


The [retained robot socket-marker diagnosis](evidence/m3-robot-socket-close-diagnosis-2026-11-10/README.md)
finds an instrumentation/gate mismatch: socket-close markers require a valid
handle during local shutdown, but the gate requires them for every role. All8
retained traces share39 non-socket-specific records; extra records are exactly
per-fd close triplets. Already-invalid robot link slots explain the local marker
absence; peer-first closure is consistent with timing, while exact earlier close
cause/result is unobserved. No gate or runtime change, new experiment or PASS
promotion; all29 campaign cases remain disabled.


The [worker lifecycle distinction and new N0 diagnostic](evidence/m3-bridge-shutdown-lifecycle-2026-11-10/README.md)
pass484 tests and the worker-exit observation gate using explicit ENOENT,
registered PID/start_ticks/parent/name and ordered join markers; PID reuse and
read errors remain failures. One new seed1701/10s attempt then stops at robot
stage coverage: missing socket_close_begin/end. Both bridges exit0/unforced;
cleanup and frozen evidence verify. Overall FAIL retained, no gate waiver,
tuning/two-loss4211 or further attempt; all29 campaign cases remain disabled,
M3 open, PR2 draft and M4 untouched.


The [reviewed native observer calibration](evidence/m3-observer-bootstrap-calibration-2026-11-10/README.md)
passes readiness and one unchanged blocked fixture after adding only fstatfs and
openat2 for the runtime bootstrap path. It captures24 nonempty kernel stacks in12
post-signal blocked samples, with no denied reads; target exits0/unforced in3.053s
under the unchanged5s wait. Synthetic ARM64 kernel-stack capture is calibrated;
original bridge-hang causality remains unknown. Previous failed attempts remain
recorded. No tuning or two-loss4211 retry; all29 campaign cases remain disabled,
M3 open, PR2 draft and M4 untouched.


The authorized [frozen N3 cohort](evidence/m3-n3-frozen-cohort-2026-11-09/README.md)
finished with8 strict passes and a final-case shutdown FAIL: the operator bridge
exceeded its5s SIGINT wait and required forced kill. No retry or tuning; all29
remaining campaign cases stay disabled. M3 remains open and PR2 stays draft.
The [observer-permission attempt](evidence/m3-observer-stack-permissions-2026-11-09/README.md)
failed in observer pre-exec setup before arming. A native-x86-64 filter was
prepared on an ARM64 Docker daemon; exact nested errno is not retained. The one
blocked target exited0 and the capability container/volume were removed. No retry,
production tuning or two-loss4211 run; all29 campaign cases remain disabled.


Final comparison and acceptance conclusion:
[M3_COMPARISON_AND_ACCEPTANCE.md](M3_COMPARISON_AND_ACCEPTANCE.md).
The reporting task is complete; the qualification status below remains open.
The concrete [N3/current-build closure plan](M3_CLOSURE_PLAN.md) is prepared,
with the authorized N3 outcome recorded and all later stages disabled.

**M3 is not ready to mark complete or merge.** The current evidence supports a
local Linux amd64/Jazzy simulator development result, with explicit failed and
unqualified gates. M0–M2 remain accepted only in their recorded scope; Intrinsic/
M4 is not started. PR2 stays draft. No new diagnostic cohort is scheduled here.

The milestone contract in [ARCHITECTURE.md](ARCHITECTURE.md) asks for reproducible
impairment evidence, preserved semantics and demonstrated benefit or justified
non-superiority. It does not require tuning DDS until it succeeds. A failed DDS
cold start is a measured comparison outcome; it supplies no steady-window latency,
sensor availability or resource denominator and must not be converted into a
numerical superiority claim.

| Gate | Current evidence and result | Remaining boundary |
|---|---|---|
|Core/ROS command semantics|[M2 acceptance](evidence/m2-ros-jazzy-2026-11-05/ACCEPTANCE.md); [sender reconciliation](evidence/m3-sender-reconciliation-2026-11-09/README.md) implements exact-row UNKNOWN on actual local abandonment; SDK81/ROS41 pass|Simulator only; no historical UNKNOWN replay/nonexecution inference|
|N1/N2 SRT execution|[N1](evidence/m3-srt-n1-full-2026-11-06/README.md), [N2](evidence/m3-srt-n2-full-2026-11-06/README.md): recorded three-seed600s cases and publication-age bounds|Those exact historical build hashes; not a fresh matrix on the latest install|
|N1/N2 DDS execution|[N1](evidence/m3-dds-n1-full-2026-11-06/README.md), [N2](evidence/m3-dds-n2-full-2026-11-06/README.md): full-duration execution evidence|DDS age gate remains open; N2/2903 robot has170,340 filtered vs170,338 file records, so capture population is not reconciled. Realtime Header ages are not SRT ingress interval bounds|
|N3 deterministic repair|[Frozen current-build cohort](evidence/m3-n3-frozen-cohort-2026-11-09/README.md): first8 strict cases pass with zero source skips; case9 two-loss4211 fails operator bridge shutdown|Existing5s SIGINT budget exceeded; forced kill/-9. Case9 accounting/capture revalidation not reached; cohort FAIL, no retry. Older case6 source-skip failure remains unchanged, no splice|
|N4 interruption/start/result/restart|[Failure controls and phase cuts](evidence/m3-failure-n4-2026-11-08/README.md), [remaining bounded cases](evidence/m3-n4-remaining-2026-11-08/README.md) retain passing scoped evidence and earlier failures|Bounded native/ROS fixtures, not every long combined load/hardware case|
|N5 SRT command progress|[Frozen probe cohort](evidence/m3-probe-loaded-cohort-2026-11-09/README.md): N0 8/8, N5 128/128,22 skipped offers|Qualified prior matched probe build, not newest sender-reconcile loaded qualification; SENSOR reduction/accounting is not full freshness/availability acceptance|
|N5 retained SENSOR freshness and bridge slots|[Offline audit](evidence/m3-n5-sensor-retained-audit-2026-11-09/README.md): all27,750 publications covered; exact modeled upper ages178.324341/182.559637ms <250ms; six balances0; fixed one-latest-sample/route/stage storage|Prior probe build/one300s seed only;465 unknown-age rejections and47,287 unobserved source samples retained. No continuous availability, measured queue high-water or hard SDK/process memory peak|
|Default DDS cold startup under N5|[Latest matched-build confirmation](evidence/m3-dds-loaded-confirmation-2026-11-09/README.md): N0 8/8; N5 FAIL before measurement with asymmetric sampled endpoint matching|Current default-DDS cold-start failure confirmed. No steady60s workload result, no unique fragmentation cause or default change|
|Age, CPU, memory and wire comparison|Existing source fences, endpoint/resource accounting and observation scopes retained|No common-origin age equivalence, complete observer/security-cost parity or controlled hardware-performance claim|
|Lifecycle and provenance|Latest DDS cohort: all6 native children exit0,4 containers/2 networks removed;146 raw hashes; matched runtime chain fixed; host407 pass|Does not erase prior missing-footer failures or qualify real robots/cross-host clocks|

## Concrete closure work

1. Freeze the build and scope being accepted. Earlier full matrices remain tied
   to their archived hashes; a passing historical run is not silently assigned to
   a new binary. New sender reconciliation has focused recovery/capacity/result-
   race and full affected SDK/ROS checks, but no new loaded SRT cohort is claimed.
2. The [retained operator shutdown diagnosis](evidence/m3-n3-shutdown-diagnosis-2026-11-09/README.md)
   is complete to its observation limit. Sampler and packet data end before
   SIGINT; absent footer alone does not locate the blocking stage. The operator
   worker is plain SDK, not ROS rate backend. No specific corrective patch is
   justified yet; a narrow stage/blocked-stack visibility design would be the
   discriminating next evidence, subject to a separate scope decision. The new shutdown-tracing matched build has a separate bounded live calibration:
   default-off and healthy stages PASS, independent3s wait sampling PASS, but
   kernel-stack access FAIL (22 post-signal reads denied/errno13). No two-loss4211
   retry or permission fallback. A subsequent one-shot permission attempt failed before observer arming;
   native-x86-64 in-process filter versus ARM64 daemon is an unchecked
   compatibility blocker, while exact pre-exec errno is unavailable. Target
   cleanup and permission-container removal pass. The later reviewed native
   profile passes synthetic kernel-stack calibration (24/24 nonempty reads in12
   post-signal samples), preserving these earlier failures. Real bridge shutdown
   stacks and hang attribution remain unperformed; no automatic run or timeout change. Keep8 strict PASS/1 FAIL, the5s
   lifecycle gate and all29 remaining stages disabled; no retry or cohort splice.
3. The retained-run N5 publication-age assessment is now complete in the
   [offline audit](evidence/m3-n5-sensor-retained-audit-2026-11-09/README.md).
   All publication histograms reconcile; unknown/missing populations are explicit,
   and fixed bridge slots are source-established. Keep continuous availability,
   measured occupancy peaks and total SDK/process memory caps unavailable rather
   than upgrading them to passes or launching another experiment. This does not
   promote the old probe build into newest-build/all-seed qualification.
4. The [comparison and acceptance statement](M3_COMPARISON_AND_ACCEPTANCE.md)
   is now complete: default DDS has no latest loaded steady window, age/security/
   resource equivalence is not established, and no general superiority claim is
   justified. Failed/unavailable populations, including the DDS N2 capture
   discrepancy, remain explicit. This reporting closure grants no M3 acceptance,
   changes no source-slot threshold and does not schedule another experiment.

No automatic N3 retry, DDS fallback experiment, provider patch, ARP study or new
tracer follows from this review. Existing no-tuning/no-forced-expiry/no-historical-
replay constraints persist. A scoped acceptance proposal can be reviewed after
these concrete boundaries are resolved; this document grants no waiver, changes
no acceptance threshold and authorizes neither merge nor M4 development.
