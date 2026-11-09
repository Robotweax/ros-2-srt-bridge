# Delivery focus — 2026-11-09

The authorized [frozen N3 cohort](evidence/m3-n3-frozen-cohort-2026-11-09/README.md)
finished with8 strict passes and a final-case shutdown FAIL: the operator bridge
exceeded its5s SIGINT wait and required forced kill. No retry or tuning; all29
remaining campaign cases stay disabled. M3 remains open and PR2 stays draft.


M0–M2 are accepted for the recorded Linux amd64/Jazzy simulator baseline. M3 is
the delivery blocker. PR2 remains draft; Intrinsic/M4 is not started. Current
implementation and qualification are described by the latest HANDOFF entries.
The current comparison and acceptance decision is in
`M3_COMPARISON_AND_ACCEPTANCE.md`: reporting complete, M3 completion not accepted
under the unchanged plan. No new experiment or waiver is queued.
`M3_CLOSURE_PLAN.md` now gives the concrete N3/current-build closure sequence;
the authorized N3-only execution is now recorded as8 strict passes/final shutdown FAIL,
with every later stage disabled. Next work is retained-evidence teardown diagnosis,
not another experiment or a shutdown-budget increase.

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
