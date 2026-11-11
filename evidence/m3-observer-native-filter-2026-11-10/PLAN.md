# Native observer policy and one blocked calibration — 2026-11-10

User authorizes architecture-compatible filtering and explicit pre-exec diagnostics,
then only the blocked-thread calibration. No tuning, two-loss4211 retry, bridge,
SENSOR/control cohort, N4/N1/N2/N5 or other campaign stage. All29 cases disabled.
Preserve previous failed runs and their exact frozen evidence.

Architecture preparation: query daemon native architecture, resolve a native
arm64 observer image from the existing pinned ROS base digest, and require an
exact daemon/observer match before creating any target. Keep the original pinned
amd64 target image, SDK13 inventory, original blocked binary/source,3s wait and
5s child SIGINT budget unchanged. No native syscall numbers or in-guest filter
installation on the emulated process. No SDK/ROS rebuild.

Docker/libseccomp compiles a named-syscall default-deny profile for the native
observer. Allow only interpreter startup/exec, passive proc/file/clock reads,
private output writes and ordinary memory/signal/wait operations. Deny mounts,
namespaces, credentials, BPF/kernel administration, ptrace/process-memory,
network and fork/clone. The target retains Docker default seccomp and ALL
capabilities dropped/NNP1; its supervisor also has no capability (including
bounding) at any time. Observer alone receives SYS_ADMIN (no SYS_PTRACE), NNP1,
read-only root/helper bundle and the native custom policy, network-none. It joins
only the target's private PID namespace, never host PID/user/network. Minimal
read-only bundle and fresh root-owned named output volume only; no host writable
workspace/proc/socket. No global daemon/sysctl changes, unconfined/privileged mode,
debugger installation, CAP fallback or production timing/rate/queue change.

Exactly one observer readiness self-check, with no target/stack read, precedes
fixture launch. It must execute native Python under the exact final policy and
produce entry/verification/self-check records, matching role/architecture/profile
hash and clean exit. Docker/runc startup errors are retained even if Python never
starts. On failure, do not start the target or relax the policy mid-run.

After readiness and freeze checks, run exactly one unchanged blocked fixture.
Its unprivileged supervisor starts the target and waits for host authorization;
no SIGINT until the native observer has readiness and explicit pre-exec/exec
records with correct capability/NNP/seccomp proof and matching target identity.
No Python preexec_fn: the native launcher writes stage, errno, exception type,
message and traceback around setup and os.execv; error fallback also goes to
stderr. Docker state/log/exit errors preserve pre-interpreter startup failures.

The existing stop_children sends SIGINT/waits5s. Require target exit0/unforced
within2.5..5s, all5 original stages with contiguous sequence/identity/zero drops,
observer readiness before signal, independent mode/time namespace/identity proof,
no observer budget/truncation/finalization failure and at least2 fully contained
post-signal/known-blocked samples. Require nonempty successful kernel-stack
reads for both registered threads and no denied reads in that interval. No
wchan/syscall substitution or user-stack/GDB claim. Target PID1 stays alive
briefly after its child exits only to let the sidecar finish its footer; this
post-child coordination does not extend or retime the5s child gate.

Stop first failed gate; no further target attempt, policy adjustment or alternative
mode in this plan. Export closed evidence, remove both containers and the output
volume. A PASS would calibrate kernel-stack collection on the synthetic target
only, not original-hang causality, user-space stacks, N3 completion or M3 acceptance.
