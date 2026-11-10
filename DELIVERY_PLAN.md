# Delivery focus — 2026-11-09

The [bounded native SDK/ROS calibration](evidence/m3-sdkros-task-calibration-preparation-2026-11-10/README.md)
is prepared on freeze4d64d753f6eb, **not run; execution disabled, no grant**.
One native readiness check then one N0/1701/10s diagnostic on unchanged matched
SDK/ROS builds, integrated per-thread/launch/workload gates and original five-second
child waits.28 preparation tests PASS; runtime read-only preflight quiescent.
All38 campaign IDs/stages disabled, N1/2903 FAIL and1PASS/1FAIL/7unexecuted preserved.
No tuning/retries/builds/live run. Short diagnostic is not campaign coverage;
actual SDK/ROS gates remain unqualified until run. M3 open/PR2 draft/M4 untouched.

The [campaign per-thread assessor integration](evidence/m3-campaign-task-assessment-integration-2026-11-10/README.md)
is wired and verified offline:25 integration,42 assessor and511 existing tests
PASS. Exact calibrated collector/assessor, explicit native activation and closed
launch/exec/clock gates feed the unchanged campaign workload/profile checks.
Execution remains blocked:all38 IDs/stages disabled, no freeze/grant/live run,
tuning or retries. N1/2903 FAIL and1PASS/1FAIL/7unexecuted preserved. Native
integrated SDK/ROS/race/overhead coverage remains open; M3 open/PR2 draft/M4 untouched.

The [native post-SIGINT calibration](evidence/m3-task-post-sigint-calibration-execution-2026-11-10/README.md)
PASSES readiness and one controlled fixture on freeze8acc653d87ad. Two post-signal
readable worker observations precede controlled join and supported enumeration
absence while parent lives; exact candidate lifecycle gate passes.9 raw stacks
OK/0unavailable, child exit0/unforced/747.3345ms signal-end-to-reap. Cleanup and
integrity PASS. No tuning/retries/N1 rerun; its FAIL and1PASS/1FAIL/7unexecuted
remain unchanged, all38 campaign IDs disabled. This qualifies one controlled
post-signal absence path; exact mid-read race/SDK/ROS/overhead remain unqualified.
M3 open/PR2 draft/M4 untouched.

The [bounded native post-SIGINT calibration](evidence/m3-task-post-sigint-calibration-preparation-2026-11-10/README.md)
is prepared on freeze8acc653d87ad, **not run; execution disabled and no grant**.
33 offline preparation tests pass. Exact assessment candidate; two pre-signal
and two post-signal readable worker samples, then controlled join/absence before
parent exit, with unchanged five-second child wait and observer policy/budgets.
Unrelated CI remains running and blocks future execution preflight; untouched.
No tuning/retries/N1 rerun. Its FAIL and1PASS/1FAIL/7unexecuted are preserved;
all38 campaign IDs stay disabled, M3 open/PR2 draft/M4 untouched.

The [offline per-thread assessment candidate](evidence/m3-task-metadata-assessment-2026-11-10/README.md)
adds strict schema, identity, timing and prior-cache rules plus a prospective
lifecycle adapter.42 new /28 collector /23 preparation /511 existing tests PASS.
Retained calibration:5 readable records and1 observed absence,0 confirmed task
exits. Native post-SIGINT/race coverage remains unqualified; no campaign integration,
freeze, grant or live run. N1/2903 FAIL and1PASS/1FAIL/7unexecuted remain unchanged;
all38 campaign IDs disabled, no tuning/retries. M3 open/PR2 draft/M4 untouched.

The [bounded task-visibility calibration](evidence/m3-task-visibility-calibration-execution-2026-11-10/README.md)
PASSES readiness plus one controlled fixture on freeze6357a2c0f58d. Two matched
worker observations then a complete-enumeration absence hint;5 native stack reads
OK/0unavailable, all task/read/schema/policy gates and cleanup/integrity pass.
No tuning/retry/N1 rerun; its FAIL and1PASS1FAIL7unexecuted remain unchanged, all38
campaign IDs disabled. This calibrates visibility only, not a new acceptance rule.
M3 open/PR2 draft/M4 untouched.

