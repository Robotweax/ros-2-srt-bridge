# Prospective observer-only stack-access calibration — 2026-11-09

User authorizes narrowly scoped observer stack permissions and one rerun of only
the finite blocked-thread calibration. No bridge control or campaign case,
no two-loss4211 retry, no tuning. All29 remaining campaign cases stay disabled.

Use the exact previous shutdown-tracing13-entry matched build and original
blocked_fixture binary/source. Do not rebuild/change the fixture, SDK, observer
logic, sampling limits,3s hold or5s SIGINT wait. One fresh run, no retries or
permission fallback after its first failed gate.

Upstream Linux7.0 fs/proc/base.c proc_pid_stack explicitly checks SYS_ADMIN in the
initial user namespace and returns EACCES. Its subsequent lock_trace is also used
by proc_pid_syscall, whose reads already succeeded in the retained calibration.
This informs one selected capability, SYS_ADMIN, not SYS_PTRACE. Vendor LinuxKit
source equivalence and sufficiency are tested, not presumed.

Create one private-PID, network-none, nonprivileged container from the same pinned
image, with --cap-drop ALL and --cap-add SYS_ADMIN, no-new-privileges and Docker's
unchanged built-in seccomp. No host PID/user namespace, host /proc, Docker socket,
network capabilities, devices or sysctl change. Root filesystem is read-only;
only a minimal read-only bundle (frozen fixture, helper modules and controller)
and one fresh root-owned named output volume are mounted. /tmp is transient.
No full workspace/host writable mount or package/debugger installation.

The supervisor's bootstrap needs the capability to start the observer. It forks
the target with all effective/permitted/inheritable/ambient capabilities zero,
no-new-privileges and a dumpable same-UID identity before executing the unchanged
fixture. It starts the observer with only SYS_ADMIN, then drops its own active
capabilities before SIGINT. Require attestation that only the observer retains
that capability during the wait; target/supervisor remain zero and cannot regain
it through exec (NNP1). The bounding set remains the single selected bit.

The observer receives an additional seccomp filter stacked over Docker's default:
reject foreign/x32 ABI and administrative mount/namespace/kernel/BPF/ptrace/
process-memory/network/child-creation syscalls. Initial interpreter exec and
ordinary proc reads/writes/waits remain allowed. Filter bytecode/semantics are
unit-checked offline; require one extra active filter on the observer. No GDB,
no attachment/stop-the-world operations, no privileged operation probes.

Gate before SIGINT on target readiness, observer readiness and exact role
capability/NNP/seccomp proof. Then retain existing5s stop_children behavior.
Require target exit0/unforced within2.5..5s, all5 original fixture stage markers,
valid observer identity/zero time namespace offsets, unexhausted bounded observer
lifecycle and at least2 contained post-signal samples. Unlike the prior denied
run, require nonempty successful kernel-stack reads for both original target
threads during the known wait; no truncation/identity failures or denied
post-signal stack reads. Missing/denied data fails and stops, without fallback.

Export closed evidence, remove the container and its named volume, verify no
permissions persist. Preserve prior calibration FAIL and original N3 8PASS/1FAIL.
Success would calibrate kernel stacks for this synthetic target only, not user
stacks, original-hang cause, bridge reproduction, N3 completion or M3 acceptance.
