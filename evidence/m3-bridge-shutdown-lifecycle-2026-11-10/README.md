# Worker identity lifecycle and one N0 diagnostic — 2026-11-10

**Worker lifecycle gate PASS; overall diagnostic FAIL at robot shutdown stages.**
All484 Python tests pass, including6 new lifecycle controls. Exactly one newly
frozen N0/seed1701/10s attempt ran and stopped at the first failed gate. No tuning,
policy/privilege/sample-rate/wait change, two-loss-4211, commands, expiry/replay,
second attempt or other campaign stage. All29 cases disabled; M3 open/PR2 draft/
M4 untouched. Original N3 stays8 PASS/1 FAIL/unknown hang cause.

## Distinguishing worker termination from PID reuse

An evidence-local copy of the read-only observer now reports explicit stat
results: matching PID/start_ticks, process_missing only for ENOENT, pid_reused
for a different start_ticks, identity_unavailable for permission/malformed/other
errors. Each result carries a check timestamp; matching records retain observed
identity, parent and name. No native runtime/SRT/ROS binary or policy is changed.
Sampling periods, process/thread/read/time budgets and same-UID inspection remain
unchanged. The original collector and all prior captures/freezes remain immutable.

A missing worker is accepted only if exactly that PID/start_ticks was sampled
before SIGINT as the known journal worker with the bridge as direct parent, and
unique ordered same-thread worker_join_begin/end markers precede the ENOENT check.
Stage identity/sequence/drops and check/sample timestamps must match. PID reuse,
read errors, unknown/wrong/premature disappearance, ambiguous old statuses,
identity changes during collection, missing join proof and root disappearance
before supervisor reap still fail. Reuse/error rows are checked after root reap
too. Confirmed termination does not assert worker exit status or its death cause:
worker_join_end records join completion, not the join return value. No crash or
original-hang causality is inferred.

Six regression tests cover actual temporary procfs-stat absence/matching/reuse,
permission/malformed failures, confirmed worker exit, post-reap reuse/read errors,
missing/premature/wrong-worker/root/stage-drop cases and mid-sample/legacy ambiguity.
Old ambiguous FAIL records cannot satisfy this new proof and are not relabeled.
The exact calibrated native image/permissions/filter and matched13 build remain;
only diagnostic Python collection/assessment and required frozen paths change.

## Single execution and failure

New freeze178e40eebcab and separate exact user authorization bind the attempt.
Capability/configuration/native entry/exec/ready checks pass before SIGINT. The
operator observer records3 samples,26 successful kernel-stack reads/zero denied,
complete all_owned_processes_gone footer and no budget exhaustion. Within the
supervisor wait:2 samples/25 nonempty stacks, including1 contained post-signal
sample. Registered workerPID158/start_ticks1123 has explicit ENOENT after
worker_join_end31,113,468,430ns. The lifecycle assessor confirms it; no PID reuse
or unavailable identity/stack error occurs. This validates this observed lifecycle,
not exhaustive future races or user-space frames under amd64 emulation.

The next unchanged full-stage check fails: robot trace lacks socket_close_begin
and socket_close_end. Operator51/robot39 records have zero dropped_before and end
at main_context_shutdown_end. Missing required markers are retained as FAIL;
they alone do not prove a socket leak or hang. No new stage rule, instrumentation,
source patch, permission fallback or attempt followed the failure.

Underlying SENSOR host adapter PASS remains distinct from final diagnostic FAIL/
driver exit1. Later diagnostic SENSOR/capture assessment is not reached. Operator
exits0/unforced220.430292ms, robot334.928375ms, source167.202875ms, within original
5s waits. Both bridge exits are healthy; original faulted shutdown failure was
not reproduced or attributed. No original cohort splice or N3/M3 acceptance.

## Integrity and cleanup

All two lab containers plus observer, network and output volume removed/absent,
credential deleted, all supervised children/observer reaped without force. Source/
input/helper freeze,13 matched SDK/ROS entries/preserved build chain and all prior
raw indexes, including116 artifacts from the previous lifecycle-gate FAIL, match
postflight. No SDK/ROS/native rebuild or heavy checks overlapped capture.116 new
closed local artifacts are hash-indexed; exact observer/stage records are public.

PLAN/source/test logs/freeze/authorization/preflight, both result statuses, gate
report and postflight retain the prospective contract and outcome. readiness.json
is its pre-run snapshot; the separately authorized output now exists and cannot
be reused. Next prerequisite is retained-evidence review of robot socket-close
marker coverage before proposing any stage change or live attempt. Nothing
further is queued and no failed gate is waived.
