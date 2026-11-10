# Per-launch N0 shutdown tracing and lifecycle assessment — offline only

**Implemented;26 lifecycle/trace tests,4 runtime-import tests and all511 existing
tests pass offline. No N0 rerun, tuning, automatic retry or later stage.**

This separate candidate preserves the frozen preparations and all failed runs.
No new campaign freeze, execution grant or live output is created. Other28 stages
remain disabled; N0 unqualified, M3 open, PR2 draft and M4 untouched.

## Per-launch records and traces

Diagnostic.start derives a unique shutdown trace filename from the same role,
launch name and random token used for readiness. Each positive bridge gets its
own .shutdown.jsonl alongside its readiness record. The warmup file is never
removed, truncated or reassigned. The native writer retains O_CREAT|O_EXCL and
its256-record bound. The expected wrong-hash negative test keeps its original
startup behavior and does not require a successful shutdown trace.

A per-role launch catalog records context/token, registered PID/start_ticks/PPid,
purpose (negative_type_hash, warmup or measurement), readiness/identity/trace
paths, attestation and return code. The declared topology is unchanged: one
operator measurement bridge; robot negative test, warmup bridge and measurement
replacement. Unexpected positive launches are refused. The existing reset_link
is the declared warmup transition, not a failed-case retry.

Every positive launch keeps its own attested identity file. The role-level
compatibility identity is still written for the unchanged native sidecar, but
assessment requires it to equal the final measurement launch. Child outcomes now
retain launch token, start_ticks, purpose and exact trace/identity paths. Early
exits are retained as failures rather than disappearing from the child report;
already-recorded outcomes are not duplicated. The original stop implementation
still owns SIGINT, its5s wait and forced-kill failure behavior.

## Assessment

launch_assessment.py requires the exact ordered catalog, unique tokens, expected
negative outcome/type-hash proof, complete positive readiness and explicit helper
provenance. Positive outcomes are looked up by token and full launch identity,
not by the first matching child. Both warmup and final robot launches must pass.
Missing/extra/duplicate/reordered launches or child outcomes fail closed.

Each positive trace independently passes the byte-identical calibrated stage and
socket gates: required points, sequence/PID/thread/drop checks, slot dispositions
and actual close results. Trace timestamps must fall after that launch's checked
pre-exec snapshot and before child reap; shutdown must follow its SIGINT bracket.
The warmup must finish before the final robot launch starts. This prevents reuse
of an earlier trace even when a PID is reused. Reused/foreign/legacy role paths,
missing or unlisted trace files and mixed lifecycle identities are refused.

assess.py uses the final operator's child/identity/trace for the existing native
observer readiness, PID/start_ticks, stack/worker-lifecycle checks. Combined
SENSOR/command/journal/capture/provider and cleanup checks remain in place. The
observer still covers only the final operator shutdown; no robot/warmup stack
coverage is claimed. No stage/socket/observer/age/command gate or timeout is waived.

## Offline verification

26 new tests use synthetic catalogs/procfs/children and retained closed stage
fixtures. Mocked Popen models exclusive file creation, proving that warmup/final
paths differ and the warmup file survives replacement. Tests cover expected
negative startup, ordered catalogs, reordered child reports, token/PID/start_ticks
binding, reused PID with stale trace, missing warmup/final traces/outcomes,
early/forced/nonzero exits, compatibility identity mismatch, negative outcome
mismatch, unlisted/legacy paths and unchanged socket-close failures. Parent
attestation writes both unique and current compatibility identities.

A full assessment test uses retained final-operator observer evidence plus mocked
combined/cleanup callbacks to exercise final-launch selection and warmup checks.
Retained stage events are test inputs only; synthetic robot timelines are offset
to keep fixture launches disjoint. No new live qualification credit is inferred.

Four fresh Python-interpreter tests import the actual new parent/wrapper with
runtime order and the ROS helper cached first, including poisoned-cache variants.
They reuse the prior import regression driver; only the candidate path changes.
All511 existing tests also pass. Syntax checks pass. No Docker call, Linux
capability syscall, ROS node, bridge/capture/observer or N0 workload starts.
Ordinary offline Python test interpreters and temporary files only.

launch_readiness.py and bridge_exec.py are byte-identical to the explicit-identity
fix. The full Benchmark workload and native reduce function remain unchanged.
Calibrated stage_gate.py/socket_gate.py/lifecycle.py are byte-identical to the
frozen originals. Host workload.py changes only scenario selection. No native
source/build, source rate, queue/clock/crypto setting, wait, observer policy or
sampling budget changes.

## Integrity and future boundary

input-hashes.json/public-artifact-hashes.json bind the candidate and test inputs;
postflight.json records unchanged frozen source/inputs/current14/preserved13/full
build chain/native87 and retained public/raw evidence, including all three failed
N0 runs and prior N3 outcomes. Old drivers remain bound to old code and cannot
silently select this candidate. A separately prepared new freeze and explicit
authorization are required for live qualification. Offline PASS does not establish
successful300s measurement, live trace/observer timing or full M3 acceptance.
