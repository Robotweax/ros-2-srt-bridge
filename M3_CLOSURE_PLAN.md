# M3 acceptance closure plan — 2026-11-09

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


**Latest authorized N3 execution: FAIL,8 strict passes then a shutdown failure.**
See [the frozen current-build cohort](evidence/m3-n3-frozen-cohort-2026-11-09/README.md).
The exact9-case N3-only scope was authorized and executed once, without tuning,
rebuild or retry. Case9 two-loss4211 exceeded the existing5s operator bridge
shutdown wait and was force-killed. No remaining stage was authorized or launched;
all29 N0/N4/N1/N2/N5 cases remain disabled. M3 remains open, PR2 draft and M4 untouched.

The plan below preserves its fixed gates, original case order and historical
planning snapshots. Neither the new8-case passing prefix nor the old5-case prefix
closes N3. No automatic retry, cohort splice, threshold relaxation or stage
advancement follows. The [retained shutdown diagnosis](evidence/m3-n3-shutdown-diagnosis-2026-11-09/README.md)
is complete to its observation limit: no post-signal stage/stack data, hence no
uniquely identified blocked function. The separate [bounded shutdown calibration](evidence/m3-shutdown-live-calibration-2026-11-09/README.md)
on a new matched build passes default-off, healthy stages and independent wait
sampling, but fails kernel-stack access (22 denied post-signal reads). No two-loss
4211 retry or permission change occurred. At that point stack capture was uncalibrated;
all29 remaining campaign cases remain disabled and no corrective patch/experiment is queued.
A later scoped-permission blocked-target attempt failed before observer arming;
the old native-x86 filter/ARM64 daemon path remains unqualified. No retry followed;
its capability container and output volume were removed.

The [reviewed native observer calibration](evidence/m3-observer-bootstrap-calibration-2026-11-10/README.md)
passes readiness and one unchanged blocked fixture after adding only fstatfs and
openat2 for the runtime bootstrap path. It captures24 nonempty kernel stacks in12
post-signal blocked samples, with no denied reads; target exits0/unforced in3.053s
under the unchanged5s wait. Synthetic ARM64 kernel-stack capture is calibrated;
original bridge-hang causality remains unknown. Previous failed attempts remain
recorded. No tuning or two-loss4211 retry; all29 campaign cases remain disabled,
M3 open, PR2 draft and M4 untouched.


## 1. One candidate, with a concrete coverage ledger

Proposed qualification candidate: `sender-reconcile-929d1f7c7727`, identified by
[its existing binary manifest](evidence/m3-sender-reconciliation-2026-11-09/binary-verification.json),
SHA256 `929d1f7c7727b6c9ba363762074557873d0ffeb6ed6a2b4ab75957d341ee0fc7`.
Use `install/bridge-sender-reconcile` and `install/m3-sender-reconcile-ros` together,
private worker IPC4, the pinned amd64/Jazzy image and SRT52be7c86 provider. The
current source check finds all86 recorded native build inputs unchanged and all13
manifest binary/archive/test entries matching. No rebuild is needed to name or
verify this candidate. SDK81/ROS41/host413 are retained results, not new test runs.

| Area | Credit available now | Closure needed for this candidate |
|---|---|---|
|SDK/ROS components|Recorded SDK81/ROS41, current recovery/receipt/execution guards|Reuse; do not repeat solely for prose or unchanged native inputs|
|N3|New candidate cohort:8 strict prefix passes, case9 shutdown FAIL; original cohort failure retained|Diagnose operator shutdown from retained evidence; no retry, splice, threshold relaxation or later-stage advance|
|Combined SRT N0|Native checks and30s sensor-only baseline are useful but different|One300s combined candidate control|
|N1/N2|Historical3-seed600s series retain their own binary scope|Six600s candidate cases|
|N4|Current component guards, matched fixture source/build-link preparation and earlier bounded network/ROS evidence|All19 current-build runtime cases remain disabled; build/link alone is not qualification|
|SRT N5|Prior probe-build128/128 and full retained publication-age audit|Three300s candidate cases; fresh plan, not resumption of old stopped4211|
|DDS comparison|Current-build N0 8/8 and N5 cold-start failure already documented|Reuse the measured outcomes and explicit age/capture/security limitations; no new DDS experiment proposed|
|Final acceptance|Comparison reporting is complete|Review candidate-labelled coverage without waiving N3, mixing builds or asserting unsupported superiority|

