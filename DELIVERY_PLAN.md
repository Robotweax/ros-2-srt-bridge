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

The SENSOR contract permits drops under N5 overload; freshness and boundedness
are the acceptance criteria, not lossless delivery. Raw loss percentages alone
must not create another open-ended diagnostic program. Cross-host clock,
hardware/offload and security/resource limits retain their declared scopes;
simulator acceptance is not silently promoted to those environments.

Near-term progress reports should state which gate closed, which blocker remains
and the next concrete change. Test counts and new trace points are supporting
evidence, not the primary measure of delivery progress.
