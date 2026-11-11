"""Daemon-compiled, native-architecture observer policy. No in-process seccomp install."""
import errno
from pathlib import Path

# runc post-seccomp FIFO/procfs validation also needs fstatfs/openat2.
# Single-threaded native Python/procfs collector only. No sockets, ptrace,
# process-memory, mounts, namespaces, BPF, credentials, clocks or child creation.
OBSERVER_SYSCALLS=set('''read write readv writev pread64 pwrite64 close close_range lseek fstat fstatfs newfstatat statx
access faccessat faccessat2 openat openat2 readlink readlinkat getdents64 getcwd
mmap mprotect munmap mremap madvise brk
rt_sigaction rt_sigprocmask rt_sigreturn sigaltstack restart_syscall
futex set_tid_address set_robust_list rseq
clock_gettime clock_getres clock_nanosleep nanosleep gettimeofday times
getpid getppid gettid getuid geteuid getgid getegid getresuid getresgid getgroups uname sysinfo
getrlimit prlimit64 sched_getaffinity sched_yield getcpu membarrier
fcntl ioctl dup dup3 pipe2 poll ppoll pselect6 epoll_create1 epoll_ctl epoll_pwait
getrandom umask fchmod fchmodat mkdir mkdirat unlink unlinkat renameat renameat2
fsync fdatasync ftruncate exit exit_group execve execveat'''.split())


def architecture(value):
    aliases={'arm64':'arm64','aarch64':'arm64','amd64':'amd64','x86_64':'amd64'}
    if value not in aliases:raise ValueError('unsupported daemon/image architecture: '+value)
    return aliases[value]


def profile(daemon_arch,image_arch):
    native=architecture(daemon_arch)
    if native!=architecture(image_arch):raise ValueError('observer image must be daemon-native; emulated observer filtering is refused')
    return dict(defaultAction='SCMP_ACT_ERRNO',defaultErrnoRet=errno.EPERM,
        architectures=['SCMP_ARCH_AARCH64' if native=='arm64' else 'SCMP_ARCH_X86_64'],
        syscalls=[dict(names=sorted(OBSERVER_SYSCALLS|({'arch_prctl'} if native=='amd64' else set())),action='SCMP_ACT_ALLOW')])


def status(pid='self',proc=Path('/proc')):
    keys={'Name','Pid','PPid','Uid','Gid','CapInh','CapPrm','CapEff','CapBnd','CapAmb','NoNewPrivs','Seccomp','Seccomp_filters'}
    return {key:value.strip() for line in (proc/str(pid)/'status').read_text().splitlines() for key,_,value in [line.partition(':')] if key in keys}


def require_role(fields,capability):
    if any(int(fields[k],16)!=capability for k in ('CapEff','CapPrm','CapBnd')) or any(int(fields[k],16) for k in ('CapInh','CapAmb')):raise ValueError('role capability set differs from declared scope')
    if fields.get('NoNewPrivs')!='1' or fields.get('Seccomp')!='2':raise ValueError('NNP/seccomp protection missing')
