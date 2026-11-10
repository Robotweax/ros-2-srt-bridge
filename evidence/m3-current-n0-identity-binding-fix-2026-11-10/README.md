# Explicit N0 identity-helper binding — offline verification only

**Implemented;30 targeted tests and all511 existing tests pass offline.**
No N0 rerun, live fixture, tuning, automatic retry or later campaign stage.
Other28 cases remain disabled, N0 unqualified, M3 open, PR2 draft, M4 untouched.
The two frozen preparations and failed attempts are preserved unchanged.

## Corrected binding

launch_readiness.py loads identity from the exact frozen source file
`evidence/m3-current-n0-preparation-2026-11-10/shutdown_observer.py`.
It checks SHA256f4b2d9ed4f31bded2772d61081b7a9de8ac88ebfabc7ef690f24f149515868d3,
compiles those same checked bytes into a private module and binds its identity
function. No unqualified shutdown_observer import, sys.path/sys.modules lookup,
bytecode-cache selection or fallback can substitute a different schema. Missing
or changed intended source fails closed; it does not select the ROS helper.

Every readiness/failure snapshot now records the helper path, SHA, private module
name and required identity fields. Validated exported identity includes that
binding; parent acceptance rejects readiness claiming another helper. Existing
PID/start_ticks/PPid, per-launch token/path/atomic publication, exact capability
snapshot retention, zero-capability/NNP/seccomp and phase rules remain in force.
The bound function returns the required ppid/name alongside pid/start_ticks/state.
No parent field is dropped or inferred from a different snapshot to bypass a gate.

scenario.py and bridge_exec.py are byte-identical to the previous readiness fix.
The host adapter changes only its scenario path to this candidate revision. The
native SDK/ROS builds, capability reduction function, combined workload, observer
policy, clock/rate/queue settings and startup/shutdown budgets are unchanged.
Readiness remains explicitly reduced-wrapper pre-exec evidence, not a successful
exec or application-readiness assertion; existing ROS gates remain mandatory.

## Runtime-import-order regressions

The30 targeted tests include22 launch readiness/snapshot tests and8 binding/
import/integration tests. Fresh offline Python interpreters use the runtime
order: tools, ROS demo scripts, candidate harness, prior evidence helper. The
actual ROS shutdown_observer module is imported and cached before the candidate.
Tests then import the actual parent scenario and wrapper without running main.
Only the scenario's /workspace root is mapped to this checkout for host execution;
ROS-facing dependencies are stubs. All remaining scenario imports execute as
written, so the relevant runtime import precedence is preserved.

Both parent and wrapper pass with the actual ROS helper already cached and with
its identity function poisoned to fail if called. Synthetic procfs data exercise
registration→publication→attestation with ppid/name intact, followed by a nonzero
capability failure whose exact status and bound helper provenance are retained.
The tests assert the selected helper path/hash/private module, not only a mocked
identity shape. Additional tests refuse a missing/changed helper and forged
readiness provenance. The original reduction, Benchmark and Diagnostic ASTs remain
unchanged; the host adapter differs only in the intended scenario selection.

All511 existing tests also pass. Logs are in validation/. Tests use temporary
procfs files, mocked children/reduction/exec and ordinary offline Python test
interpreters. No Docker call, Linux capability syscall, ROS node, bridge/capture/
observer process or N0 workload is started. Compile-only syntax checks pass.

## Evidence and execution boundary

postflight.json records frozen source/inputs/current14/preserved13/full build
chain/native87 and prior raw/public hash verification, including the57 artifacts
from the latest registration failure and64 from the earlier N0 failure. New
input/public hashes bind the candidate and test records; old packages are intact.
No native rebuild, new campaign freeze, authorization file or live output is
created. Existing frozen drivers cannot silently use this candidate revision.
A separately prepared new freeze and explicit authorization are required for
future live qualification. Offline PASS does not establish live import timing,
startup/shutdown success or300s coverage. Prior N0 failures and fresh N3 nine-case
PASS retain their original scope and remain unchanged.