The [bounded visibility calibration](evidence/m3-task-visibility-calibration-corrected-preparation-2026-11-10/README.md)
is prepared in corrected freeze6357a2c0f58d: one native readiness check then one
controlled task fixture, exact candidate6deab3c5e83e/private host binding, unchanged
policy/budgets. **Not run; no grant, tuning, retries or N1/2903 rerun.**23 offline
preparation tests pass; unchanged28 candidate/511 existing results retained. Earlier
freeze4e8c9ee78f1f failed host-import verification and is preserved. N1 failure/
1PASS1FAIL7unexecuted unchanged; all38 campaign IDs disabled, M3 open/PR2 draft.

The [per-task visibility candidate](evidence/m3-task-identity-visibility-2026-11-10/README.md)
adds default-off, bounded task identity/read/absence records with28 offline
regressions and511 existing tests PASS. One stack attempt; explicit missing,
reuse/error/truncation evidence,512-entry bounded history. No gate/filter/driver
change, live experiment, tuning, retry or new freeze/grant. N1/2903 remains FAIL,
cohort1PASS/1FAIL/7not-executed unchanged; remaining cases/stages disabled. M3 open.

The [offline N1/2903 diagnosis](evidence/m3-n1-2903-thread-evidence-diagnosis-2026-11-10/README.md)
identifies a task enumeration/read race during provider cleanup:3 named SRT
threads have12 ENOENT file reads while their parent remains alive. The assessor
checks parent lifetime without per-task exit evidence. Normal cleanup exit is
strongly supported, but individual exit/reuse proof is absent; failure remains.
No fix/tuning/test/experiment/Docker/retry or new grant. Original1PASS/1FAIL/7not-
executed unchanged; remaining cases disabled, M3 open/PR2 draft/M4 untouched.

The [N1/N2/N5 cohort](evidence/m3-current-long-execution-2026-11-10/README.md)
stopped at the first failed gate: **1 PASS /1 FAIL /7 NOT EXECUTED**. N1/1701/600s
passes all strict gates (300/300 commands). N1/2903 inner workload passes but
strict observer coverage fails on3 ENOENT thread-stack reads after SIGINT; normal
child exit0 does not waive missing evidence. Both cleanup/integrity postflights
pass. No tuning/retry/fix or later case; seven remaining cases and other stages
stay disabled. M3 open/PR2 draft/M4 untouched.

The [nine remaining current-build cases](evidence/m3-current-long-preparation-2026-11-10/README.md)
are prepared in freeze868a21578a61: N1/N2 three seeds each at600s, then N5 three
seeds at300s, unchanged matched build and stabilized lifecycle/observer. **No live
run or grant; execution disabled, no tuning or automatic retries.** All29 completed
N0/N3/N4 IDs are excluded/disabled.21 preparation,39 lifecycle,4 import and511
existing tests PASS. Prior failures unchanged; M3 open/PR2 draft/M4 untouched.

The [fresh corrected-assessor N4 cohort](evidence/m3-current-n4-corrected-execution-2026-11-10/README.md)
**PASSES19/19** on freezeecb0d1346932:13 native,3 ROS freshness and3 crash/restart
cases. Driverexit0, all19 strict/cleanup/integrity gates pass; no tuning or retries.
Original crash uncertainty/committed-result/no-replay semantics retained. Previous
N4 failure unchanged. Current-build N0, fresh N3 and bounded N4 now pass within
recorded scope; nine N1/N2/N5 cases remain disabled. M3 open/PR2 draft/M4 untouched.

