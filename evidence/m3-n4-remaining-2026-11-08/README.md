# Remaining bounded N4 development tests

Ten independently planned cases pass: four native deadline/query cases, three
15s ROS freshness directions, and three corrected real ROS crash/restart cases.
Two earlier crash-fixture cohorts remain FAILED at their first case with later
cases unexecuted. Their logs/plans are preserved; no passing case replaces them.
Production SDK/ROS C++/worker/provider binaries were unchanged. N5 has not run.

## Native deadline overruns and isolated QUERY recovery

Frozen source c70de04 extends the standalone fixture only, using existing barriers,
original5s command budget and20s test coordinator watchdog. A6s VM hold exceeds
both original sender and conservative receiver expiry before held work resumes.

| Held phase, both-direction cut | Durable outcome | Effects | SDK command handoffs |
| --- | --- | --- | --- |
| Receiver admission before commit |REJECTED/context_lost|0|1|
| Durable dispatch before execution start |REJECTED/context_lost|0|1|
| Atomic start before effect |EXPIRED/start_deadline|0|1|
| Result committed, direct final response withheld,2s hold |SUCCEEDED|1|1|

Context rejection takes priority over an expiry classification in the first two
cases after the connection changes; no expiry-specific decision is invented there.
All expired/invalid work remains unexecuted, with invalid result and generation0.
Both journals match original identity/hash/origin/state/result and preserve exact
sender ingress+5s, with earlier mapped receiver expiry. Closed proof, phase order,
restored qualification, zero-loss traces and bounded full shutdown pass.

The fourth case uses the existing test_withhold_final_status to suppress direct
terminal COMMAND reply while permitting QUERY replies. The committed100Hz/gen1
result is recovered by actual QUERY (queries_sent5), with one effect and no second
command handoff. Overrun cases observe8 queries each, not accepted-command replay.
No production clock, locks, deadlines or retry policy changed.

## Continuous ROS freshness across network interruption

Each fresh owned fixture produces IMU200Hz/joints50Hz for a nominal15s window.
Initial and final qualified stable checkpoints fence counters; a warm2s interval
precedes root100% loss, a2s VM hold and restored N0. Measured common guaranteed
cuts are2.563823876s both directions,2.478296876s operator→robot, and2.484646168s
robot→operator. All cut interfaces record actual drops with verified seed/loss.

| Direction cut | Actual IMU /joints Hz | Source produced | Typed observed | SDK-to-receiver gap | Max shared-VM ingress→observer |
| --- | --- | --- | --- | --- | --- |
| Both |200.001368 /50.016948|3764|2886|735|25.352125ms|
| Operator→robot |200.020185 /50.005046|3765|3634|0|23.417917ms|
| Robot→operator |200.004876 /50.017825|3764|2961|658|23.454333ms|

All cases meet1% cadence, exact source hashes/stamps/order, complete zero-drop
source/sender/receiver trace status and their fixed4000/20000 record allowances,
within unchanged hard10000/75000 limits. All six balances0, nonnegative loss terms,
empty stable queues, qualified same-owner final endpoints and matching peer sessions.
Missing observations are explicit, not lossless-delivery results:

| Aggregate term | Both | Operator→robot | Robot→operator |
| --- | --- | --- | --- |
| Upstream DDS |4|1|0|
| BUSY admission |4|4|12|
| Outbound replacement |133|125|133|
| SDK-to-receiver gap |735|0|658|
| Receive replacement |1|0|0|
| Observer DDS |1|1|0|
| All other terms |0|0|0|

Every observed callback is tied to an accepted original source/SDK/receiver
identity and its VM bridge-ingress lag is<=250ms. Both routes show many fresh
post-restore samples originating after restoration (at least455 per route in the
smallest case), alongside pre-cut progress. Robot egress cuts show no typed output
after the500ms settling allowance inside the guaranteed cut. Operator-only egress
does not itself cut the data path, so ongoing fresh delivery is valid.

Conservative bridge publication upper-age maxima (IMU/joints ns) are19982604 /
30356050,16744479 /29177878,15278040 /27483615, with reconciled route histograms.
These are software callback/publication checks on proven shared VM monotonic time,
not physical sensor age, independent packet capture or cross-host performance.

Context histories are retained rather than forbidding legitimate transitions.
SDK identities join original owner/session/route/origin/envelope and actual message
number; local generation counters are not assumed equal across peers. Inactive
zero-session admissions are only accepted by an explicit parser option for rejected
codes2/4; queued/SDK/receiver success remains strict. The N4 checker permits only
BUSY1 and obsolete4 rejection, counting both. The older validator's mistaken
obsolete2 mapping was corrected with a negative regression; stopped is2. This
changes analysis only; earlier passed finite cases had no obsolete inputs.

## Preserved restart-fixture failures and corrections

- Original c70de04 before case fails to regain a new qualified session within40s;
  new receiver prefix shows endpoint worker failure, but exact WorkerFault and
  old-worker exit were not recorded. Later effect/committed cases unexecuted.
- Source726752b explicitly closes live inspection connections (transaction context
  managers alone do not close SQLite), records state/worker faults and requires
  the old owned worker to exit or become zombie before restart. The new receiver
  becomes ready/clock-qualified with worker_fault0. That before case then FAILS
  during final live inspection with `database is locked`: production exclusive
  SQLite ownership correctly blocks a concurrent reader. Later cases unexecuted.
