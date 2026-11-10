# Complete Python harness lifecycle — offline stabilization

**39 lifecycle tests,4 runtime-import tests and all511 existing tests PASS.**
No N0 rerun, Docker call, live ROS/SRT fixture, native build, tuning or automatic
retry. Other28 campaign cases remain disabled, N0 unqualified, M3 open, PR2 draft,
Intrinsic/M4 untouched. Old freezes, three failed N0 runs and N3 outcomes remain
unchanged. No new campaign freeze or execution grant is created.

## Whole-flow verification

validation/offline_flow.py drives the production Python lifecycle methods together,
not only isolated start/stop callbacks. It executes the actual inherited Driver
robot loop, negative wrong-hash test, all six operator file-RPC requests/responses,
Benchmark link-reset handler, Diagnostic launch/readiness/stop methods and wrapper
main. A profile regression checks that those production methods really execute.
The actual host arm-before-release, observer-finally, lab cleanup and credential
cleanup AST blocks are also exercised against modeled dependencies.

The successful sequence is:

1. Operator startup; robot simulator and expected negative startup.
2. Real robot startup and readiness, warmup pause and clean warmup shutdown.
3. One planned replacement with fresh token/identity/exclusive shutdown trace.
4. Resume/pause controls, observer arm and release before the final finish RPC.
5. Final robot and simulator shutdown/ack, then operator shutdown and cleanup.

All six controls use the actual operator RPC method and actual robot loop/handlers:
start, pause, reset_link, resume, pause, finish. Two ordinary Python test threads
coordinate the modeled executor; every response sequence is checked. Virtual
clocks, temporary procfs and mocked child/reduce/exec boundaries replace ROS,
Linux capability changes and native processes. The wrapper still publishes and
parents validate real readiness-protocol files through the bound identity parser.
Mocked native trace emission models exclusive creation and uses retained trace
structures; no retained record is relabelled a new live result.

The successful output is consumed by the real launch-lifecycle assessor. A full
assessor test additionally exercises modeled observer records and the closed-file
cleanup checks, with combined SENSOR/command validation explicitly outside this
lifecycle model. Another check prevents a failed host result from passing merely
because all children exited cleanly. Per-launch traces, identity/helper provenance,
negative outcome, token/start_ticks/PPid, stage/socket and observer-role checks
remain mandatory.

## Failure paths and hardening

Whole-flow tests inject spawn refusal, nonzero capabilities, unexpected negative
success, trace-path collision, warmup/final shutdown timeout and observer arm/close
failure. They verify first failure retention, no extra startup/replacement retry,
no finish RPC without observer release, final child reaping, modeled owned cleanup
and credential deletion. Failed/incomplete paths cannot pass lifecycle assessment.
Observer-close failure remains failed even after successful cleanup. Existing
5s stop timeout/forced failure is exercised with virtual time, not changed.

Two bookkeeping corrections accompany the model:

- Diagnostic.start closes its log when Popen fails, saves an explicit spawn-phase
  failure with no invented PID/status, and preserves the original exception.
- Diagnostic.cleanup saves the final launch catalog even on cleanup/error paths,
  so observed child return codes do not remain stale. It does not turn missing
  normal shutdown evidence into a passing child outcome.

Readiness, wrapper reduction, per-launch planning, lifecycle/stage/socket assessors,
Benchmark workload, observer policy and native source/build are otherwise unchanged.
The host adapter changes only scenario selection to this candidate. No rate,
queue, clock/crypto configuration, startup/shutdown budget or filter is tuned.

## Evidence and limits

The39 tests comprise26 retained trace/lifecycle regressions and13 whole-flow tests,
including production-method/host-block call verification. Four fresh-interpreter
import tests retain the real runtime precedence/cached-ROS-helper protections.
The existing511-test suite also passes. Logs and compile-only syntax verification
are retained; no Linux capability syscall or actual bridge/observer process runs.

The complete Python control-lifecycle model does not execute Benchmark.operator's
300s SENSOR/command measurement loop, ROS graph discovery, SRT traffic, worker
supervision or kernel stack sampling. RPC scheduling and native endpoints are
modeled; helper provenance roots are rebased only in temporary test outputs from
the host checkout to the target /workspace mount. Observer stacks/owned cleanup
in this model are explicitly synthetic, not proof of kernel permissions or real
Docker-object absence. Existing retained observer tests keep their original scope.
Offline PASS is stronger integration coverage, not live N0 or M3 qualification.

input-hashes.json and public-artifact-hashes.json bind this candidate, test inputs
and logs. postflight.json records unchanged frozen source/inputs/current14/
preserved13/full chain/native87 and historical public/raw archives. Old drivers
cannot silently select this revision. A separately prepared freeze and explicit
execution instruction remain necessary before any live qualification.
