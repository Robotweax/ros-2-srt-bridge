# Reviewed bootstrap policy and blocked-thread calibration — 2026-11-10

**PASS: one native observer readiness check and one unchanged blocked fixture.**
The default-deny observer filter adds only fstatfs and openat2 after upstream
runtime source review. All 468 Python tests pass. No production tuning,
two-loss-4211 retry, bridge/SENSOR case, expiry/replay or other campaign stage ran.
All 29 remaining campaign cases stay disabled; M3 open, PR2 draft, M4 untouched.

[Bootstrap review](BOOTSTRAP_REVIEW.md) explains the runc 1.5.2 post-seccomp FIFO
and safe-procfs path. [Source references and hashes](bootstrap-review.json) bind
the review; this is not binary reproduction of the daemon. The previous failed
native profile, readiness and opaque permission-attempt evidence stay immutable.

## Observed calibration

Readiness emitted entry, preexec_verified and self_check_passed, exiting 0 under
the exact frozen native ARM64 filter. It ran without a target or stack read.
The single original amd64 blocked fixture then launched under the unchanged
pinned target image. Its native ARM64 observer joined only that target's private
PID namespace, verified target PID/start_ticks and emitted entry,
preexec_verified, exec_begin and observer-ready before SIGINT. Matching boot ID
and zero time-namespace offsets establish a shared monotonic origin.

Only the observer has SYS_ADMIN; its effective/permitted/bounding sets equal
bit21 and inheritable/ambient sets are zero. Target and supervisor proofs show
all five capability sets zero, NNP1 and Seccomp2 before SIGINT and supervisor
finalization. Both containers have read-only roots, minimal RO helper bundle,
network-none, fresh output volume, NNP and no host namespace/socket/workspace
exposure. Target uses Docker default seccomp; observer uses the exact native
allowlist. Mount/namespace/credential, ptrace/process-memory, network, BPF and
fork/clone operations remain denied. No SYS_PTRACE, GDB, privileged/unconfined,
global permission change or policy fallback.

The target exits 0 without force after **3.053350251s** from signal completion
through reap, inside its original 5s wait. All five original fixture markers are
present, contiguous and identity-matched with zero dropped stages. The original
3s condition-variable hold and binary are unchanged.

There are **12 fully contained post-signal/known-blocked samples, 24 successful
nonempty kernel-stack reads**, two threads (TIDs7/8), no denied or truncated reads,
identity failures or observation-limit hits. Both show ARM64 futex kernel frames,
consistent with the target's two condition-variable waits. Total observer output:
13 samples/26 successful stack reads/zero unavailable; completed footer with
parent_stop and no budget exhaustion. No debugger attach or userspace stack.

These are Linux ARM64 kernel stacks for the unchanged amd64 fixture executing
through emulation. They do not resolve amd64 application frames, prove live
observer overhead equivalence, identify the original bridge hang, close N3 or
qualify a new production cohort. The synthetic result establishes kernel-stack
collection on this host under this exact bounded observer policy only.

## Integrity and disposition

Readiness, target and observer containers and both output volumes were removed;
absence verified. No forced cleanup. Source/input/helper/profile freeze, all13
matched SDK/ROS entries and preserved build chain match postflight. No native,
SDK or ROS rebuild. All913 original N3 raw files,219 older calibration files and
both previous observer attempts retain their hashes. Original N3 remains8 PASS/
1 FAIL with unknown hang cause. No retry, passing-prefix splice or stage advance.

PLAN/freeze/preparation/driver bind the prospective scope. Public records include
ready/exec/capability/child/stage/stack evidence, gate-report and postflight.
local-artifact-hashes indexes97 closed local artifacts, helper files and reviewed
source files. The raw observer JSONL is also published unchanged. The one-shot
driver refuses its existing output. No further experiment is automatically queued.
The next decision concerns a separately scoped bridge-hang diagnostic attempt;
this calibration itself grants no original-case retry or remaining campaign run.