The [fresh N4 freeze](evidence/m3-current-n4-corrected-preparation-2026-11-10/README.md)
is prepared with the corrected assessor: freezeecb0d1346932 binds all19 original
ordered cases and exact assessordd1fa84dc1ed on the unchanged matched build/fixture.
**Execution disabled: no grant, live run, rebuild, tuning or automatic retry.**
8 binding,20 preparation,10 JSON regression and511 existing tests PASS. Prior
16PASS/1FAIL/2not-executed stays unchanged; nine other unexecuted cases disabled,
ten completed N0/N3 excluded. M3 open/PR2 draft/M4 untouched.

The [N4 assessor JSON fix](evidence/m3-current-n4-assessor-json-fix-2026-11-10/README.md)
is verified offline:10 regressions,20 preparation tests and511 existing tests PASS.
The separate candidate normalizes recomputed crash proofs at the JSON boundary;
all17 retained started cases reassess consistently, while the original failure
reproduces. Original live result remains16 PASS/1 FAIL/2 NOT EXECUTED. No live
run, Docker call, build, new freeze/grant, tuning or retry; two remaining N4 and
nine other unexecuted cases stay disabled. M3 open/PR2 draft/M4 untouched.

The [current-build N4 execution](evidence/m3-current-n4-execution-2026-11-10/README.md)
stopped at the first failed gate: **16 PASS / 1 FAIL / 2 NOT EXECUTED**. All13
native and3 ROS freshness cases pass; crash-before-admission fails strict audit
comparison. Retained proofs differ only in trace-name map integer versus JSON
string keys; JSON-round-tripped proofs match, but the case remains FAIL. All17
cleanup/integrity postflights pass. No tuning/retry/fix or further run; two N4
crash cases and nine other unexecuted cases stay disabled, completed10 N0/N3
excluded. M3 open/PR2 draft/M4 untouched.

The [current-build N4 preparation](evidence/m3-current-n4-preparation-2026-11-10/README.md)
freezes exactly19 cases:13 native interruption/query,3 ROS freshness and3 ROS
crash/restart. Freeze513f13066b30 uses the unchanged matched SDK/ROS build; the
standalone peer alone passed isolated compilation and static link inspection.
20 preparation tests and511 existing tests PASS offline. **No N4 case run or
execution grant:** all19 remain disabled, with first-failure stop/no automatic
retries/no tuning. Other9 unexecuted N1/N2/N5 cases stay disabled; completed10
N0/N3 cases are excluded. Runtime qualification remains pending; M3 open/PR2 draft.

The [stabilized current-build N0 case](evidence/m3-current-n0-stable-execution-2026-11-10/README.md)
PASSES seed1701/300s:150/150 commands, no unresolved/skipped slots, six SENSOR
balances0, modeled age bounds below250ms, complete capture/provider and per-launch
lifecycle/native-observer gates. All4 children exit0/unforced; cleanup/integrity
verify. One fresh case, no tuning/retry. Other28 stages remain disabled, historical
failures preserved, M3 open/PR2 draft/M4 untouched.


The [stabilized-lifecycle N0 freeze](evidence/m3-current-n0-stable-preparation-2026-11-10/README.md)
is prepared for exactly seed1701/300s. Freeze98a357e418c2 binds stabilized harness,
matching per-launch assessor/helper SHAs and unchanged matched build. Execution
disabled, no grant/live run.12 preparation,39 lifecycle and4 runtime-import tests
pass offline; prior511-test PASS retains its scope. Runtime/images and retained
hashes verify. No tuning/retry/rebuild; other28 stages disabled, N0 unqualified,
M3 open/PR2 draft/M4 untouched.


The [complete offline lifecycle verification](evidence/m3-current-n0-lifecycle-stabilization-2026-11-10/README.md)
passes39 lifecycle tests (including13 whole-flow tests),4 runtime-import checks
and511 existing tests. Actual robot/RPC/wrapper/start-reset-stop methods and host
release/cleanup blocks run against modeled dependencies. Spawn failures now close
logs/retain evidence, and cleanup refreshes final catalogs. No N0/live fixture,
new freeze/grant, tuning or retry; old inputs/builds/failures unchanged, other28
stages disabled, N0 unqualified and M3 open/PR2 draft/M4 untouched.


