# Campaign per-thread assessment — wired, offline only

**25 integration tests, 42 assessor regressions and 511 existing tests PASS.**
The prospective campaign harness now connects the calibrated collector, explicit
activation, closed-file exec/launch checks and per-thread lifecycle assessor.
No tuning, retries, Docker calls, live procfs reads, builds or live runs occurred.
No freeze, native bundle directory or execution grant was created. All 38 campaign
IDs and every stage are disabled. N1/2903's original FAIL and the stopped cohort
1 PASS / 1 FAIL / 7 NOT EXECUTED remain unchanged. M3 open, PR2 draft, M4 untouched.

## Connected campaign path

`run.py` loads the prospective driver through `campaign_binding.py`. That private
source graph binds local modules by `bindings.json` hashes and pins the exact
calibrated collector, metadata assessor and lifecycle adapter. Generic cached
`cases`, `sidecar`, `lifecycle`, `task_assessment`, launch and socket/profile gate
modules cannot replace these implementations. No generic cache is rewritten.
The reviewed candidate files and collector are byte-identical to the native
post-SIGINT calibration on freeze8acc653d87ad; no assessment rule is loosened.

The prospective workload references this package's stabilized scenario and
sidecar. The sidecar command explicitly forwards `--task-visibility` to the exact
calibrated native entry. The entry checks `collector-binding.json`, collector
SHA and activation before exec. Host arming also requires matching activation
proof. `observer_bundle.sources()` describes all six required native files,
including the activation binding; it creates nothing. Its binding includes the
assessment hashes and complete module-manifest hash. The prospective driver
rejects old freezes without this new binding before querying any runtime.

The campaign assessor uses the exact candidate `coverage`, followed by the new
`observer_gate`: launch-bound root PID/start_ticks, ready-before-SIGINT, matching
observer PID, identical bootstrap/final exec exports, exact collector SHA and
flag, profile source hash, role permissions, boot and zero clock offsets. Task
absence stays separate from readable stack and worker-process exit proof. The
candidate's post-SIGINT/pre-reap, prior-cache, identity, raw-error, join/root-reap
and forced-kill coverage requirements remain intact. Legacy observer records
are refused rather than upgraded or silently handled by an older assessor.

The same real launch/readiness/socket/stage, combined SENSOR/command/capture,
original profile/kernel-readback and cleanup gates still run. Launch, stage,
socket, profile and stabilized scenario helpers are byte-identical to the old
campaign harness. Observer permissions, isolation, sample/read/history limits,
original five-second child wait, matched SDK/ROS/provider builds and transport/
workload settings are unchanged. The collector remains default-off globally;
only the prospective sidecar invocation explicitly requests the calibrated mode.

## Execution interlocks

Driver main/dispatch, workload main and sidecar arm reject execution before
runtime calls or file creation. Every grant is rejected by `cases.authorize`;
`allowed` is false, enabled IDs empty, disabled IDs all 38. The old nine profiles
remain an assessment grammar only, not a selected future cohort or rerun plan.
`case-plan.json` records every stage false. Frozen preparations, observers,
assessors, bundles, historical results and old execution grants are untouched.
A separately authorized prospective preparation must select scope, review the
execution interlocks and bind all integration bytes into a new freeze before
any live activity; this package supplies no execution authority.

## Offline verification and limits

The complete modeled assessment pipeline passes with the real combined SENSOR,
command, capture, profile/readback and cleanup implementations. The test overlay
copies retained passing workload evidence and journals into a temporary directory,
constructs launch catalogs using the existing lifecycle fixture, and retimes a
copy of the retained calibration to that modeled launch. It never changes the
retained capture or claims a new real campaign PASS. Missing/foreign launch,
trace/socket proof, metadata, activation, boot/clock/profile, capture/command/
SENSOR evidence, credential cleanup and old freeze/grant failures are exercised.

The actual sidecar arm body runs only under a modeled Docker callback in a test,
with the first unconditional production guard removed from its AST in memory;
production bytes stay disabled. Command isolation/activation, private import graph,
fresh interpreter host order, candidate-byte identity and disabled entrypoints
are checked. No native process, signal, procfs collection or container is used.
Two initial overlay-model issues (leftover old launch trace files and a list-valued
type-error field) are retained in logs and corrected offline. Existing SQLite
read-helper ResourceWarnings remain visible in the integration log; tests pass.

The exact bound lifecycle also passes the retained native post-SIGINT capture
without retiming: three post-signal samples, one observed enumeration absence,
zero confirmed task exits. Separately, the original frozen gate still reproduces
N1/2903's `live target kernel stack unavailable`; the new adapter refuses its
missing schema1 metadata. Neither historical passing nor failing captures get
new qualification credit.

`verify.py` audits frozen source/full matched build/native87 inputs, all earlier
public/raw indexes, both calibration preparations/executions, original verdict
hashes, disabled states and unchanged helper bytes using filesystem reads only.
The seven later case directories remain absent. Native exact mid-read ENOENT,
unseen reuse, integrated SDK/ROS/SRT workload and observer overhead remain
unqualified; this offline wiring does not close those gaps or accept M3.

```sh
python3 -m unittest discover -s evidence/m3-campaign-task-assessment-integration-2026-11-10/validation -p 'test_*.py' -v
python3 evidence/m3-campaign-task-assessment-integration-2026-11-10/verify.py
```
