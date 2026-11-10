# OCI runtime bootstrap review — 2026-11-10

The daemon reports runc 1.5.2, commit v1.5.2-0-g29dd3dc2. Review uses that
upstream tag and its go.mod dependency filepath-securejoin v0.7.0. Downloaded
sources stay local with SHA256 references in bootstrap-review.json; this is
source-path correspondence, not reproduction or attestation of the daemon binary.

With no-new-privileges, [standard init](https://github.com/opencontainers/runc/blob/v1.5.2/libcontainer/standard_init_linux.go)
installs the payload seccomp policy before its final FIFO reopen and exec.
No seccomp notification rule is configured; syncParentSeccomp returns without
its socket exchange. User/capability/namespace setup precedes this filter point.
StartContainer hooks are not configured in this Docker invocation.

[Safe procfs handling](https://github.com/cyphar/filepath-securejoin/blob/v0.7.0/pathrs-lite/internal/procfs/procfs_linux.go)
validates descriptors with fstatfs/fstat. The prior runtime error reaches this
validation on its existing procfs descriptor. Mount APIs are neither needed for
that validation nor newly allowed. The fsmount label in the prior error names
the descriptor; it is not evidence that an fsmount syscall must be permitted.
[Lookup](https://github.com/cyphar/filepath-securejoin/blob/v0.7.0/pathrs-lite/internal/procfs/procfs_lookup_linux.go)
selects openat2 when the kernel supports it. Denying that call with EPERM would
fail this branch rather than select its legacy lookup path. Both file-validation
calls were missing from the previous profile; add only fstatfs and openat2.

The rest of the reviewed path uses existing openat/fcntl/statx/fstat/access/
readlink/getdents64/close/write allowances. Final descriptor cleanup uses the same
safe procfs wrapper and ordinary directory reads/close, then execve. Go/Python
memory, futex, signal and clock-read calls retain their existing allowances.
No new permission for mounts, fsopen/fsconfig/fsmount/open_tree/move_mount,
namespace changes, capset/prctl, ptrace/process-memory, sockets or fork/clone.
NNP and role capabilities remain Docker-configured before policy installation.

Default deny remains EPERM with the same native ABI and isolation. Offline tests
assert the exact two-call delta and preserve denied-operation/capability/exec
error checks. Source review does not guarantee a complete live bootstrap contract;
readiness is the necessary test under the exact frozen policy. One readiness
check precedes one original blocked fixture only if successful. No policy edits,
fallback or rerun after a failed gate in this prospective attempt.