The [per-launch trace/lifecycle fix](evidence/m3-current-n0-trace-lifecycle-fix-2026-11-10/README.md)
gives warmup/final bridges separate exclusive trace paths, catalogs and attested
identities. Child outcomes and stage/socket proofs bind to each launch; native
observer assessment selects the final operator, not the first child.26 lifecycle,
4 runtime-import and511 existing tests pass offline. No N0 rerun/new freeze/grant,
tuning or retry; old inputs/builds/failures unchanged, other28 stages disabled,
N0 unqualified and M3 open/PR2 draft/M4 untouched.


The [explicit-identity N0 attempt](evidence/m3-current-n0-bound-execution-2026-11-10/README.md)
passes initial identity/capability readiness but fails the planned warmup reset:
replacement robot exits1 with cannot create shutdown trace. The retained trace
path belongs to its prior launch and is reused despite O_EXCL creation. No300s
measurement or observer; one case/no tuning/retry, all28 other stages disabled.
Cleanup and frozen integrity verify; N0 remains unqualified, M3 open/PR2 draft.


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


M0–M2 are accepted for the recorded Linux amd64/Jazzy simulator baseline. M3 is
the delivery blocker. PR2 remains draft; Intrinsic/M4 is not started. Current
implementation and qualification are described by the latest HANDOFF entries.
The current comparison and acceptance decision is in
`M3_COMPARISON_AND_ACCEPTANCE.md`: reporting complete, M3 completion not accepted
under the unchanged plan. No new experiment or waiver is queued.
`M3_CLOSURE_PLAN.md` now gives the concrete N3/current-build closure sequence;
the authorized N3-only execution is now recorded as8 strict passes/final shutdown FAIL,
with every later stage disabled. Retained diagnosis now locates the observation gap but cannot name the blocked
function. Default-off behavior/stages and independent wait sampling passed the
initial bounded live calibration. Earlier stack-access and observer startup
failures remain retained. The latest native bootstrap policy passes readiness
and synthetic kernel-stack capture; real bridge stage/stack capture and hang
attribution are still unperformed. No corrective patch, timeout change, original
case retry or campaign advancement is queued.

## Execution rules

- Work against acceptance blockers rather than adding successive forensic
  studies. Preserve historical UNKNOWN/rejected outcomes without making their
  impossible retrospective reconstruction a prerequisite for forward progress.
- Reuse exact qualified builds and archived baseline checks. Rebuild/retest the
  affected layers when code changes; do not repeat the entire matrix for prose
  or read-only analysis changes. Never overlap heavy work with live capture.
- One final bounded probe-traced cohort in this diagnostic chain: N0 control,
  then one300s N5 slot. No retry to obtain a failure, no new instrumentation by
  default, no automatic extension. Either outcome must select a concrete next
  engineering action or an explicit acceptance decision.
- Keep raw evidence/hash integrity, but publish compact gate summaries and
  relevant probe branches. Do not re-run broad packet/ARP archaeology when the
  existing capture gates pass and it does not change a delivery decision.
- Current constraints persist: no tuning, forced expiry, historical118 replay or
  silent resumption of stopped4211. Diagnostic observations never authorize
  journal outcomes or re-execution. Scope changes must be explicit.

## Ordered work and exit criteria