The machine-readable [coverage ledger](evidence/m3-closure-plan-2026-11-09/coverage-ledger.json)
keeps these credits and gaps separate. Historical successes are not discarded,
but are not relabelled current-build full-matrix passes.

For N3/combined runs, keep the existing200ms maximum clock interval,1000ppm drift
assumption,1ms timestamp error,5s probe-age limit and original250ms SENSOR/5s
command budgets. Preserve existing probe attempt/pending rules and all queue/
crypto settings. Combined capture retains immediate/full-snapshot mode,32768KiB
buffer request and16 files x16MB rotation; N3 keeps its separate existing filtered
identity/measurement recorder limits. Exhaustion or overwritten capture fails
instead of triggering an automatic buffer increase. N4's existing diagnostic
barriers/watchdogs are separate fixture settings, not production overrides.

## 2. Preparation before any future live case

The dispatcher is wired and the isolated native fixture compile/link is now
validated under the user's explicit preparation-only scope.440 offline Python
checks pass. See [current build/readiness evidence](evidence/m3-dispatcher-fixture-validation-2026-11-09/README.md).
That preparation step launched no fixture or campaign case. The later N3-only
execution is recorded above; all29 other cases remain disabled. Original planning
snapshots retain their original scope.

1. **Strict dispatch and assessment.** `tools/m3_campaign_dispatcher.py` now
   maps all38 declared slots to single-case adapters. It checks the complete
   freeze before/after each case, applies the shared closed-case assessor and
   recorded cleanup gates, then permits the next slot. Inner harness status is
   separate. Failure stops every later slot with no retry or resumption. All
   adapter calls and complete campaign transitions were tested with mocks only;
   live dispatch remains unvalidated. Combined capture assessment consumes the
   original summaries rather than independently reparsing every packet.
2. **Matched N4 fixture build/link.** The standalone peer compiled and linked
   in a network-disabled pinned-image container against the selected SDK and
   provider, into `build/m3-n4-sender-reconcile-peer`. Imported prefixes, selected
   worker macro, linker map and ELF metadata pass static audit. The36-file
   binding passes native preflight. Production and old fixture prefixes were
   not rebuilt. No peer/worker execution or loader/runtime/IPC validation was
   performed. IPC4 retains its existing `--worker-ipc-v3` process launch flag.
3. **Offline negative controls.** Source skips, missing observers/footer,
   frozen input drift, unresolved command progress, outage readback/timing,
   incomplete capture and cleanup failures reject independently of inner PASS.
   Dispatcher checks additionally bind the output and exact case order and
   prove no later dispatch after failure.440 host Python tests pass; no runtime
   matrix case is closed by these tests.
4. **Frozen evidence identity and execution gate.** The new disabled
   `campaign-freeze.json` binds the plan, invocation settings, candidate/preserved
   builds, peer binding, provider/image, helpers and full source inventory.
   No authorization grant is created. A future execute request requires a
   separate exact-freeze/order/fresh-output grant after an explicit scope change;
   the current no-new-experiments instruction remains in force. Fresh journals
   never reopen old identities and no old-cohort splice is supported.

The original planning step applied the zero-skip guard to all9 retained N3
results: the sixth remains failed and the final3 remain `outside_stop_boundary`.
Neither this preparation nor the later build changes those results. Original
[readiness.json](evidence/m3-closure-plan-2026-11-09/readiness.json) describes the
then-missing port/orchestrator; the new readiness delta records their preparation
completion without implying live qualification or M3 acceptance.

## 3. First execution stage: strict N3, only if separately authorized

Use the existing matched-layout multiroute runner and the corrected window gate.
One new campaign, new evidence identity, once per case, in this exact order:

| Seed | Order | Duration per case |
|---|---|---:|
|1701|baseline → one-loss → two-loss|30s each|
|2903|baseline → one-loss → two-loss|30s each|
|4211|baseline → one-loss → two-loss|30s each|

