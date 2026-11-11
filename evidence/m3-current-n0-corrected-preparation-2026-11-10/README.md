# Corrected-readiness N0 freeze — preparation only

**Execution disabled. Zero live runs; no authorization file.**

Prepare exactly N0-combined-1701, campaign ordinal10, seed1701,300s combined
SENSOR/COMMAND coverage on the same frozen socket-disposition SDK/ROS build.
This new freeze selects the offline-verified launch-specific readiness correction;
it does not retry or relabel the historical N0 startup failure. All28 other
unexecuted N4/N1/N2/N5 cases stay disabled and completed N3 is not reexecuted.
No tuning, native rebuild, automatic retry, merge or M3 acceptance. PR2 draft,
M3 open and Intrinsic/M4 untouched.

## Bound harness and case

The local workload.py is byte-identical to the corrected harness adapter in
../m3-current-n0-readiness-fix-2026-11-10/. It selects that package's scenario.py,
bridge_exec.py and launch_readiness.py, all bound as freeze inputs. Per-launch
negative/positive tokens, atomic readiness paths and PID/start_ticks/parent
binding prevent an earlier wrong-hash marker from authorizing the real child's
capability check. Failures retain the exact evaluated status, identity brackets,
expected identity, launch/phase and read errors. Pre-exec wrapper readiness is
explicitly distinct from application readiness; existing ROS readiness remains.

The native matched14/preserved13/full earlier chain/provider and87native inputs
are unchanged. Pinned amd64 target/native ARM64 observer images, IPC4, source
rates200HzIMU/50Hzjoints, command slots every2s, dynamic-neighbor N0 profile,
clock/queue/crypto settings and original wait/observer budgets are retained.
No fault selector, outage or competing load is introduced. Seed1701 identifies
the predeclared independent start, not random-loss coverage.

Strict combined SENSOR/command/journal/capture/provider checks, both-role stages/
socket dispositions, native observer lifecycle and complete cleanup/integrity
remain mandatory. The observer is armed by the existing end-of-measurement
release gate before normal shutdown. Gates are not waived to predict a PASS.
This combined path with the readiness correction has offline validation only;
no live startup/shutdown/300s qualification is asserted.

## Freeze and execution boundary

freeze.json binds the exact one-case plan, all28 disabled IDs, completed N3 IDs,
corrected harness revision/public manifest, frozen source/input/runtime/build
chain, capture helpers, prior public/raw evidence, a new read-only observer bundle,
fresh prefix and fresh output path. The prior preparation/failure/diagnosis/fix
packages stay immutable. The old driver cannot select this freeze or adapter.

Scope is current-build-N0-combined-launch-readiness-v2-socket-disposition. A future
separate exact grant must bind this freeze SHA, one ordered N0 ID, all28 disabled
IDs, launch-specific-v1 harness revision, historical failure preservation,
completed-N3 exclusion and no tuning/automatic retries. No such grant is created
by preparation. Existing output refuses resume/retry. First failed startup,
measurement, evidence, shutdown, cleanup or integrity gate stops the sequence;
there is no later-stage dispatch or automatic action.

## Readiness checks and limits

Nine new preparation tests and21 corrected-readiness tests pass offline. The
existing511-test suite is retained from the unchanged-source fix verification;
its log is hash-bound and not relabelled a new live result. New tests use pure/
mocked callbacks and temporary procfs/metadata; no process fixture or Docker
container runs. Syntax and source/input/build/prior-evidence checks pass.

Preparation uses read-only Docker version/info/image/list metadata to check the
same runtime/pinned architectures and absence of live or owned objects. It does
not create/start containers, networks, volumes, capture, bridges, observers or a
readiness experiment. Only a local read-only observer bundle and disabled files
are produced. No native build, provider change or tuning is performed.

readiness.json/postflight.json describe preparation only. N0 remains unqualified
until a separately authorized future case passes all gates. The original startup
failure and missing capability values remain preserved; fresh N3 stays9/9 and the
historical N3 failure remains separate. Physical sensor age, diagnostic overhead,
latest-only availability and other documented M3 acceptance limitations persist.