| Priority | Deliverable | Exit criterion |
|---|---|---|
|1|Loaded per-probe evidence on the existing calibrated build|One frozen cohort completed or stopped, probe admission/queue/SDK distinctions reported, next engineering action selected; then close this instrumentation loop|
|2|Pending-input/journal reconciliation|Concrete authoritative transport-to-coordinator result path or documented contract decision; no fabricated EXPIRED/success, no ticket reuse, meaningful recovery tests|
|3|M3 qualification gaps|Finish actual ROS SENSOR N3 freshness/repair gates and loaded DDS discovery/comparison; reuse completed N1/N2 and bounded N4 evidence within their original scope|
|4|Acceptance review|One consolidated gate report for command safety/progress, sensor age/bounds, teardown, matrix coverage and resource/security comparability; open gates remain explicit|
|5|Intrinsic/M4|Start its separate pinned API/toolchain inventory after the bridge milestone decision; no remote real-time or motion capability inferred|

## Current checkpoint

Priority1 is closed by `evidence/m3-probe-loaded-cohort-2026-11-09/`: N0 8/8,
N5 128/128,22 skipped offers, actual busy/timeout/old-echo branches retained.
No further diagnostic cohort or new trace facility is scheduled automatically.
Priority2 is implemented in `evidence/m3-sender-reconciliation-2026-11-09/`:
opaque transport receipts drive exact-row UNKNOWN reconciliation, with one-use/
worker-generation guards and bounded admission. SDK81/81 pass; matched ROS/host
validation is recorded with the change. Priority3 is next: actual ROS SENSOR N3
freshness/repair and loaded DDS discovery/comparison acceptance. Historical
UNKNOWN outcomes remain uncertainty, not a requirement to reproduce them.

### N3 follow-up checkpoint

The fixed30s three-seed matrix in
`evidence/m3-n3-thirty-second-matrix-2026-11-09/` is audited FAIL: five prefix cases
pass; two-loss2903 skips3 IMU source slots despite cadence within1%. The old
harness missed the frozen zero-skip gate and continued; three later cases are
supplementary outside the intended stop boundary. Guard corrected, host402 pass;
original harnessPASS/exit0 and all measurements retained. All transport/freshness/
fault subgates pass, but do not close the planned N3 matrix or retry automatically.
Next: loaded DDS discovery/comparison confirmation with existing defaults, then
consolidate acceptance decisions including the prospective source-slot allowance.

### DDS confirmation and acceptance checkpoint

`evidence/m3-dds-loaded-confirmation-2026-11-09/` closes the bounded confirmation
question: current matched-build system DDS/simultaneous N0 passes8/8 commands;
N5 cold start FAILS sender readiness before measurement. Operator never samples
robot CONTROL/HELLO publishers or a received HELLO; robot matches all4 endpoints
and receives407. Captures/competitor/shutdown gates pass; journals empty in N5.
No retry, startup-order fallback, decoder/tracer expansion or default change.

Use `M3_ACCEPTANCE_REVIEW.md` as the current closure list. A DDS failure is a
comparison result, not an obligation to tune DDS until it passes. Next useful
work is the existing-capture N5 SENSOR freshness/bounds assessment and explicit
comparison limitations; any N3 source-slot contract change remains prospective.
Keep M3 open/PR2 draft; no automatic new cohort or acceptance waiver.

### Retained N5 SENSOR assessment completed

`evidence/m3-n5-sensor-retained-audit-2026-11-09/` recomputes the complete frozen
300s N5/1701 publication-age/checkpoint population:27,750 publications, modeled
upper maxima178.324341/182.559637ms below250ms, six conservation residuals0.
465 unknown-age rejections,74 other rejections and47,287 unobserved source samples
remain explicit; no per-SAMPLE cause is manufactured. Fixed latest-only bridge
slots are source-established, but continuous occupancy peaks/availability and
hard SDK/process memory caps are unavailable. This closes that retained-run age
assessment, not newest-build/all-seed/full N5 or M3 acceptance.

Offline only:303 original hashes and six frozen source blobs verify,413 host
checks pass; no runtime experiment/build/tuning/journal recovery/replay. Next is
the comparison/acceptance statement with these limits and the prospective N3
source-slot contract decision; no automatic new experiment.

### Comparison and acceptance statement delivered

