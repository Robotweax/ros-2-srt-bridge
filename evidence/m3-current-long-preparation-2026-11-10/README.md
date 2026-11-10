# Remaining current-build N1/N2/N5 — nine cases prepared, not run

**Execution disabled; zero live cases and no authorization file.** Reuse the
frozen socket-disposition SDK/ROS/provider build with the stabilized startup,
warmup, per-launch readiness/identity/traces, restart, shutdown and native observer
lifecycle that passed the current-build N0 case. No tuning, automatic retries,
production build, experiment, merge or M3 acceptance. All29 completed N0/N3/N4
case IDs are excluded and disabled from this dispatcher. M3 open/PR2 draft/M4
untouched; all historical failures remain preserved.

## Exact order

| Original rows | Profile | Seeds, in order | Source duration per case |
|---|---|---|---:|
|30–32|N1|1701,2903,4211|600s|
|33–35|N2|1701,2903,4211|600s|
|36–38|N5|1701,2903,4211|300s|

The exact original plan IDs/settings are recorded in case-plan.json. Total
nominal source time4500s (75min), excluding startup, warmup, drain, cleanup and
all other overhead; not an elapsed-time estimate or schedule. No smoke, subset,
N0/N3/N4 rerun, custom seed/duration, resume or batch fallback is allowed.

settings.json records the unchanged network profiles: N1 delay20ms/jitter5ms/
loss1%, N2 delay60ms/jitter15ms/loss3%,256-packet netem queues; N5 roots512kbit/s,
4096-byte bursts,32768-byte TBF limit and16-packet children. Role seeds retain
operator=base+1,robot=base. N5 keeps the existing128Kbit/s UDP competitor with
1024-byte payload and source-duration+60s process lifetime; it must remain alive
and pass original target/load checks. Dynamic neighbors are retained. No ARP,
qdisc observer, fault injection, capture-drain intervention or queue/rate tuning.

Workload remains200Hz IMU/50Hz joints, original2s command offer slots,5s command
budgets,250ms SENSOR age budget and200ms clock interval. The original immediate
full-snapshot PCAP buffers/rotation, native monotonic capture, command/provider/
SENSOR-provider/start/sender diagnostics and5s child waits are retained. Trace
and capture exhaustion/drop/retention gates remain failures, not permission to
expand budgets; live600s capacity/scheduling is not claimed by preparation.

## Harness and assessment

The workload/scenario/wrapper/lifecycle components are frozen into this package.
Scenario and bridge wrapper bytes match the stabilized N0 scenario exactly.
Host workload changes only the allowed profile/seed/duration scope and the path
to that identical scenario. Readiness explicitly binds the intended identity
helper; unique launch token/PID/start_ticks/PPid, expected negative startup,
warmup and final trace lifetimes, stage/socket dispositions and final-operator
observer selection remain mandatory. Historical n0 marker/module names are
unchanged internal lifecycle conventions, not another N0 workload.

Each case has fresh output/journals/NetworkLab and a unique observer prefix; the
read-only native observer bundle/filter/images/budgets and bridge capability
reduction are unchanged. Observer is armed before the original child wait.
No host namespace/debugger/global permission fallback is introduced.

Strict assessment reuses all existing combined capture/frame/clock/cadence/
SENSOR accounting/publication-age/durable command-progress/shutdown gates. Safe
uncertainty does not count as strict progress, authorize replay, force expiry or
reinterpret NOT_FOUND. The additional closed-file profile gate requires exact
original install commands and N1/N2 kernel delay/jitter/loss/queue/seed or N5
root/rate/burst/child/queue/seed readback. No existing gate is relaxed.

Every case must finish strict assessment, recorded cleanup, credential deletion,
independent owned container/network/observer/volume absence and frozen source/
input/build/evidence verification before the next case starts. Assessment errors
still trigger postflight. Unexpected host exceptions invoke bounded cleanup of
only recorded owned objects; case stays failed. First failure leaves later rows
not_executed. No automatic retry, new freeze or stage advancement occurs.

run.py requires a separate exact future grant binding this freeze, all9 ordered
IDs,29 disabled/completed exclusions, identity/lifecycle helper SHAs, historical
failure preservation and no tuning/no retries/first-failure stop. Old N0/N3/N4
execution grants are refused. Output must be fresh. No grant is created here.

## Offline verification and limitations

21 preparation tests,39 lifecycle tests,4 fresh-interpreter identity/import tests
and511 existing tests PASS. New coverage exercises real parser refusal before
mutation, exact9 invocation mapping/order, old/changed grant refusal, all9 failure
positions, full mocked dispatch/postflight ordering, unique prefixes, no output
reuse, credential/owned-object refusal and exception cleanup. Profile tests use
constructed kernel metadata; changed settings and missing installs are refused.
Exact byte comparisons limit scope changes and preserve calibrated components.

The39 lifecycle models retain actual production Python startup/negative/warmup/
restart/shutdown methods, virtual clocks/procfs, mocked child/reduce/exec/observer
and host cleanup blocks. Two successful full-assessor models explicitly mock the
combined and profile gates outside lifecycle scope; profile checking has its
separate tests. No ROS graph, SRT traffic, real syscall permissions,600s loop,
loaded competitor or native observer is exercised offline.

Read-only preflight binds source/inputs/current14/preserved13/full SDK/ROS/provider
chain/native87, prior native fixture/build artifacts and all earlier public/raw
archives, including the fresh N4 1140-file archive. Prior current-build N0 PASS,
fresh N3 9/9 and bounded N4 19/19 retain their scope; no hardware/physical sensor
age, independent overhead/security/resource equivalence or full M3 acceptance.
The copied runtime manifest changes location only; its bytes/build SHA stay fixed.

freeze.json binds scripts/assessors/settings/case order, matched builds, observer
bundle, prior evidence, runtime/images and fresh absent output/prefix. Runtime
checks inspect Docker metadata only; no containers, network, worker, ROS node,
fixture or build are started. readiness/postflight describe preparation only;
public-artifact-hashes.json binds the complete package. Actual runtime safety,
progress, capture/freshness and lifecycle gates still require separately
authorized execution. No later stage or Intrinsic/M4 work is queued.

Preparation lookup correction: the initial read-only check referenced nonexistent
N3 cohort.json and stopped before runtime inspection, freeze/bundle/output
creation or any live operation. It now checks the published gate-report.json
and exact9/9 status; the added regression reads the actual prerequisite reports.
validation/preparation-correction.json preserves this preparation-only failure.
