# Bounded live shutdown calibration — 2026-11-09

**Overall FAIL at the kernel-stack access gate.** Default-off behavior, healthy
shutdown-stage tracing and independent post-signal sampling pass their declared
subgates. Kernel stacks are unavailable:22 post-signal reads return PermissionError,
errno13. No fallback, privilege change, tuning or retry followed. All29 remaining
campaign cases stay disabled; M3 remains open, PR2 draft and M4 untouched.

The user authorized bounded live calibration on a new matched build, excluding
any retry of two-loss4211. PLAN.md was predeclared before execution. Exactly three
slots ran once, stopping at the first failed live gate. None is a campaign
qualification case: no selected packet loss, seed4211, N0 combined command control,
N4/N1/N2/N5 case, forced expiry or historical command replay ran.

| Slot | Result | Declared evidence |
|---|---|---|
|Default-off N0 SENSOR,1701/10s|PASS|Original cadence/zero-skip/window/age/accounting/trace/capture/cleanup gates; no shutdown-stage/observer files or child records|
|Enabled N0 SENSOR,1701/10s|PASS|Same gates,51 operator/42 robot stage records, contiguous identities/zero drops, required stage/thread/time pairs; independent observers armed before SIGINT and cleanly closed|
|Separate3s blocked-thread target|FAIL stack access gate|Target exits0 without force in3.061764543s under unchanged5s wait;5 complete fixture stages; observer has11 contained post-signal samples/22 thread reads, but0 nonempty kernel stacks|

## New matched build and unchanged settings

New SDK `install/bridge-shutdown-trace-calibration` and all3 ROS packages under
`install/m3-shutdown-trace-calibration-ros` were built from current source in the
same pinned amd64/Jazzy image/provider, into fresh build/install directories.
The13-entry binary inventory includes SDK archives/worker, ROS executables and
one separate finite fixture. Actual ROS CMake import and embedded new worker
prefix were checked. The new `shutdown-tracing` layout recursively verifies all
preserved candidate chains, including sender-reconcile, before/after each slot.
It is a matched build with **partial calibration**, not full qualification.

Network/SRT/ROS clock, source rate, queues, crypto, retries and5s child SIGINT wait
are unchanged. The SENSOR slots use the existing N3 fixture's N0 profile,
permanent-neighbor scope and NET_ADMIN/BPF capabilities. The blocked target runs
network-none with ordinary image defaults: no added capabilities, ptrace/sysctl
change or tool installation. The pinned image has no GDB/eu-stack/pstack; procfs
mode was selected prospectively. User-space debugger calibration was not run.
All13 old sender-reconcile entries and prior build chains still match. The
preparation compile artifacts and913 original N3 raw files are unchanged.

## Positive visibility results and limits

The enabled operator and robot logs contain real main/context, destructor,
endpoint/worker join, socket/epoll, run-local provider cleanup, trace-drain and
post-node-reset stages. Identity, monotonic/thread pairs, contiguous sequences
and zero-drop fields pass. Operator SIGINT-to-reap is221.282ms enabled versus
223.842ms off; robot342.737ms enabled versus340.790ms off. These two observations
are not an overhead estimate, speedup or timing equivalence claim. Enabled clean
exits each had one contained post-signal observer sample.

The synthetic target is not the failed bridge case. It uses the new SDK's trace
header and deliberately waits on a condition variable for exactly the predeclared
3s after SIGINT, then releases its worker thread. It sends no ROS/SRT/network or
application command. Its supervisor still waits5s. The separate observer keeps
recording while the parent blocks, with valid PID/start identity and zero time
namespace offsets. Both target tasks are sampled sleeping in `futex_do_wait`.
This verifies independent wait coverage, not successful stack access.

All22 post-signal kernel stack reads are denied. wchan/syscall data are not
substituted for a stack, and zero readable stacks is not interpreted as an empty
healthy stack. The observer lifecycle completes without exhaustion/forced kill;
its24 total kernel stack reads are all unavailable. The exact capability/LSM/
ptrace rule causing denial is not established by this calibration. No permission
was relaxed and no target was re-run. The next prerequisite for stack calibration
is a separately scoped access/tooling decision; it is not production tuning or
an instruction to retry until passing.

## Execution integrity

Before live launch, a Python import collision made the new wrapper and offline
gate controls resolve the ROS script m3_source_preflight instead of the tools
module. Startup failed before any slot or output directory existed. The import
order was fixed, two offline gate controls rerun successfully, and a corrected
prospective freeze issued. Failed logs and the invalidated initial freeze/
preflight are retained. No live case was retried or substituted. Full offline
suite457 tests and the two gate controls pass before actual measurement; no heavy
checks overlapped live capture.

The final freeze binds exact plan/driver/fixture, source inventory, image, matched
candidate/preserved chain and fresh output directory. It still matches postflight.
The default-off and enabled sensor namespaces/credentials were removed; the
network-none target container was auto-removed. All owned processes exit cleanly;
no forced bridge/target shutdown, debugger attach or permission intervention.
Calibration JSON retains inner statuses independently of strict verdicts.

## Evidence and acceptance boundary

- PLAN.md and freeze.json: prospective three-slot scope and unchanged settings.
- binary-verification.json: immutable matched-build inventory, not a PASS label.
- gate-report.json/calibration.json:2 passed slots, failed stack-access gate;
  no remaining campaign-stage authorization.
- operator/robot-shutdown-stages.jsonl: real healthy shutdown stages.
- stages.jsonl, child-shutdown.json, observer-coverage.json and
  blocked-target-shutdown-stacks.jsonl: finite target and explicit denied reads.
- local-artifact-hashes.json:219 retained local files (~23MB), including complete
  packet/source/typed records, per-case provenance and independent observer logs.
- preflight/postflight, original failure and corrected validation logs.

This does not diagnose the original operator shutdown hang, reproduce it, close
two-loss4211, establish9/9 N3, quantify trace cost or qualify all future blocked
states. Original cohort remains8 strict PASS/1 FAIL. No retry/cohort splice or
N0/N4/N1/N2/N5 advancement follows from the partial calibration. The requested
bounded run is complete; stack capture remains explicitly uncalibrated.

Versioned build/validation logs remove trailing whitespace; exact original copies
remain locally hash-indexed in raw-log-manifest.json.