This is9 cases/270 nominal source seconds, not a promised elapsed run time. The
existing failed campaign stays failed; its five passing cases remain supporting
coverage, not stitched into a claim that this new cohort passed9/9.

Keep all existing N3 gates:

- IMU200Hz/joints50Hz within1%, **zero skipped source slots**, actual30..31s fence.
  Source/sample hard limits10000/75000 and allowances7750/15501 stay fixed.
- Actual SDK/handshake/tuple/socket identity selects one source8, or sources7/8 in
  one four-source/one-parity row. Each selected classifier records exactly one
  drop; parity is not selected. One-loss must recover the original typed hash/
  stamp while the classifier is installed. Two-loss must show the selected pair
  absent at the drained cutoff, with later fresh progress on both routes.
- Full source/admission/SDK/receiver/typed accounting, six residuals0, no unexpected
  receiver gap/rejection, complete zero-loss native/full-PCAP/trace populations,
  qualified context/QoS/clock, per-route upper ages<=250ms and clean shutdown.

Any source skip fails this stage even if average cadence is within1%. Stop the
remaining campaign; retain the exact event, verdict and cleanup. Do not reschedule
the same case, extend a deadline, alter source pacing or relax the zero-skip rule.
The retained data do not prove a unique source-delay cause, so a passing future
cohort cannot be guaranteed without execution. Another failure would require a
separate engineering/scope decision, not automatic repeated trials.

## 4. Current-build coverage after N3

Each stage below requires the earlier gates to pass and its own preparation to be
ready. None is launched or scheduled by this document.

| Order | Candidate stage | Proposed future cases | Exit criterion |
|---|---|---:|---|
|A|Combined N0,1701|1 x300s|Original typed/clock/age/accounting/capture/lifecycle gates and positive closed-journal command progress on the candidate|
|B|Bounded N4 network/ROS|19, detailed below|Phase placement, restored freshness, correct durable outcome and no accepted-command replay; all children/namespace cleanup accounted|
|C|N1,1701→2903→4211|3 x600s|Candidate-labelled complete cases with fixed20±5ms/1% profile and declared safety/progress gates|
|D|N2,1701→2903→4211|3 x600s|Same, fixed60±15ms/3% profile and unchanged250ms publication bound|
|E|N5,1701→2903→4211|3 x300s|Fixed512kbit/s roots/16-packet children and measured128Kbit competitor; positive command/typed progress, complete ages/reductions/accounting and bounded bridge storage|

Nominal source time for N3 plus A/C/D/E is5,070s (**84.5minutes**), excluding all
startup, drain, analysis, teardown, N4 cases and preparation. N4 ROS sensor cases
add45 nominal source seconds. This is a bounded proposed workload, not a wall-
clock estimate or permission to run it. Failure can stop it much earlier.

For combined cases, reuse `tools/run_m3.py --runtime-layout sender-reconcile
--skip-build` with the exact profile/seed/duration; do not run archived full-matrix
scripts which select older installations. Existing command and provider/SENSOR
diagnostics, native capture and source-fenced histogram/accounting readers must
be explicitly frozen in the future run manifest. No sample-trace expansion for
long windows, new ARP study, tracer or provider patch is part of this plan.

### N4 case list and required outcomes

- 12 native cases: admission-before-commit, durable-dispatch-before-start,
  atomic-start-before-effect and committed-result phases, each with both,
  operator→robot and robot→operator cuts. Preserve the existing2s hold, kernel
  drop/readback evidence, original5s sender budget and earlier mapped receiver
  fence. Use the existing per-phase outcome checker: success needs matching valid
  durable proof/one effect; a permitted safe rejection/expiry needs zero effects
  and its actual reason. A committed result must remain successful. A safe decline
  is recorded distinctly, never renamed success or automatically retested.
- 1 native withheld-result QUERY case, both directions/2s: the existing committed
  success must be recovered with positive QUERY observations, one effect and one
  original COMMAND handoff. Do **not** invoke the six-second `--remaining-native`
  overrun batch; forced-expiry experiments are outside this plan.
