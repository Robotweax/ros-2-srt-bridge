# Explicit-identity N0 execution — 2026-11-10

**FAIL during warmup reset_link, before the300s measurement. One case, no retry.**
User authorized exactly N0-combined-1701/300s on freeze66f21a2916b9 with explicitly
bound identity helper, stop first failed gate/no tuning/automatic retries, other
stages disabled. The unchanged driver ran once and exited1. All28 other cases
stay disabled; M3 open, PR2 draft and M4 untouched. No source/helper/gate/native
build, capability policy or tuning change occurred. Earlier failures preserved.

## Progress and first failure

Explicit identity binding passes the prior registration point. Four distinct
pre-exec records are retained: operator bridge, wrong-hash robot negative test,
initial robot bridge and the planned warmup replacement robot bridge. All have
unique tokens, pid/start_ticks/ppid/name, the exact bound helper SHA/private module,
zero capability sets and NNP1. Operator and replacement robot parent identity
exports also retain the bound helper and zero capabilities. This is scoped live
startup evidence, not a full N0 or production capability qualification.

The negative type-hash test passes. The initial robot bridge participates in
warmup, then exits0/unforced after the existing reset_link request. Its child
report and51 stage records are retained for PID141. That planned reset is part of
the frozen combined workload's warmup exclusion, not a retry after a failed case.
The replacement robot PID177 then exits1. Its complete log is:

    bridge startup failed: cannot create shutdown trace

Robot traceback ends in the existing readiness wait with `bridge exited 1`.
The last control request is sequence3/action reset_link; measurement-start and
full results are absent. No further reset, second case or retry follows failure.

Retained source explains the trace-path conflict: Benchmark.start_bridge supplies
robot-shutdown-stages.jsonl for every robot bridge launch. reset_link stops the
warmup bridge then starts another. ShutdownTrace opens the supplied path with
O_CREAT|O_EXCL, so it requires a fresh file. The retained file belongs to PID141;
replacement PID177 cannot create the same role-level file. Exact open errno was
not logged, so no syscall/errno trace is invented. No new experiment was used to
inspect this source/artifact consistency, and no path/gate fix was made here.

## No measurement or shutdown acceptance

No300s measurement-start, operator result, robot-final, normal end-of-measurement
release, observer readiness or strict assessment. No observer is started/armed.
The first warmup robot's clean child exit is a partial observation only; final
case lifecycle/socket/capture/command qualification was not reached.

Secondary errors retain unavailable endpoint_measurements for capture reduction
and missing/duplicate final command/provider statuses. They remain failures,
without waiver or inferred qualified populations. Partial operator/robot stage
and journal/capture files are preserved as evidence, not complete coverage.

Normal/emergency owned cleanup records are retained. Independent final Docker
metadata confirms both lab containers, network, observer and observer volume
absent and credential deleted. This is object absence after failure, not a full
clean child-exit/shutdown qualification. No later stage is enabled.

## Provenance and next boundary

Frozen source/inputs/explicit harness/current14/preserved13/full build chain and
native87 inputs verify unchanged. Preparation public hashes and all retained
raw/public indexes verify, including both previous N0 failures and original/new
N3 outcomes. New closed raw archive:74files/703,520bytes, hash-indexed. Public
copies include exact grant/preflight/driver/cohort, four launch records, parent
identities, robot child/stages/exit log, failure traceback and cleanup report.

No tests or native builds ran during this case. Prior10/30/511 offline outcomes
retain their preparation scope; they do not establish this warmup/restart trace
integration. N0 remains unqualified. A future trace-lifecycle correction would
need distinct launch paths and matching lifecycle assessment; no correction,
new freeze or extra live experiment is authorized or performed by this result.
All28 other stages disabled, M3 open/PR2 draft/M4 untouched.
