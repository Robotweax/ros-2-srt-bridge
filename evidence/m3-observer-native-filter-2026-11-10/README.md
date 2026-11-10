# Native observer filtering and readiness — 2026-11-10

**FAIL at OCI runtime startup; blocked-thread calibration was not launched.**
One predeclared native observer readiness check failed before Python entry. The
first failed gate stopped execution. No blocked fixture, bridge/SENSOR case,
two-loss-4211 retry, tuning, expiry/replay or remaining campaign stage ran.
All 29 remaining cases stay disabled; M3 remains open, PR2 draft, M4 untouched.

The new path requires the observer image to match the ARM64 Docker daemon and
uses Docker/libseccomp's named-syscall default-deny profile. It avoids raw native
x86 syscall numbers and Python preexec_fn. The unchanged amd64 target image,
original blocked fixture, 3s hold/5s child wait and all 13 matched SDK/ROS entries
remain frozen. Native observer image resolution is pinned by digest/platform.
Docker accepts [named syscall profiles](https://docs.docker.com/engine/security/seccomp/)
and compiles them for the selected native architecture. This design has not
passed live runtime compatibility or stack-access calibration.

The observer container drops all capabilities except SYS_ADMIN, uses NNP,
read-only root and minimal helper bundle, a fresh output volume, no network and
a custom filter denying namespace/mount, ptrace/process-memory, credential,
network, kernel administration and child creation calls. Planned target and
supervisor drop all capability sets including bounding, with Docker default
seccomp. The sidecar would join only their private PID namespace. Neither target
nor sidecar execution was reached; configured isolation is not per-process
runtime attestation. No privileged/unconfined mode, host namespace/socket,
global sysctl or permission fallback was used.

The readiness command returned exit 1. Retained stderr explicitly reports:
`reopen exec fifo: get safe /proc/thread-self/fd handle: fstatfs fsmount:fscontext:proc: operation not permitted`.
Docker State.Error also retains the associated OCI/network-namespace startup
failure. The frozen allowlist omits fstatfs. This identifies a runtime-bootstrap
compatibility gap before the Python launcher; it does not prove that adding one
syscall alone would suffice, or identify the old opaque preexec exception.
There are no entry, preexec verification, ready or stack records. No profile
adjustment, second readiness check or target attempt followed.

The launcher now records setup/exec stage, exception type, errno, message and
traceback to JSONL and stderr after Python entry. Docker command stderr,
State.Error, logs and exit codes cover failures before Python can start. Two new
offline controls demonstrate wrong-architecture rejection and preservation of
ENOENT from os.execv. Four other controls check architecture matching, denied
operations and exact capability/NNP/seccomp expectations. All 467 Python tests
passed before freeze; no tests or build ran concurrently with readiness.

The sole readiness container and output volume were removed and absence checked.
Prospective source/input freeze, 13 matched binaries and preserved build chain
match postflight. All 913 original N3 raw files, 219 earlier calibration files
and the prior permission-attempt records still match their retained indexes.
No SDK/ROS/native rebuild occurred. Prior stack-access FAIL and original N3
8 PASS/1 FAIL remain separate and unchanged; original hang causality is unknown.

The next prerequisite is an offline review of OCI bootstrap syscall requirements
for the native profile, followed by a separately frozen readiness gate before
any target calibration. Nothing further is queued automatically. Existing
wchan/syscall sampling is not substituted for kernel or user-space stacks.

PLAN.md and freeze.json bind the exact scope and source/binary/helper inputs.
run.py is one-shot and refuses its existing output. runtime-startup-diagnostics,
gate-report, postflight and commands retain the failure and cleanup evidence;
local-artifact-hashes.json covers closed local output and the read-only bundle.
