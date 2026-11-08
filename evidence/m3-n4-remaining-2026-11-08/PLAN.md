# Remaining N4 development gates: deadlines, ROS freshness and restart uncertainty

After236 host tests, syntax/diff checks and the standalone native fixture's
Release/Werror build pass, freeze source/plan. Run these three independent suites
exactly once in the listed order. Each suite stops at its first unexpected failure
and retains the original verdict; later cases in that suite stay unexecuted.
Independent remaining N4 suites may still run once to investigate their separate
gates, but no passing suite replaces a failure. No retries or N5 work under this
plan; fixes/re-executions need a separately frozen diagnostic plan.

1. `python3 tools/m3_n4.py --output .local/m3-n4-remaining/native --remaining-native`
2. `python3 tools/m3_n4_ros.py --output .local/m3-n4-remaining/freshness`
3. `python3 tools/m3_n4_ros.py --output .local/m3-n4-remaining/crashes --crashes`

Pinned existing Linux amd64 image, owned internal Docker peers/namespaces, separate
ROS domains/LOCALHOST, common boot/zero-time-namespace proof and explicit permanent
neighbors. No production SDK/ROS C++/provider/worker/API/scheduling/retry policy
change or rebuild. The standalone native fixture adds only a query-recovery phase.
Previous SDK70/ROS41 remain last full validation, not new executions. Host-only
validation now uses the actual SubmitResult::obsolete enum4 (stopped is2); prior
passed runs had no obsolete inputs. Existing strict trace parser defaults stay
unchanged. New opt-in permits a zero session only for explicitly rejected inactive
admissions (stopped2/obsolete4), never queued/SDK/receiver success; observations
remain rejected and counted, not accepted context proof.

## Native deadline and withheld-result suite

Exactly four fresh both-direction cases, in order: admission6s hold, durable
dispatch-before-start6s hold, atomic-start-before-effect6s hold, then query-only
result recovery with2s hold. Existing worker phase hooks and owned PID/start-tick/
argv/stopped-state guard; same original command100Hz/gen0->1,5s sender budget,
conservatively shorter receiver expiry,20s test coordinator watchdog. All previous
native context/journal/hash/one-handoff/phase/restored-clock/stop/trace gates stay.

For6s cases guarantee measured cut>=6s and resume beyond ORIGINAL sender expiry;
require authoritative EXPIRED or context-loss REJECTED with invalid result,
zero effects/generation change and no SDK-accepted-command replay. Context rejection
may precede the expiry classification after a session change; do not invent an
expiry-specific decision where rejection has priority. Before-effect work cannot
succeed after its receiver deadline. For query phase, existing test_withhold_final_
status suppresses direct final COMMAND reply while QUERY replies remain functional.
Durable SUCCEEDED must be recovered through actual queries, one effect/handoff,
no false outcome or extended budget. No production test control is added.

## ROS sensor freshness suite

Three fresh15s continuous200Hz IMU/50Hz joints windows, directions both,
operator-to-robot and robot-to-operator. Source starts disabled, arm after qualified
stable empty checkpoints, warm2s on VM, install100% root loss/readback, VM hold2s,
measure guaranteed common cut>=2s, restore/readback N0, source remains active to
its original15s pause fence. No source-rate/command changes. Context/session/
generation transitions during outage are expected and retained; same node owners
and cumulative counters must remain valid and final endpoints qualified.

Require actual source rates within1%, fence duration15..16s, at most4000 source
and20000 sender diagnostic records (retry/error observations retained separately),
unchanged hard capacities10000 source/75000 sample traces. Complete statuses,
zero diagnostic drops/exhaustion, typed exact original source hashes/stamps/order,
all six balances0 and nonnegative stages at stable empty checkpoints. Rejected
BUSY/obsolete inputs and SDK errors are explicit, not successes or wire-loss proof.
Join source/admission/SDK/receiver by original owner/session/route/origin/envelope;
local generation counters may differ across peers after reconnect and are not
mistaken for shared identities. No duplicate SDK source/receiver decision or typed
output without accepted source. Actual peer checkpoint sessions must agree.

All bridge publication upper-age maxima<=250ms with histogram populations matching
publications. On the proven common VM, every observed callback's original bridge-
ingress lag must also be0..250ms (includes local observer delay, not physical
sensor age). Both routes require>=5 observed samples before cut and>=5 fresh
post-restore samples whose source ingress follows restoration. With robot egress
cut, no typed output after a500ms settling allowance during the guaranteed cut;
with operator-only egress cut the data path is not itself cut, so fresh ongoing
data is allowed. Counter losses/context changes stay explicit. This is software
freshness with full local metadata, not independent packet/FEC/physical-wire
capture or cross-host timing/resource acceptance. Controlled final child exit0
and complete final source/sample statuses required; no planned crashes here.

## ROS crash/restart suite

Fresh real bridge pairs and external simulator per case, source publishing disabled
so generation/effect state is isolated from sensor cadence. One command200Hz/
generation0->1 with original5s budget, no subsequent Execute retry. Same device
process and receiver journal persist across receiver restart; receiver process
owner and control session must change. Three ordered cases:

- before: cut both directions BEFORE submission; verify sender SDK handoff1,
  external effects0 and live read-only receiver journal empty. Deliberately kill
  receiver bridge(-9), relaunch same journal and restore network. Sender must
  remain UNKNOWN/reconcile_required with invalid result despite peer NOT_FOUND,
  including observations beyond original expiry; receiver remains no-entry and
  external effect/generation0. Absence is never promoted to expiry/nonexecution.
- effect: simulator applies the command and delays its response2500ms. Observe
  persistent effects1 and receiver DISPATCHING before deliberately SIGKILLing only
  the owned ROS rate worker. Require surfaced worker fault; stop its parent bridge
  cleanly, relaunch receiver on same journal, reconnect. Recovered UNKNOWN with
  invalid result must remain UNKNOWN, original receiver journal owner retained,
  external effect/generation stays1. Observed device effect is fixture ground truth,
  not a fabricated command success without durable result.
- committed: verify original SUCCEEDED/result and receiver committed state before
  deliberately killing receiver bridge. Restart same journal/device, reconnect;
  retain matching durable SUCCEEDED, external effect1 and sender handoff1.

Observe refreshed statuses for10s after new qualification, always QUERY-only.
Sender final command trace must be complete/zero-drop and contain exactly one
provider_sent for original ID. Expected killed receiver incarnation may lack its
footer and is explicitly recorded as injected negative, never called complete;
all surviving/restarted children must shut down normally. Core dumps/credentials
are not archived. Closed original journal proof/hashes, initial vs new owner/
session, expected crash events and independent device snapshots are retained.
No actual hardware, cryptographic comparison or full M3/N4 acceptance implied.

Archive plans, original suite/case verdicts and failure logs, metadata/hash/status/
clock/qdisc/shutdown/crash and closed-journal extracts, build/tests and runtime
hashes before/after. Raw journals/resources/traces containing payloads, full
inspect/environment/core dumps and credentials excluded; hashes retained. Remove
all owned networks/containers/passphrases, preserve all previous failed/skipped
cohorts. Remaining issues stay open if any gate fails; do not move to N5 prematurely.
