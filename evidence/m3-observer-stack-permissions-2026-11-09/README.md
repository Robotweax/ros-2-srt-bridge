# Observer stack permissions: single blocked-target attempt — 2026-11-09

**FAIL before the observer armed. Stack access remains uncalibrated.** One
unchanged blocked target ran; its cleanup exited0 without force after
3.074699502s under the existing5s wait. No retry, bridge/sensor case, two-loss4211,
production tuning or remaining campaign stage was run. All29 campaign cases stay
disabled; M3 open, PR2 draft and M4 untouched.

## Permission preparation and isolation

Upstream Linux7.0 proc_pid_stack explicitly checks SYS_ADMIN in the initial user
namespace before lock_trace and returns EACCES when it is absent. The subsequent
lock_trace check is also used by proc_pid_syscall, whose retained reads succeeded.
That evidence informed selecting SYS_ADMIN only, without SYS_PTRACE, debugger
installation, sysctl changes or privileged mode. The upstream/vendor equivalence
is not assumed. See [upstream source](https://raw.githubusercontent.com/torvalds/linux/v7.0/fs/proc/base.c)
and kernel-source-reference.json (content hash and short guard excerpt).
Docker's [capability controls](https://docs.docker.com/engine/containers/run/)
apply per container; no daemon/global permission setting was changed.

The predeclared policy creates one private-PID/network-none container from the
same pinned image, dropping all capabilities except SYS_ADMIN. Root filesystem
is read-only, no-new-privileges enabled and Docker's built-in seccomp retained.
Only a minimal read-only bundle is exposed: unchanged target/observer/cleanup,
new controller and permission helper. A fresh root-owned named output volume
avoids needing DAC/CHOWN privileges on a host writable bind. No full workspace,
host PID/proc, Docker socket, host network or writable host mount is exposed.

The design drops all active capability sets in the target before exec and in the
supervisor before signalling, leaving SYS_ADMIN only in the observer. A further
in-process seccomp filter was intended to deny administrative mount/namespace,
BPF/kernel/ptrace/process-memory/network and child-creation operations while
preserving passive proc reads. Foreign/x32 ABIs are refused. This filter is
**native x86-64 only**; the offline policy emulator correctly validates its
instruction semantics, but that does not establish compatibility with emulation.

## Observed failure and missed preflight

The container-policy inspection passed. The unchanged target started with its
pre-exec capability-drop self-check. Observer creation then raised exactly:
`SubprocessError: Exception occurred in preexec_fn.`

The current Popen error path does not retain the nested exception/errno or exact
failing call. No observer ready marker, JSONL data or per-role before-signal
permission proof exists. Therefore this run cannot attest observer capability
retention, filter installation, successful stack access or improved visibility.
An empty observer log is not evidence that the observer ran successfully.

Read-only daemon metadata establishes **aarch64**; the selected image/process is
amd64. The helper checks the process architecture and constructs a native-x86-64
BPF filter. That is not a valid daemon-native architecture preflight. This is a
concrete compatibility blocker, independent of which pre-exec call raised; the
record does not prove an exact kernel/emulator errno or implementation-specific
cause. I missed this check before target launch. It should have been caught by
comparing native daemon and image/filter architecture first.

No policy fallback or target rerun followed. A future design must enforce a
compatible daemon-native observer policy (or use a compatible native execution
path), preserve the capability/namespace/mount limits and retain pre-exec errors
explicitly before another calibrated attempt. Do not use this experimental
in-process filter as a ready ARM64-host permission recipe. No such alternative
profile, debugger, permission escalation or live attempt was introduced here.

## Cleanup, integrity and scope

On preparation failure, the supervisor dropped its active capabilities and
signalled/reaped the target through the unchanged helper. The target completed
its3s condition-variable wait and all5 original markers, exited0, no forced kill.
The final supervisor status attests effective/permitted/inheritable/ambient sets0
and NNP1; its bounding set is the selected SYS_ADMIN bit, not an active grant.
The intended before-signal per-role proof was not reached and is not inferred.

The container and named volume were removed (both exit0), and absence verified.
There is no remaining privileged process or persisted permission change. The
read-only helper bundle remains locally hash-bound as evidence, not executable
authorization. All13 matched shutdown-tracing entries, earlier calibration
records and913 original N3 raw files verify unchanged. No SDK/ROS/native rebuild.
The previous kernel-stack denial and this preparation failure remain separate
FAIL records; neither replaces the other or affects the original8PASS/1FAIL N3.

Validation before the attempt:461 offline Python tests, four new permission-policy
checks and one evidence-local final-gate control passed. Tests use synthetic BPF,
capability dictionaries and file records; they did not install a host filter or
prove Linux/daemon compatibility. No heavy checks overlapped the single run.

Evidence: PLAN/freeze/bundle manifest, policy instructions and kernel source
reference; commands/inspect/result/cleanup in local-artifact-hashes; copied stage,
child/final-permission records; gate-report and postflight. Exact fixture binary
and observer bytes match the previous matched build. No other calibration slot,
statistical retry, queue/deadline change, historical command replay or campaign
advancement follows. A compatible permission mechanism is still a prerequisite.
