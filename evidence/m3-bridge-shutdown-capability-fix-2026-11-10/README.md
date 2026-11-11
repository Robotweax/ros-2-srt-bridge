# Capability-name correction and one N0 bridge diagnostic — 2026-11-10

**Capability validation fixed; overall diagnostic FAIL at observer lifecycle coverage.**
Three new regression controls and all478 Python tests pass. Exactly one new
frozen N0/seed1701/10s attempt ran, then stopped at the first failed gate. No
observer/timing/filter/capability fallback, tuning, extra attempt, two-loss-4211,
commands, expiry/replay or remaining campaign stage. All29 cases stay disabled;
M3 open, PR2 draft, M4 untouched. Original N3 remains8 PASS/1 FAIL/unknown cause.

## Narrow correction and prospective freeze

The new sidecar normalizes an optional CAP_ prefix in CapAdd, then still requires
exactly the SYS_ADMIN set. Missing/wrong/extra capabilities fail; all other
isolation checks are unchanged. Regression uses the exact Docker inspect record
from the prior failure, verifies no input mutation and confirms the other guards.
No production source, native binary, observer policy/image or budget changed.
The previous failed case, preparation scripts, freeze and raw records remain
immutable. This directory copies the prepared harness to preserve that history;
only capability validation and required path/provenance references change.

The new source/input freeze and separate user-authorized single-scope record bind
the attempt. All13 matched SDK/ROS entries/preserved build chain, exact calibrated
native observer helper/image/profile/runtime and retained raw indexes verify
before launch. No tests or builds overlap capture. Existing output is one-shot.

## Actual result and first failed gate

Capability/configuration validation passes. The native ARM64 observer starts and
emits entry/preexec_verified/exec_begin, verifies the registered bridge identity,
capability scope/NNP/seccomp and shared clock origin, and is ready before SIGINT.
It observes the operator bridge PID141 and plain journal-worker descendantPID157.
There are3 samples and28 nonempty successful kernel-stack reads, no denied reads,
no truncation or observation-budget exhaustion. Before signal:23 bridge threads
plus1 worker thread. One fully contained post-signal sample has4 successful bridge
stacks; the worker row is gone_or_reused. Final sample follows root reap, then
complete all_owned_processes_gone footer; observer exits0 without force.

The unchanged coverage assessor rejects any non-sampled registered process in
samples ending before the bridge reap. It therefore raises exactly
`live target observation incomplete` at the worker row in that post-signal sample.
The retained worker_join_end marker precedes it (34,558,644,098ns versus sample
begin34,697,387,390ns); the worker was previously identified as robotweax-journ.
This is consistent with ordinary worker exit during clean bridge teardown.
The collector deliberately combines disappeared and reused PID statuses, so no
unique PID-reuse or crash cause can be inferred from this row alone. Do not
silently waive/relabel the frozen gate or call this a complete diagnostic PASS.

Underlying SENSOR host adapter result is PASS; final diagnostic assessment is
FAIL and driver exits1. Later diagnostic stage-completeness checks are not reached.
These statuses remain separate. Operator bridge exits0/unforced221.450875ms,
robot bridge320.953167ms, source167.404875ms, all within original5s waits. This
healthy run does not reproduce the original two-loss shutdown failure or identify
its cause. Kernel stacks are ARM64 Linux frames of the amd64 processes under
emulation; no user-space/GDB or overhead-equivalence claim.

## Cleanup and disposition

All two lab containers plus observer, internal network and output volume are
removed/absent; credential deleted, all supervised children and observer reaped
without force. New source/input/helper freeze, matched13/preserved chain and all
prior raw indexes, including109 files of the preceding failed diagnostic, match
postflight. No SDK/ROS/native rebuild.116 closed local artifacts are hash-indexed.
Original/previous failures and synthetic observer PASS retain their scope.

PLAN/freeze/authorization, regression log, primary gate report, exact observer
JSONL/exec/ready/capability/policy/child/stage records and postflight preserve the
attempt. readiness.json is the prospective offline preparation snapshot; the
separate authorization enabled only this new output, which now exists and cannot
be reused. No source or gate edit followed the failure and no retry is queued.
Next prerequisite is a separately reviewed lifecycle rule for confirmed owned
worker exit versus PID reuse, grounded in these retained join/stack records.
