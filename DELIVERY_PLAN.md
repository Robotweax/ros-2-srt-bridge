# Delivery focus — 2026-11-09

M0–M2 are accepted for the recorded Linux amd64/Jazzy simulator baseline. M3 is
the delivery blocker. PR2 remains draft; Intrinsic/M4 is not started. Current
implementation and qualification are described by the latest HANDOFF entries.

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
