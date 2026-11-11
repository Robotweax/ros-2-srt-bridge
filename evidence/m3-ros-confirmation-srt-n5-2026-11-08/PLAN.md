# ROS discovery confirmation and longer SRT N5 progress

Freeze plan and Python implementation before live execution. Six ordered slots,
fresh owned namespaces, exactly once each; no retry or replacement. Two independent
groups: stop/skip remaining ROS slots if a ROS gate fails; stop/skip remaining SRT
slots if an SRT gate fails. A failed ROS group does not cancel independent SRT
work. Preserve original statuses/reasons, including not-executed slots. CLI returns
nonzero if any group fails. PR2 remains draft; Intrinsic/M4 untouched.

1. ROS DDS N0/system/control-first, seed1701,15s measured workload.
2. Same fresh ROS fixture with robot continuation offset185 cut before any ROS
   participant starts;8s VM hold after both command owners' local journal/handler/
   QoS eligibility. Same existing owned u32 selector as native proof. This is
   controlled ROS N0 confirmation, deliberately removing telemetry overload as a
   confound, not an N5-loaded mitigation or default transport change.
3. SRT N0 preflight15s, seed1701.
4. SRT N5 steady300s, seed1701.
5. SRT N5 steady300s, seed2903.
6. SRT N5 steady300s, seed4211.

ROS real command_node/rate_simulator binaries are reused unchanged. A test-only
file barrier pauses both workload drivers while still spinning local diagnostics;
no Execute/admission/effect and no sensor publication is permitted before restored
qualification. Its90s coordination allowance does not change native1.5s lease,
post-barrier readiness45s, original5s intent start budget or8s result drain.

The cut is installed before node launch, with owned namespace/source/destination/
IPv4 IHL5/UDP/offset185 guard, zero initial and positive actual drop counters,
install/removal VM brackets and empty post-removal readback. Refuse existing hooks.
After8s preserve both diagnostic snapshots: locally eligible, HELLO write attempts
>=30, zero commands/start claims/effects, and at least one missing operator CONTROL
or HELLO endpoint match. Record ready/callback states without assuming all are0.
Restore once even if a later hypothesis gate fails. Require both owners ready,
all four endpoint match counts positive,>=3 HELLO callbacks and unchanged process
epochs within45s after removal; only then release workload barrier. Preserve local
child PID/start metadata, zero pre-start device publication snapshot, original
journal IDs/budgets and post-recovery command proof. Do not require link/session
epochs unchanged across discovery loss. No accepted-command replay.

SRT retains default dynamic neighbors, unchanged512kbit/s TBF/16-packet queue,
128000bit/s competitor,200/50Hz source and absolute2s intent slots with explicit
skips. Command/provider diagnostics and capture drain checks enabled, same methods
for preflight/all three seeds. No new packet fault, provider/SDK timeout or sample
budget changes. This prospectively selected seed matrix is not repetition until
favorable and does not replace old reset/UNKNOWN/capture failures.

All runs require image/provider pins and eight production binary hashes unchanged,
common VM clock proof, original5s sender deadline and earlier/equal receiver
start limit, matching durable success/context/result/generation proof, one SRT
SDK command handoff per successful intent and no duplicate accepted handoff.
All attempts must have confirmed successful outcomes for this progress gate;
UNKNOWN/unresolved/not-admitted cause failure and pause/skips remain explicit,
never fabricated success/nonexecution/expiry. Skipped scheduling slots are reported
rather than silently excluded from offered-work claims. Read journals only after
owned workers close/checkpoint. No new full SDK/ROS build/validation claim.

Capture listeners must be ready before any UDP producer; fixed final file/filter/
kernel/footer gates and bounded stable drain remain unchanged. Reject unreconciled
populations even if older harness status says passed. Record source manifests,
seeds/qdisc/readback/competitor load, original success/failure/skipped matrices,
ROS startup and child shutdown, all SRT incarnation trace/provider completeness,
sensor conservation/age and command counters. Realtime PCAP age authority remains
withheld when clock qualification fails. Native callbacks, packet counts, actual
handler starts and physical device outcomes are distinct. No CPU/security/clock/
semantic equivalence, hardware, cross-host, lossless or superiority claim.

No tests/builds or other experiments concurrent with live slots. Archive selected
metadata/logs and raw file hashes; raw PCAPs/journals/resources/clocks remain local,
exclude credentials and full inspect/environment dumps. Every owned selector is
removed on all exits and child cleanup is bounded before namespace teardown.
Any code correction needs its own declared revision/new output directory; never
rewrite earlier outcomes. Full N5/M3 and default-DDS mitigation remain separate.