`M3_COMPARISON_AND_ACCEPTANCE.md` completes Priority4's consolidated reporting
exit criterion while leaving Priority3's open qualification explicit. Supported
retained bridge behavior is documented; a general SRT-over-DDS speed/resource/
security claim or DDS equivalence is not established. The DDS N2 capture
population exception and clock-rejected age populations are retained, not hidden
behind older execution PASS labels. Latest DDS N5 never entered measurement.

M3 completion is not accepted under the unchanged plan: the frozen N3 cohort
fails, the newest candidate does not inherit older full profile/seed matrices,
and comparison age/capture coverage has the listed limits. This is not a claim
that all bridge properties fail or that DDS must be tuned until successful.
No source-slot waiver, runtime threshold change, merge, M4 start or automatic
new experiment follows. Any future scope/contract proposal must be explicit and
prospective; the current reporting request is complete.

### Concrete N3/current-build closure plan prepared

`M3_CLOSURE_PLAN.md` targets the existing sender-reconcile candidate identified by
manifest929d1f7c7727, not a moving HEAD or a mixture of build variants. Read-only
checks verify13 manifest entries and86 unchanged native build inputs. The current
zero-skip guard still rejects retained N3 case6; old later cases stay excluded.
No threshold relaxation, cohort splice, runtime test, build or experiment occurs.

Preparation must bind the old N4 fixtures to the matched IPC4 SDK/worker/ROS paths
and supply a shared strict all-stage assessor. Neither is represented as ready.
If explicitly authorized later, order is strict9-case N3, combined300s N0,
19 bounded N4 cases, six600s N1/N2 and three300s N5 cases. All38 proposed cases are
not scheduled/not authorized; first failed declared gate stops later work, no
retry-until-pass. The source-time sum84.5minutes excludes N4 and all overhead,
not a duration promise. No new DDS or forced-expiry case is proposed.

This request's deliverable is the concrete plan/coverage ledger/readiness record.
M3 remains not accepted as complete/PR2draft/M4untouched. Further planning or
preparation does not silently lift the user's no-new-experiments instruction.

### Implemented contract: authoritative sender submission receipt

- Give each admitted sender proof a bounded, opaque submission receipt that the
  coordinator can retain. The transport updates it at its actual handoff/drop
  decisions; do not consume lossy CommandTrace as authority. Bound storage by
  outstanding tracked admissions and fence receipt reuse by original identity,
  session/epoch, payload and generation.
- A proved pending/outbound drop must reach the coordinator even while its
  current job has completed. Reconcile that exact sender entry conservatively
  to UNKNOWN/reconcile_required, preserving revision/result rules. Never invent
  receiver EXPIRED/success, never invalidate unrelated entries or reset device
  generations, and never reissue a command ticket.
- Preserve the existing query-first treatment of provisional UNKNOWN (already
  nonterminal in the endpoint). A later authoritative peer result may reconcile
  it; NOT_FOUND remains insufficient for expiry or replay. Known accepted/final
  peer states must not be overwritten by a delayed local receipt.
- Validate receipt before/after SDK acceptance, stale/reused/wrong-context
  receipts, result races, worker restart/storage failure and bounded saturation.
  Use fresh fixtures and revocation/context loss where possible; no live forced
  expiry of historical118 or a retry of the stopped experiment.
- This is a correctness/status-delivery change, not clock/network tuning. Rebuild
  and test affected SDK/ROS layers once the implementation is concrete, then
  return to the remaining N3/DDS acceptance gates.

The SENSOR contract permits drops under N5 overload; freshness and boundedness
are the acceptance criteria, not lossless delivery. Raw loss percentages alone
must not create another open-ended diagnostic program. Cross-host clock,
hardware/offload and security/resource limits retain their declared scopes;
simulator acceptance is not silently promoted to those environments.

Near-term progress reports should state which gate closed, which blocker remains
and the next concrete change. Test counts and new trace points are supporting
evidence, not the primary measure of delivery progress.
