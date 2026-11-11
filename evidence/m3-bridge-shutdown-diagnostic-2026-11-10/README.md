# Single prepared N0 bridge shutdown diagnostic — 2026-11-10

**FAIL at observer configuration validation; observer never started.**
Exactly one authorized prepared N0/seed1701/10s attempt ran. The source fence
covered10.053922838s, both roles reached their measurement result barriers, then
the observer isolation check rejected Docker's capability spelling. Execution
stopped there, without tuning, code/policy changes or retry. All29 remaining
campaign cases stay disabled; no two-loss-4211, command, expiry or replay.
M3 open, PR2 draft, M4 untouched; original N3 stays8 PASS/1 FAIL.

## First failure and scope

The prepared sidecar expects CapAdd exactly ['SYS_ADMIN']; Docker inspect returns
['CAP_SYS_ADMIN']. All other fields in that combined isolation check meet their
expected values: not privileged, root read-only, network-none, no user namespace
override, CapDrop ['ALL']. Normalizing the optional CAP_ prefix produces precisely
the intended single SYS_ADMIN capability. This is a literal validation bug, not
evidence of a broader grant or denied kernel-stack permission.

I missed this Docker normalization in the prepared bridge-specific gate. The
working synthetic observer calibration already normalizes capability names;
this separate sidecar check does not. No fix or fallback was applied during or
after this run. A future correction needs a regression control and new prospective
scope/freeze before another attempt; this record grants no retry.

The observer container was created and inspected, but no docker start command
was issued. There are no Python entry/exec/ready or kernel-stack records. The
secondary assessor reports missing operator-observer-ready.json; it is a
consequence of the earlier configuration rejection, not the first failed gate.
The original prepared freeze/helper/driver remain unchanged.

The host abort/release path then performs only required cleanup through the
unchanged stop_children helper. Operator bridge exits0/unforced in223.895250ms;
robot bridge exits0/unforced in326.048375ms and source in172.833417ms. All are
inside their original5s waits. Operator51/robot39 stage records have zero drops
and end at main_context_shutdown_end. Both bridge identity proofs attest all
capability sets including bounding zero and NNP1/Seccomp2. These are retained
cleanup observations, not a passing bridge-observer diagnostic or proof of the
original hang cause. No post-signal stacks or observer overhead claim exists.

Source/accounting/packet validation after observer arming was not reached. The
measurement barriers and closed captures do not establish a fully qualified
SENSOR window, zero-skip/cadence/age PASS, N3 closure or M3 acceptance. No later
gate is inferred PASS after the primary failure. No full test suite/build ran
during the attempt; the prepared475-test offline result retains its prior scope.

## Integrity and cleanup

Preparation source/input/helper/profile freeze,13 matched SDK/ROS entries and
preserved build chain match pre/postflight. All prior N3/calibration/observer raw
evidence indexes match. No SDK/ROS/native rebuild. The two lab containers, created
but unstarted observer, internal network and observer output volume are removed
and absent; credential deleted, all supervised children reaped without force.

PLAN/authorization/preflight bind the sole user-authorized execution. The original
preparation record remains disabled and immutable; separate authorization was
consumed by creating its one-shot output, so its driver refuses that output again.
result.json preserves the primary error, diagnostic-assessment the secondary
missing-ready error, and gate-report maps them explicitly. Public child/stage/
capability/policy/command records plus postflight document cleanup. The109 closed
raw artifacts, including exact logs/captures, remain locally hash-indexed.
