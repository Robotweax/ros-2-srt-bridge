# Shutdown visibility preparation — 2026-11-09

Default-off shutdown-stage tracing and an independent stack observer are
implemented. Validation:456 offline Python tests, one file-only native contract
test, isolated SDK and ROS bridge compilation. No bridge/worker, live observer,
GDB attach, campaign case or new experiment was launched. No production tuning,
retry, forced expiry or replay. All29 remaining campaign cases stay disabled;
M3 open, PR2 draft, M4 untouched. The prior cohort remains8 strict PASS/1 FAIL.

## Stage tracing

The ROS parameter `shutdown_diagnostics` defaults false; its path defaults empty.
Opt-in requires a fresh `shutdown_trace_path`. Existing files/symlinks are refused;
output is a private0600 regular file, separate from stdout. There is no file open
or signal callback registration when disabled. The C++ TransportConfig pointer
also defaults empty; its addition requires matching rebuilt C++ consumers.
Worker IPC stays4 with the existing --worker-ipc-v3 launch flag; no IPC/protocol,
journal, ticket, clock, rate, queue, retry or timeout setting changed.

JSONL records contain schema, sequence, monotonic timestamp, PID, native Linux TID,
constant stage name, optional socket handle and prior write-drop count. They never
carry commands, payloads or credentials. The fixed cap is256 attempted records,
384-byte formatting buffers and one write per admitted stage. Short/error writes
are counted, not retried indefinitely. Sequence allocation can precede concurrent
writes; use sequence/thread/time together, not file order alone. Missing endings,
gaps, malformed records or drops do not prove stage completion. Direct regular
file I/O has no hard latency guarantee; enabled diagnostics add observer work.

Markers cover main spin/context shutdown, ROS context shutdown callback, node
destructor/timer reset, endpoint stop/join, parent worker stop/join, transport
session stop, per-socket epoll removal/close, epoll release, run-local provider
lock/cleanup/release, transport thread body end, trace drain and post-node-reset.
The ROS callback marks context shutdown progress; it is not a raw POSIX signal
handler-entry marker. No custom signal handler was installed. Provider cleanup
markers are inside transport-thread completion, where the retained diagnosis
identified the observation gap. Parent worker markers do not alter the child IPC.

## Independent observer

`shutdown_observer.py` is started as a separate process/session before SIGINT,
with a readiness handshake. It samples independently while the parent blocks in
its unchanged5s `wait`. Start identity is PID+start_ticks. Only the registered
owned child and discovered descendants are followed; reused PIDs are rejected.
Known descendants remain tracked after the root exits. There is no global /proc
scan. Output includes identity checks, task stat/wchan/syscall, kernel stack text,
monotonic brackets, boot/time-namespace proof and explicit unavailable/truncation
fields. Kernel permission failures are not empty successful stacks.

Limits:8 processes,64 threads per process,16KiB per proc read,48 samples at250ms
spacing and a12s observation budget. Kernel/I/O/scheduling and debugger operations
can exceed nominal sampling cadence; limits are not a real-time guarantee.
The observer is stopped after the owned-child wait; its teardown is separately
recorded and excluded from that child's existing signal-to-reap bracket.
Readiness failure cannot prevent child shutdown. Incomplete observer lifecycle
fails the opted-in scenario's diagnostic gate, without manufacturing a command
outcome or hiding a forced kill. Observer lifecycle completion does not assert
that kernel/user stacks were available; sample records/footer state availability.

`procfs` is the stack observer's default mode, and supplies kernel stacks only.
Optional `gdb` mode attempts user-space backtraces after2s if the child is still
present. It needs an available debugger, adequate symbols and ptrace permissions;
none is installed, granted or relaxed automatically. GDB uses no init/auto-load
scripts or debuginfod, suppresses frame arguments, limits backtraces to32 frames
and output to64KiB, and records attach/exit/timeout brackets. Debugger timeout
interrupts/kills the debugger; the observer owns a separate process group so
cleanup can also stop a leftover debugger without signalling the target group.
Target resumption is explicitly **not verified**. GDB attaches pause processes:
those intervals cannot qualify unchanged timing or establish production causality.
Unavailable/failed attaches remain explicit; this mode was mocked, not live tested.

## Wiring and defaults

N3 source runner/scenario expose independent opt-in flags:
`--shutdown-diagnostics`, `--shutdown-stacks`, and `--shutdown-stack-mode gdb`.
GDB mode requires the explicit stack flag. Defaults pass no new bridge parameter,
start no observer and register no extra context callback. Frozen campaign adapters
supply none of the flags. No timeout override, debugger capability change,
automatic grant, retry or experiment command was added. Existing native child
SIGINT budget remains5s. The demo install list includes the observer/helper.

Tests use fake proc trees, fake children and mocked debugger launches/signals.
They cover defaults, identity reuse, missing stacks/debugger, limits, readiness
ordering, parent cleanup despite observer failure and isolated observer-group
cleanup. The native unit writes temporary stage files only, checking exclusive
creation, concurrent records, default-off calls and cap/drop accounting. Initial
native test compilation found a Werror indentation issue in the new test; it was
fixed, with failed log retained. Versioned logs remove trailing whitespace;
exact raw copies are locally hash-indexed by raw-log-manifest.json. Final SDK/ROS compilation succeeds; existing
message interfaces are reused as the explicit ROS underlay.

## Build/evidence boundary

Isolated compile prefixes `install/bridge-shutdown-trace-compile` and
`install/m3-shutdown-trace-ros-compile` are uncalibrated preparation artifacts,
not registered campaign layouts. Actual CMake import and embedded stage strings
were checked. SDK81/ROS41 earlier runtime checks are historical; they were not
rerun or credited to these changed binaries. No runtime shutdown/observer behavior
on the ROS stack, ptrace permissions, symbol completeness or observer timing cost
has been calibrated. Compilation/unit tests do not close an acceptance case.

All13 old matched candidate entries and913 original raw files still match;
archived evidence is unchanged. Current development sources intentionally differ,
so the original full campaign freeze now refuses them. It was not rewritten or
reused. Any future execution needs a separately verified matched build and
prospective freeze, plus explicit scope authorization. No new grant or experiment
was created here. The shutdown root cause remains undetermined until new evidence
is separately authorized; no retry or advancement follows from this preparation.
