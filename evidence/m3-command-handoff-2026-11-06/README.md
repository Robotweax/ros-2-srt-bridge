# Command handoff diagnosis and soft-clock fix

The separate traced 90-second N5 development case at 381dfa8 identifies an
unsent command discarded when envelope creation returned clock_unqualified.
The transport had consumed its volatile mailbox admission, but never handed
that command to the SDK. This case explains a newly observed failure path;
historical intents 105 and 3 remain uncertain without equivalent traces.

## Retained pre-fix result

The original run.json remains **failed**. It records ten successful commands /
effects, one unresolved intent (11), 34 skipped slots and zero PCAP kernel drops.
The last driver poll for intent 11 observes LOCAL_QUEUED/revision 0, with peer
NOT_FOUND and no valid terminal result. Its source-window cutoff is
609893441734 ns; envelope rejection was observed at 547851173247 ns.
A later teardown session invalidation is requested at 621291205864 ns and
completes at 621298984656 ns, before coordinator stop at 621798999489 ns.
The closed sender journal retains UNKNOWN/reconcile-required for 11, and the
receiver has no record. These timestamps distinguish the recorded live polls
from subsequent teardown observations; they are not durable-commit or physical
delivery timestamps. No expiry, success, safe replay or nonexecution proof is
invented. Ten common terminal records agree.

The first validator incorrectly required exactly two bridge log files. The
scenario deliberately replaces the robot bridge during setup, producing three
incarnations. All three actual traces are complete (43/4/4 events, zero trace
drops). The corrected read-only trace-reanalysis.json retains each incarnation
without changing the original failed manifest. A host regression requires all
incarnations to be validated and fails on a missing role or incomplete trace.

## Fix and regression

899a6eb retains the original unsent command in a reserved transport ingress
slot while only the soft clock condition is unqualified. The slot counts toward
the existing total 64 / command 56 limits and preserves FIFO order. Proof,
context, origin and deadline stay unchanged and are checked on subsequent
attempts. Clock probes and owner I/O continue. Expiry, revocation, context loss
and other envelope errors still fail closed. This does not re-admit a command,
renew its budget, or resend an SDK-accepted command.

The native regression uses a 150-ms clock-probe lifetime to produce a controlled
expiry interval. The old transport fails with "command was discarded instead of
waiting for clock". With the fix, IPv4 and IPv6 tests observe deferral, the
reserved ingress charge, rejection of ticket reuse, one later SDK handoff and
unchanged original source time / 5000-ms budget. Revoking a second deferred
command prevents peer receipt and SDK handoff even after clock recovery.
check_regression.py records the old-transport negative test; fixed-build-tests.log
contains the full final suite. The negative test deliberately used the old
transport implementation with the regression fixture, restoring the edited
source afterward; it is not an N5 qualification run.

## Separate post-fix result

| 90-second N5 development case | Successes/effects | Unresolved driver / closed sender UNKNOWN | Skipped | Soft-clock deferrals | SDK accepts | PCAP kernel drops |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Pre-fix 381dfa8 | 10 | 1 / 1 | 34 | 0 (one envelope discarded) | 10 | 0 / 0 |
| Post-fix 899a6eb | 32 | 0 / 0 | 13 | 2 | 32 | 0 / 0 |

Both post-fix deferred intents complete successfully. All three post-fix traces
are complete (108/4/4 records), with zero diagnostic drops. All 32 common journal
records agree; device generation/effects reaches 32. Original source/binary
inventories are frozen before each case, with separate post-fix execution
binding and final selected-binary recheck. Capture mode, snapshots, buffer and
retention are unchanged. Source manifests match their named commits byte-for-byte.
This is functional development evidence with changed compiled runtime and
observer/logging workload, not a performance comparison or a replacement for
the failed full SRT N5 qualification cohort.

Historical closed-journal owner checks use immutable read-only SQLite reads and
before/after hashes. Intents 105 and 3 match their operator process epochs in the
recorded checkpoints; that alone does not establish an exact transition or
exclude all recovery paths. Checkpoint sender/receiver labels describe sensor
direction: operator is sensor receiver and command sender. The native recovery
control separately observes an UNKNOWN entry retaining its original owner epoch
under a new coordinator epoch without replay.

## Validation and limits

- 68 native/SDK CTests pass, including bounded trace overflow/concurrency,
  normal/shutdown/recovery provenance, clock deferral and revoked-pending controls.
- 36 ROS-reported tests pass (32 actual GTests plus wrappers).
- All 92 host Python tests pass, including trace loss, truncation, concurrent
  sequence ordering and multi-incarnation coverage.
- No full new M2 acceptance run is claimed. SRT wire, worker IPC, receiver start
  fencing, deadline, lease and no-replay policy remain unchanged. Public config
  layout changed for tracing; consumers were rebuilt.

Command diagnostics are optional, bounded and observational. Sequence order
across producers is not causal order. SDK acceptance is not peer delivery.
Unavailable /proc I/O remains explicit, and sampled state/counters do not prove
a recorder root cause. Raw packets/native prefixes/journals/clocks remain local
with hashes; original manifests and logs are preserved, with no full inspect or
environment dumps or credentials. Reader validation never mutates journals.

Full SRT N5, original recorder failure, historical uncertainty, default DDS N5,
N3/N4 and remaining age/clock/security/resource gates remain open. Keep PR #2
draft; M3 is incomplete and Intrinsic/M4 untouched.
