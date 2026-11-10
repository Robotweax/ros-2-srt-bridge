# Explicit socket dispositions and one N0 shutdown diagnostic — 2026-11-10

**PASS: one newly frozen N0/seed1701/10s shutdown diagnostic.**
Explicit final-slot ownership and close-return tracing remove the prior ambiguity
without assuming missing close markers mean success. All491 Python tests and the
extended native trace contract pass; an isolated matched SDK/ROS build supplies
14 inventory entries and preserves the old13-entry build plus its full chain.
No tuning, two-loss-4211, command, expiry/replay or other campaign stage. All29
remaining cases disabled, M3 open/PR2 draft/M4 untouched.

## Tracing and matching contract

Each final CONTROL/SENSOR data/listener slot emits exactly one disposition with
its current fd: -1 is already invalid; a valid fd must be followed by the actual
matching epoll-remove/close-begin/result/close-end bracket. Every locally traced
close now records the actual srt_close return value; all such returns must be0.
The helper calls srt_close exactly once and returns its original result; transport
still invalidates the slot afterward regardless of that result, as before. The
existing close count/order, retry policy, crypto, rates, queues and5s child wait
are unchanged. A single per-call observing decision keeps its diagnostic bracket
consistent if another thread requests stop between statements.

Gates require four unique, ordered, correctly phased/threaded slot records; valid
slots require matching fd/outcome pairs, while already-invalid slots cannot hide
close records there. Orphans, wrong/missing/duplicate disposition, invalid fd,
failed result, mismatched thread/fd, missing markers, trace drops and reversed
same-thread close times fail. Unconditional CONTROL/SENSOR/provider/endpoint/node
stage requirements remain. The old unconditional socket-close presence rule is
replaced by this stronger explicit evidence, not simply removed.

Seven Python controls cover preclosed caller slots, valid data/listener slots,
missing/duplicate/invalid dispositions, close errors/missing results/fd mismatch,
concealed orphan closes, thread/phase/drop/time failures and record write order.
The native file contract adds default-off/unobserved no-record controls, exact
one-close call counts and preserved success/error returns with recorded outcome.
Concurrent trace records are checked by complete unique sequence population and
same-thread call order rather than inter-thread write arrival. Existing PID-reuse/
worker-exit safeguards and observer budgets remain intact.

## Isolated build and prospective run

build.sh uses the unchanged pinned amd64 image, network-none, Release settings
and installed SRT provider. New SDK install/bridge-socket-disposition and all three
ROS packages install/m3-socket-disposition-ros use separate build/install paths.
The messages package warns only that SDK/SRT CMake variables are unused there;
all packages build successfully. No old binary/install prefix is overwritten.
The one evidence-local runtime selector verifies new14 entries and recursively
verifies preserved shutdown13 and earlier candidates/provider. General campaign
adapters are unchanged; the SENSOR scenario parser merely admits this new prefix
while retaining its default. Private IPC4/--worker-ipc-v3 is unchanged.

Freezebc59e3d73dc0 and separate exact user authorization bind one new N0 session,
source/capture/typed accounting and shutdown tracing on both roles; the calibrated
native ARM64 observer targets only operator bridge/registered descendants. No
heavy check/build overlaps measurement. Permission/filter/image/sample/time
budgets and original child SIGINT waits remain unchanged.

## Observed result

Operator59/robot43 stage records pass sequence/drop/identity/thread/time and all
common/explicit socket gates. Robot reports all four final slots already invalid,
with zero locally traced closes. This positively establishes slot state at this
new run's final boundaries; it does not recover earlier close return values or
reclassify the previous missing-marker FAILs.

The operator's CONTROL/SENSOR data slots are already invalid at the final sweep
because its session-stop phase records their closes first. Its two listener
slots are still valid and then closed. All four traced operator srt_close calls
return0. Exact per-slot fd/result proof is in gate-report and raw stage JSONL;
no whole-process descriptor leak-freedom claim is made.

The observer lifecycle passes with27 nonempty successful kernel-stack reads,
zero unavailable reads, one contained post-signal sample and confirmed registered
worker absence after valid join evidence. Shared clocks/identity/capability/NNP/
seccomp readiness and bounded footer pass. ARM64 kernel frames under amd64
emulation are not application user frames or overhead equivalence.

The reused strict SENSOR window/accounting/capture checks pass:10.054288796s,
200.014147Hz IMU/50.028402Hz joints, zero source skips, six accounting balances0;
modeled published age maxima69ms/80ms. Source2514 vs observed2394 leaves120
samples accounted across existing upstream/admission/replacement/publication/
observer stages. This is latest-only bounded delivery, not lossless availability,
physical sensor age, general SRT/DDS comparison or N3 qualification.

All supervised children exit0 without force: operator215.842500ms, robot bridge
326.124084ms, source165.464791ms after signal completion. Original5s gates pass.
The underlying SENSOR adapter and final diagnostic assessment both PASS/driver0.
Original two-loss bridge hang remains unobserved/unknown; N3 stays8 PASS/1 FAIL.
No remaining campaign case is advanced or M3 acceptance inferred.

## Integrity and disposition

All lab/observer containers, network and output volume removed/absent; credential
deleted, no forced cleanup. Frozen source/input/helper/new14 binaries and old13/
provider/preserved chain match postflight. Every earlier raw index, including the
previous lifecycle-stage FAIL, remains unchanged.116 new closed raw files are
hash-indexed; public records include actual stages/dispositions/outcomes,
observer/child/ready/exec/policy, assessments and build/test/provenance manifests.
The one-shot output now exists and cannot be reused. No follow-on run is queued.
Historical FAILs stay intact; this PASS applies only to the new bounded healthy
shutdown diagnostic with its explicit trace contract.