- 3 ROS freshness cases, one per direction,15s source window and existing2s cut:
  original payload/order, age/counter balances, restored qualified context and no
  stale queued replay. Reduction is counted, not treated as lossless delivery.
- 3 ROS crash/restart cases: before receiver admission → UNKNOWN/reconcile_required
  with controlled zero effects; effect-before-result → UNKNOWN with one effect
  and invalid success proof; committed-result → matching SUCCEEDED/one effect.
  Query-first reconciliation, unchanged original deadline, fresh owner/session
  on restart and no second accepted COMMAND remain mandatory. Receiver absence
  alone never authorizes nonexecution, expiry or replay.

These19 cases depend on the matched fixture port. Preserve original fixture
watchdogs/barriers and document their test-only scope; do not extend production
operation, lease or shutdown timeouts to obtain a pass. Retain earlier deadline-
negative/component tests as evidence; no new six-second expiry hold is scheduled.

### Shared combined-case verdict

Before advancing, require original harness and independent strict assessor gates:
correct candidate/image/source bytes, actual network readbacks, complete file/
dispatch/kernel/native/trace populations, valid typed output/no DDS bypass,
qualified publication-age histogram coverage of every counted publication, six
nonnegative balanced accounting equations, no over-budget publication and all
owned-child cleanup. Nonempty publications on both routes and real command
attempts are required so an empty interval cannot pass vacuously.

Use the recent strict progress default: each observed attempt must have matching
closed success/result/effect proof (`command_progress`), no unadmitted/UNKNOWN/
unresolved attempt, and no duplicate handoff/effect. Count skipped offers and
rejected/unknown/missing sensor populations separately. A safe command decline
can satisfy a safety check yet fail this declared strict-progress gate; preserve
both conclusions. Do not silently substitute a permissive safety-only PASS,
authoritative-expiry alternative or an invented continuous2s latency guarantee.
N4 uses its explicit phase-specific outcomes instead of this all-success rule.

## 5. Stop rules, deliverables and acceptance review

- Every future case runs once. First failed declared gate, timeout, hash change or
  cleanup failure stops all later cases/stages. A host outer deadline for existing
  N3/combined cases is nominal duration+240s; this is an orchestration bound, not
  a transport/command budget extension. Inventory the exact existing N4 bounded
  phase deadlines during its port before claiming readiness.
- Evaluate gates before starting the next case. Later cases not started are
  NOT_EXECUTED; any already executed after a missed gate stay explicitly outside
  the intended stop boundary. No warm restart, seed substitution or favorable-run
  selection. Cleanup records and known observer losses cannot be hidden.
- No parallel builds/tests/heavy unrelated analysis during a future capture. Keep
  current rate, queue, clock, crypto, offload, neighbor, TTL and provider settings;
  preserve each fixture's already declared conditions rather than inventing one
  new shared tuned environment. N3/N4 permanent-neighbor fixture scope differs
  from combined-run default dynamic neighbors and remains explicit.
- Produce per-stage verdicts, exact build/settings hashes, raw-file dispositions,
  closed-journal proofs, histogram/reduction denominators and cleanup results.
  Then update the same candidate coverage ledger; do not aggregate different
  binaries into a full-matrix PASS. A safety-affecting runtime change requires a
  new candidate identity and an explicit affected-gate plan, not hidden rebuilding.

A future completion review can close N3/current-build gaps only from qualified,
candidate-labelled evidence under this unchanged contract, or a separately
approved prospective scope change. DDS cold-start failure, DDS N1/N2 age limits,
the DDS N2 capture discrepancy, security/age-origin/observer asymmetry and
unmeasured peaks stay explicit in the comparison. They are not automatically new
experiments or claims of equivalence/superiority. No new DDS case is proposed.

For now the deliverable is this plan and its
[machine-readable proposed case list](evidence/m3-closure-plan-2026-11-09/plan.json).
Readiness is partial, cases executed0 and new experiments0. No threshold waiver,
merge or M4 start follows. The next permitted work remains planning/preparation
within the user's scope; generic continuation does not silently lift the explicit
no-new-experiments constraint.
