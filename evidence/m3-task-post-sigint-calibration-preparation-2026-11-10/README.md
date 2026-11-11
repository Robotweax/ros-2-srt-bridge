# Bounded native post-SIGINT assessment calibration — prepared only

Execution is disabled. This preparation authorizes no live run and creates no
grant. Exactly one future native observer readiness check and one controlled
Python parent/worker fixture are planned. All 38 campaign IDs stay disabled;
N1/2903's original failure and 1 PASS / 1 FAIL / 7 NOT EXECUTED remain immutable.
No tuning, retries, SDK/ROS/SRT workload, native build or campaign resumption.
M3 stays open, PR2 draft and Intrinsic M4 untouched.

## Predeclared protocol and gates

1. Run one observer `--self-check` on the unchanged pinned native ARM64 image,
   with the exact collector, activation, role permissions and filter. Any failure
   leaves the controlled fixture not executed. No target in this readiness step.
2. Start one controlled Python parent/worker fixture on the unchanged pinned
   amd64 image. Register parent PID/start_ticks and worker TID/start_ticks. Start
   the independent native observer only in that exact owned target PID namespace.
3. Require at least two schema-valid nonempty worker stack samples before SIGINT.
   Then issue one exact identity-bound signal authority to the capability-zero
   supervisor. The unchanged `stop_children` helper sends SIGINT and retains its
   original five-second child wait. No second signal/restart or deadline extension.
4. The child handles SIGINT without exiting. A supervisor wait-entry witness is
   written only after the helper has recorded `signal_end_ns`. The child records
   its handler observation independently. Require at least two nonempty matching
   worker stack samples wholly after both timestamps before authorizing release.
5. Release/join that worker, keeping the parent alive. Require one supported
   task-absence observation, with matching previous/current task identity as
   applicable, whose entire bracket follows controlled join and SIGINT completion.
   Check raw records with the exact reviewed per-thread assessment candidate.
6. Only then issue an identity-bound exit acknowledgement. Parent exits normally;
   supervisor must report exit 0 / unforced / within the original five-second
   signal-to-reap bound. Observer stops and exports a completed bounded capture.
   Apply the exact prospective lifecycle adapter to the complete raw capture;
   retain separate raw stack counts, observed absence and zero confirmed task exits.

Every gate is fail closed. The host requires two pre-signal and two post-signal
live worker samples, then exactly one supported task disappearance in the final
lifecycle proof, no missing worker-process shortcut and no descendant processes.
A root process missing only after supervisor reap remains governed by the
candidate's original root/reap rule; it is not interpreted as a missing task.
The old N1 capture has no schema1 metadata and remains refused. Its frozen
assessor still reproduces `live target kernel stack unavailable`.

## Bounds and immutable components

Collector SHA256:
`6deab3c5e83e48b7c33dbbb4613c361469d9b62aa1bea86db0c1a8012cfae72e`.
The copied `task_assessment.py` and `lifecycle.py` are byte-identical to
`evidence/m3-task-metadata-assessment-2026-11-10/`. Host-only private bindings check
those bytes against the original and isolate both generic module names. Freeze
inputs bind both originals and copies, binding code and all driver/fixture bytes.
No frozen campaign assessor/driver, collector, filter, SDK or ROS source changes.

Observer: pinned native ARM64 image, SYS_ADMIN only, NNP, unchanged default-deny
filter SHA256 `d6f372b978e568045e95c6bc7ced28aa4be40607b03b21732ee289ece5347d08`,
read-only root and bundle, network none. Target/supervisor: pinned amd64 image,
capabilities zero, NNP/default seccomp, read-only root, network none. Exact owned
output volume and original 16 MiB tmpfs only. No Docker socket, host procfs/PID
namespace, debugger, SDK/repository mount, permission expansion or rebuild.

The nine-file native bundle contains the unchanged collector/observer entry,
new target/controller, unchanged stop/filter helpers and unchanged policy/
architecture plus activation binding. All files are read-only (444), directory
555. Assessment candidates run on the host, not inside the target or observer.

Unchanged observer limits: 8 processes, 64 tasks/process, at most 65 directory
entries examined, 512 previous-sample identities, 16 KiB/read, 48 samples at
0.25 seconds / 12 seconds. One attempt per stack. Pre-signal host phase retains
its six-second bound. The new post-signal host phase has a three-second deadline;
child control-file phase has a four-second deadline. The original five-second
owned-child wait remains unchanged. Snapshot cap is 8 MiB; Docker/metadata commands
retain 20-second caps and all readiness/startup/cleanup handshakes are finite.
These bound separate operations and phases, not an overall wall-clock guarantee.
Failure to meet the fixed bounds stops and retains failure; no tuning or retries.
Prefix footers derived for incremental validation are host-only calculations,
never replacements for the native final footer or readable-stack observations.

## Scope of qualification

If later explicitly authorized, this can qualify access and metadata/lifecycle
assessment for one controlled native post-SIGINT disappearance while the parent
remains alive. It does not force an exit between enumeration and first stat,
prove all unseen TID reuse impossible, establish an exact exit cause, qualify
SDK/ROS/SRT timing or observer overhead, change journal outcomes, reclassify
N1/2903, resume later cases or close M3. Ground-truth fixture join and synthetic
stages are distinct from SDK journal-worker process/join stages.

## Offline validation and execution interlock

33 preparation tests PASS using temporary procfs, actual candidate records,
modeled Docker commands and one ordinary unit-test thread with mocked signal/
native-ID boundaries. Fresh interpreter bundle imports and actual host import
order are tested. Coverage includes strict grants/old-grant refusal, one-shot
output, readiness failure before target, pre/post/absence gate failures before
release/exit, foreign PID namespace, unchanged five-second wait witness ordering,
clock/identity/access/population/stage failures, exact candidate bytes and private
import binding. One initial offline fixture-control test imported the generic
ROS collector; its model now explicitly selects the temporary-procfs candidate,
matching the existing actual-fixture test. Its original failure log is retained;
no native attempt or frozen artifact was involved.

The unchanged candidate's 42 assessment, 28 collector and 511 existing passing
logs are copied byte-for-byte, not new native execution credit. Frozen source,
matched builds/full chain/native87, all prior raw/public indexes, calibration
captures and original failure are verified. Preparation uses only read-only
runtime/image inventories and creates local preparation/bundle files; it starts
no containers and performs no live procfs collection. Freeze records a unique
absent output/prefix, all disabled IDs and a distinct post-SIGINT scope.
`run.py` refuses missing/wrong/old grants, changed inputs and existing outputs;
no subset/resume/retry option exists. No grant or command is queued here.

Preparation initially stopped before freeze/bundle creation because unrelated CI
container codex-pr77-ci-20261110 was running. The initial blocker is retained.
Preparation now records the read-only active-container inventory; no container is
stopped or altered. Future `run.verify` still refuses any live container before
creation, as an explicit offline regression verifies. Preparation is possible on
a busy host; this is not an execution-quiescence waiver or native retry.
