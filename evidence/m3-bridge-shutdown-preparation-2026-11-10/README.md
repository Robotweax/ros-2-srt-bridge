# Bridge shutdown diagnostic preparation — 2026-11-10

**Offline prepared; live execution disabled. No diagnostic run occurred.**
The user requested preparation only. No authorization file, Docker object,
network change, bridge/observer process or capture was created or started.
All 29 remaining campaign cases stay disabled; two-loss-4211 remains excluded.
M3 remains open, PR2 draft, M4 untouched.

[PLAN.md](PLAN.md) fixes one future healthy N0 SENSOR session: seed1701,10s,
original rates/clock/queues/crypto, zero selected losses and no commands. Existing
shutdown stages are enabled on both bridges. The calibrated native ARM64 sidecar
observes only operator bridge PID/start_ticks and descendants, armed before the
existing release/SIGINT fence; the original5s child wait is unchanged. No tuning,
shutdown hold, failure injection, original-case retry or campaign dispatcher.

The exact [calibrated observer](../m3-observer-bootstrap-calibration-2026-11-10/README.md)
image/profile/helper are reused. SYS_ADMIN belongs only to the network-none,
NNP/read-only/native-filter sidecar, which joins the owned operator PID namespace
and sees a minimal RO helper bundle/fresh output volume. No host namespace,
workspace/credential mount or SYS_PTRACE/GDB. Bridge wrappers drop all capability
sets including bounding and attest NNP/Seccomp before exec; workers inherit that
reduction. Lab qdisc/capture tools retain their existing permissions. No broader
observer permission or production tuning is introduced.

This bridge wrapper and integration are offline validated, not live calibrated.
The future run must pass capability, credential/journal/trace-path access and
session/SENSOR readiness gates without relaxing permissions on failure. A healthy
baseline may not reproduce the older faulted shutdown hang. ARM64 kernel stacks
under amd64 emulation do not resolve application user frames or establish cause.

run.py requires a separately supplied authorization record matching the exact
freeze SHA and single scope. No record is included. Missing/wrong/broader grants,
changed source/build/runtime/profile, other seed/duration/loss, existing output
or unrelated running containers fail before lab creation. The one-shot driver
cannot resume the campaign and refuses its existing output on subsequent use.

workload.py is an evidence-local N0-only copy of the existing SENSOR adapter;
selected-loss branches are removed. scenario.py preserves the original workload
and stop helper, replacing only bridge launch with explicit capability reduction.
sidecar.py records OCI/entry/exec/ready/clock/identity proof before release and
exports closed stacks before lab namespace removal, including failed cleanup.
assess.py preserves abnormal child exits and partial stages as FAIL, reuses the
existing healthy-stage/SENSOR/capture gates, and differentiates fast clean exit
from forced shutdown with inadequate post-signal observation. No shutdown timing
is stretched to obtain samples. Prior failed evidence remains immutable.

475 Python tests pass, including seven new controls for exact authorization,
scope rejection, no-authorization refusal before Docker, capability-drop order/
errno, failed observer cleanup/export, fast clean exit and hung-child observation.
ROS imports and actual Linux capability changes are not executed by these tests.
The wrapper is not a native-build change; all13 matched SDK/ROS entries and the
preserved build chain match. Old N3/calibration/observer evidence indexes verify.

prepare.py only reads provenance and creates a disabled freeze plus a read-only
five-file observer helper bundle locally. readiness.json states zero live runs
and marks bridge integration unvalidated. The first live attempt remains a
separate action; no automatic next run follows this preparation.