- Source24fdcf2 respects ownership: final audits after shutdown; whole-bridge
  crash snapshots after old-worker exit. For the effect fence, observe persistent
  effects1, stop the owned rate worker, verify its identity/stopped state, copy its
  stable DB/WAL to a private local directory and require DISPATCHING in that copy,
  then kill that same worker before result commit. Application recovery never runs
  on live state; original files are not modified by inspection. Source locks and
  production behavior stay intact. Final observations are saved before cleanup.

The initial failed startup's unique historical cause remains unproven. Explicit
closure removes a genuine observer lifetime defect; the next failure establishes
why active exclusive journals must not be inspected this way. Corrected results
are independent evidence, not repaired old verdicts or retries without a code fix.

## Corrected real ROS crash/restart outcomes

Each case starts a fresh bridge pair and an external simulator that stays alive
across receiver restart. Source publishing is disabled so effect/generation proof
is isolated from sensor cadence; simultaneous crash+sensor-load is not claimed.
One command requests200Hz/gen0->1, original5s budget, no subsequent Execute call.

| Crash position | Final command state | Persistent device effects | Result proof | Receiver owner/session |
| --- | --- | --- | --- | --- |
| Before admission, original SDK send blocked by cut |UNKNOWN/reconcile_required|0|Invalid, despite NOT_FOUND and elapsed expiry|Changed|
| After real effect, before result commit |UNKNOWN/context_lost|1|Invalid; old journal owner retained|Changed|
| After committed success |SUCCEEDED|1|Valid200Hz/gen1, old durable record retained|Changed|

Before case records SDK handoff1, effects0 and empty receiver journal at the crash
boundary. After reconnect it observes peer NOT_FOUND and remains UNKNOWN beyond
original expiry, never treating missing record as nonexecution or expiry proof.
Receiver stays empty and the persistent simulator stays generation/effects0.

Effect case observes external generation/effects1 while response is deliberately
delayed2500ms, then pauses the exact owned worker, snapshots committed DISPATCHING
and SIGKILLs it. The supervisor surfaces worker fault; the parent bridge stops
normally. Restart on the same journal recovers UNKNOWN with invalid result and
original owner metadata. The effect count remains1 through the observation window.
Observed device state is fixture ground truth, not a fabricated successful command
result without durable completion proof.

Committed case first obtains a valid success and persistent effect1, kills the
receiver bridge, then verifies that restart retains the old durable success with
no additional effect. This is committed-state retention; it does not by itself
isolate a lost reply. The native withheld-result case separately isolates QUERY
recovery. Refreshed ROS status RPCs may return cached final statuses locally; only
nonterminal refreshes necessarily emit network queries. No new Execute is issued.

All three observe statuses for10s after a new qualified session, retain exactly
one complete sender provider_sent observation, and preserve original sender5s
budget. Sender trace counts100/22/21 are complete and zero-drop. Every controlled
receiver incarnation's final trace was additionally rechecked offline as complete
(14;5/6;28 records respectively). Intentionally killed initial receiver incarnations
may lack footers and are labelled expected injected negatives, never called complete.
All surviving/restarted children stop cleanly, and owned namespaces/credentials
are removed. Original stopped worker PID/exit-or-zombie time is recorded before a
replacement is launched. No physical hardware, permanent-absence or automatic
reexecution conclusion is drawn from UNKNOWN or NOT_FOUND.

## Validation, provenance and next priority

239 host tests pass, including inactive-admission opt-in, correct enum mapping,
strict source/context/age/blackout/progress gates, overrun effect rejection,
explicit connection closure and exclusive-WAL snapshot behavior. The WAL regression
proves that an active exclusive owner rejects a live reader, a private copy sees
only committed state3 rather than an uncommitted result4, and original DB/WAL hashes
are unchanged. Standalone native fixture builds Release/Werror; syntax/diff pass.
No SDK/ROS C++/worker/provider source changes or rebuild; prior SDK70/ROS41 remain
last full validations, not new acceptance runs. Passing cases verify runtime hashes
before/after, independently re-inventoried after experiments. The standalone peer
has a new hash for its added QUERY-only phase; production binaries are unchanged.

Plans, original success/failure/skipped matrices, selected qdisc/VM/status/shutdown/
context/trace/typed hashes, closed-journal metadata and tests/build/runtime/local
artifact hashes are archived. Raw journals and stopped copies, detailed process/
clock/resource samples, full inspect/environment/core dumps and credentials are
excluded. Local hashes retain provenance. Source/sender/receiver trace populations
for freshness are3764/7384/2888,3765/7400/3635 and3764/7384/2961. No diagnostic
budget was enlarged or silently truncated.

The requested bounded N4 development gates now have passing evidence. N5 SRT
progress and DDS cold discovery can be investigated next, before returning to
remaining N3/comparison work. This is not full M3, long-duration combined-load,
DDS security/resource parity, cross-host/physical-age or hardware acceptance.
Historical missing-footer and other failed/skipped cohorts remain unchanged.
PR2 stays draft and Intrinsic/M4 is untouched. No N5 execution in this change.
