# M3 acceptance closure plan — 2026-11-09

**Plan prepared; execution is not scheduled or authorized by this document.**
The current no-new-experiments instruction remains in force. The original planning step performed
read-only checks and documentation changes: no tuning, build,
traffic, fixture execution, journal recovery, expiry or replay. M3 remains open,
PR2 draft and Intrinsic/M4 untouched. The existing
[acceptance conclusion](M3_COMPARISON_AND_ACCEPTANCE.md) is unchanged.

The route below keeps the strict N3 source-slot contract. It does not propose a
relaxed threshold or a retry-until-pass program. A future request to execute a
specified stage would need to explicitly change the current no-experiment scope;
this plan does not start that stage automatically.

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
|N3|Five qualified prefix cases; fault subgates and original failure retained|One separately frozen strict9-case candidate cohort, if later authorized; no old-cohort splice|
|Combined SRT N0|Native checks and30s sensor-only baseline are useful but different|One300s combined candidate control|
|N1/N2|Historical3-seed600s series retain their own binary scope|Six600s candidate cases|
|N4|Current component guards plus earlier bounded network/ROS evidence|Port old fixtures to this candidate, then the19 bounded cases below|
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

Offline source preparation is now implemented and427 Python checks pass; see
[evidence and readiness delta](evidence/m3-offline-closure-preparation-2026-11-09/README.md).
This does not authorize execution. Native compilation/link and live validation
remain unperformed; no live dispatcher is wired. All38 cases remain disabled.
The original planning snapshots below retain their original scope.

These are the preparation deliverables and their remaining boundaries:


1. **Strict campaign assessor.** Closed-case assessment and callback stop control
   are implemented with offline negative controls; live dispatcher wiring remains
   pending. Make the case-level and cohort-level verdict use
   the same declared source/capture/clock/journal/cleanup gates before advancing.
   `run_m3.py` exit0 alone is insufficient: earlier harness safety passes allowed
   unresolved commands. Use the existing closed `command_progress` proof and
   SENSOR accounting, with explicit positive/nonempty populations. Preserve inner
   harness status separately. A late audit failure stops the campaign; it cannot
   merely annotate a PASS after later cases have been scheduled.
2. **Matched N4 fixture port.** Source now supports explicit selected
   SDK/worker/ROS paths, child prefix checks and post-build fixture bindings.
   Nonbaseline native selection refuses the currently missing binding before
   lab creation. Native compilation/link and runtime validation remain pending. An old IPC3-linked peer is not current-build evidence
   when run beside an IPC4 worker. Build only the standalone peer into a new
   isolated fixture prefix against the fixed SDK; do not overwrite old
   fixtures or rebuild production libraries. The source port is offline-tested; no fixture build was performed.
3. **Offline negative controls.** Before a future campaign, the orchestration
   must stop on a source skip, missing histogram/footer, wrong image/build,
   unresolved result, incomplete capture, changed epoch or failed cleanup. Mocked
   stage transitions must prove that later slots remain unexecuted after failure.
   Freeze these harness changes and their checks before live execution.
4. **Fresh evidence identity.** Freeze candidate manifest, provider/image hashes,
   driver/assessor bytes, settings and full case list; allocate new output paths,
   namespaces and journals. Fresh numeric request IDs do not reopen historical
   identities. Verify hashes before/after each case; changing the native candidate
   pauses the plan for an impact review rather than silently continuing.

Completed in this planning step: the current zero-skip guard was applied read-only
to all9 retained N3 result files after checking their original hashes. It correctly
rejects the sixth case; the final3 keep `outside_stop_boundary`, even though their
individual window checks pass. The failed cohort is not repaired. Candidate/hash
checks and runner readiness findings are in
[readiness.json](evidence/m3-closure-plan-2026-11-09/readiness.json).
N4 porting and the all-stage strict orchestrator are explicitly **not ready**.

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
