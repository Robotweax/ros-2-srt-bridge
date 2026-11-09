# Prospective bounded shutdown calibration — 2026-11-09

Authorized by user: bounded live calibration on a new matched build, no tuning,
no retry of two-loss4211; remaining campaign stages disabled. This is a separate
calibration, not another N3 qualification cohort or a campaign resumption.

One new matched shutdown-tracing SDK/ROS layout, pinned existing image/provider,
Release settings, original clock/queue/rate/crypto and5s child SIGINT wait.
Preserve all archived candidates. Freeze sources/driver/binaries before launch;
stop on first failed gate, no retries, no fallback/permission changes mid-run.

Exactly three one-shot slots, in order:

1. Default-off N0 SENSOR control: seed1701,10s, baseline N0 kernel settings,
   permanent neighbors as existing N3 fixture scope, original native/full packet
   capture and source/typed accounting. Require zero skips,1% cadence, original
   10s window budgets, age<=250ms, complete logs/captures, clean child/lab cleanup.
   No shutdown trace files, observer files or observer child reports may appear.
2. Enabled N0 SENSOR control: same10s/settings, shutdown stages and independent
   observer enabled explicitly, procfs mode. Same original measurement/cleanup
   gates plus complete/zero-drop stage markers and valid begin/end thread/clock
   pairs, both-role main/node/endpoint/worker/transport/provider boundaries.
   Observer must be armed before SIGINT, a distinct process with zero time
   namespace offsets, complete bounded lifecycle/no identity or budget failure.
   Clean shutdown can finish before the250ms sample period: post-signal samples
   and stack-read availability are recorded here, not inferred or required.
3. Independent blocked-thread calibration target: separate finite C++ process,
   no ROS/SRT/network traffic or command, newSDK trace header, one condition-variable
   waiting thread and a predeclared3s timed wait after SIGINT. Supervisor retains
   its existing5s wait. No bridge shutdown hold/timing/parameter is changed.
   Require clean unforced exit within2.5..5s, complete fixed fixture markers,
   observer ready before signal and at least2 fully contained post-signal samples.
   Kernel stack calibration additionally requires at least one nonempty successful
   post-signal kernel stack. Unavailable/denied reads fail that gate explicitly;
   independent sampling alone is insufficient. No syscall/wchan substitution for
   a stack, and no retry with more privileges.

Nominal SENSOR source20s + fixture hold3s, excluding build/start/drain/capture/
analysis/cleanup. Pinned image preflight has no gdb/eu-stack/pstack. GDB mode is
not selected; do not install tools or change image/capabilities/sysctls/ptrace
settings. SENSOR slots retain original NET_ADMIN/BPF fixture capabilities;
blocked target uses network-none with ordinary image defaults. Stack permissions
are measured as-is. Denied kernel stacks remain a possible calibration failure,
not a reason to modify the environment until it passes.

No N3 selected-loss case, seed4211 case, N0 combined command case, N4/N1/N2/N5
qualification slot, expiry or historical command replay is authorized. The29
remaining campaign cases stay disabled even if all calibration slots pass.
Calibration cannot promote the older8PASS/1FAIL cohort or accept M3.
