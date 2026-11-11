# Explicit socket dispositions and one bridge shutdown diagnostic — 2026-11-10

**One newly authorized live attempt after regression checks and a new freeze.**
User authorizes explicit socket-disposition tracing and matching gates with regression tests, then one N0
seed1701/10s attempt, stop at first failed gate. Preserve the previous failed
run, its source/freeze and raw evidence unchanged. The separate authorization
file binds this new freeze and the same single hash-bound scope:
`one-N0-1701-10s-operator-bridge-shutdown-diagnostic`. This is diagnostic evidence,
not campaign advancement, another N3 cohort or a two-loss-4211 retry. All 29
remaining campaign cases remain disabled regardless of outcome; M3 open/PR2 draft.

## Fixed workload and target

Exactly one healthy N0 SENSOR session, seed1701, 10s publication window, original
200Hz IMU/50Hz joints, permanent neighbors and unchanged N0 qdisc settings. No
selected packet loss, neighbor manipulation, load, command submission, expiry or
replay. Reuse the existing N0 source/capture/accounting adapter, original clock,
queue/rate/crypto/worker settings, new socket-disposition SDK/ROS14 inventory (old13 preserved),
pinned amd64 image/provider and original stop_children 5s SIGINT wait. New isolated matching SDK/ROS build for tracing only; no shutdown hold, budget increase, failure injection, tuning or fallback.

Enable existing default-off stage tracing on both bridges. Observe only the
operator bridge (plain SDK journal worker, matching the earlier failure role)
and descendants registered by PID/start_ticks. Robot stages/child exit remain
required context; no second sidecar, blocked fixture or bridge restart. Existing
monotonic packet capture/source/typed conservation gates stay enabled. A healthy
N0 shutdown may not reproduce the old faulted-case hang; no causality inference
or N3 acceptance follows from a passing diagnostic.

## Observer and least-privilege integration

Use the same calibrated native ARM64 image and observer budgets/profile, read-only helper bundle,
fstatfs/openat2 profile and native architecture/runtime-version checks. The
sidecar alone gets SYS_ADMIN, no SYS_PTRACE. NNP1, default-deny seccomp, read-only
root, network-none, private root-owned output volume; join only operator lab PID
namespace. No host PID/proc/socket/workspace/credential mount, debugger, new image,
unconfined/privileged mode, global sysctl or permission change. The legacy
in-container observer is explicitly forbidden.

The existing lab still owns NET_ADMIN/BPF for its unchanged qdisc/capture tools.
A new explicit wrapper drops all bridge bounding/effective/permitted/inheritable/
ambient capabilities, enables NNP and same-UID dumpability before exec. Both real
bridge identities attest zero capabilities/Seccomp2 after launch. This reduction
is needed for same-UID proc inspection without granting SYS_PTRACE to the
observer. The lab supervisor/source/capture retain existing lab permissions and
are outside the observed root. No SYS_ADMIN is added to either bridge container.

This wrapper and bridge-specific host integration are offline validated only;
they are not already live-calibrated. Capability reduction, credential/journal/
trace-path access and bridge readiness must pass in the future run. Any failure
stops the one-shot diagnostic, without relaxing permissions or trying again.

## Signal fence and evidence gates

Before any live process: require separate exact authorization, prospective source/
input freeze, new matched14/old13 preserved chain and calibrated observer runtime/image/
profile. Refuse existing output, unrelated running containers or changed inputs.
Only change to the observer isolation gate: strip the optional CAP_ prefix
from CapAdd before requiring exactly the SYS_ADMIN set. Extra/missing capability
and all other isolation mismatches still fail. No policy/filter/timing change.
The driver admits only fixed N0/1701/10s/capture/trace arguments; no dispatcher.

After both measured SENSOR barriers and capture closure, register operator
bridge identity in the fresh observer volume. Retain Docker OCI errors plus
entry/preexec_verified/exec_begin/capability/boot/time-namespace proof. Observer
must be ready before touching the existing release fence that permits SIGINT.
No artificial sleep is added to bridge shutdown. Arm failure aborts measurement;
original cleanup still signals/reaps owned children and records that this was
unobserved failure cleanup, not a diagnostic PASS.

Collect until the original child stop helper completes, then stop/export/reap the
sidecar before removing the target lab PID namespace. Preserve raw files on
success and failure. Require clean exit0/unforced, original complete zero-drop
stage sequences/thread/clock pairs, unchanged SENSOR cadence/zero skips/age and
source/typed/packet accounting, full capture controls and cleanup for PASS.
Observer requires shared boot/time origin, exact identity, successful bounded
finalization, no live-target denied/truncated stacks or process/thread-limit hit,
and at least one nonempty real-bridge kernel stack. A fast clean exit may have
zero post-signal samples; record that limit without stretching shutdown timing.
A forced child kill is always FAIL; additionally require at least two contained
post-signal samples with nonempty kernel stack coverage to call its observation
complete. Partial stages or stacks are retained, never filled in or called PASS.

Stop at the first failed gate. No statistical retry, second profile/seed, bridge
relaunch, filter/capability change, cohort splice or other campaign stage. Owned
children, sidecar, containers, internal network, capture processes, credential
and output volume must be cleaned up, with absence and pre/post source/binary/
old-evidence hashes verified. ARM64 kernel stacks under amd64 emulation are not
application user frames or an observer-overhead equivalence result.

Lifecycle visibility adds read-only stat outcomes: matching identity, ENOENT
process_missing, different start_ticks pid_reused, and identity_unavailable for
permission/malformed/other errors. No ambiguous gone_or_reused row is accepted.
Known worker must be sampled with matching PID/start_ticks/name/direct parent
before SIGINT; accept later missing only after unique same-thread ordered
worker_join_begin/end with zero stage drops and correct root identity. Missing
root before supervisor reap, wrong/unknown worker, premature disappearance, reuse,
read failure, changed identity during sample and truncation still fail. Check
reuse/errors even in samples after root reap. Confirmation establishes termination
of a registered worker after join completion, not its exit code or death cause.
The prior ambiguous FAIL is not reclassified. Observer Python changes only;
new tracing-only native build, no privilege/filter/sample-period/5s wait changes.

Native trace additions: every final CONTROL/SENSOR data/listener slot emits
exactly one disposition with its current SRT fd (-1 means already invalid).
Every locally traced valid close emits begin(fd), result(return value), end(fd)
after existing epoll-remove marker. Use one observation decision per helper call;
SRT close count/order/result handling and slot invalidation remain unchanged.
No syscall/rate/queue/timeout/crypto policy changes. A new SDK/ROS layout preserves
all earlier build paths/binaries and uses the unchanged pinned SRT provider.
Gates require all four unique slot dispositions within channel boundaries and
matching same-thread fd/result close brackets for valid slots. Already-invalid
slots must have no close bracket there; every traced close result must be zero.
Missing/duplicate/negative-other-than-minus-one/mismatched fd/out-of-phase records,
wrong thread, trace loss, orphan close and close error all fail. Prior socket
marker FAILs are preserved, not retroactively passed. No universal socket-close
presence requirement substitutes for this positive disposition evidence.

Concurrent trace writes may arrive out of file order. Validate the complete unique
sequence population and same-thread join/close call order, not inter-thread write
arrival order; regression covers reordered file records without accepting gaps.
