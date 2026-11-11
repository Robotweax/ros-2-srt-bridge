# Independent-lane N5 cohort: failed command-outcome gate

A fresh frozen plan at 649b4ce used the independent trace lanes from dc4131c /
0a1c1b0 and command clock-deferral fix 899a6eb. Three 300-s SRT N5 cases were
planned, labels 1701/2903/4211, with command/recorder diagnostics and native v2
capture enabled. Immutable image reference, common VM/time-namespace proof,
168 source files, eight selected installed files and installed-script bytes were
fixed before execution. No stochastic impairment, retries, replacement or tuning.
Labels are repetitions, not independent random-loss samples.

**The first case failed. The second and third were not executed.**

| Executed label | Source-enabled duration | Confirmed successes/effects | Unresolved / sender UNKNOWN | Skipped slots | Trace loss | PCAP kernel drops |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1701 | At least 300 s | 14 / 14 | 1 / 1 | 135 | 0 | 0 / 0 |

The original run.json says passed under development semantics, which permit
unresolved commands; the stricter, frozen cohort gate correctly rejects it.
Both original verdicts remain unchanged. The operator trace retains all 1496
attempted records; robot incarnations retain 4 / 7, with no loss. No missing
record is reconstructed and no gate is waived.

## Observed incident

Intent 15 was handed to the SDK at about 34.039 s after the measurement marker.
Robot session change/invalidation appears at 37.517/37.519 s; operator session
change/invalidation at 42.470 s, completed at 42.478 s. The first sender UNKNOWN
observation is at 43.305 s and its stored owner epoch matches the observing owner.
This is live-window context loss, not merely teardown. incident.json retains
exact monotonic observations and the final driver status. Cross-owner sequence
order is not causal order, and timestamps are not fsync or physical delivery times.

Fourteen common successful journal records agree, including result rate and
generation. Intent 15 remains sender UNKNOWN/reconcile-required, revision 0,
invalid result and no receiver record. Device generation/effects remains 14.
Absence/NOT_FOUND does not prove nonexecution; no expiry, success or replay is
invented. Existing trace points identify invalidation but do not record the
initiating socket/session-close cause. No unique cause is attributed.

Packet Captured/Filter/File populations reconcile at 150432 per endpoint, zero
kernel drops. Native reserve/copy losses are zero and both phases independently
qualify. Six source-counter balances and four cgroup windows reproduce exactly.
Source produced 74987 samples; bridge published 11864, observer received 11863.
These stage deficits are not isolated WAN loss. The maximum measured publication
age upper bucket is 238 ms within the unchanged 250-ms gate under the shared-VM
clock model; realtime packet windows remain withheld. No transport superiority,
physical delivery, isolated cost or realtime guarantee follows.

The shaping fixture remains 512-kbit/s root TBF per direction, burst 4096,
requested limit 32768 and child netem queue 16, with base/base+1 seed labels and
no random delay/loss. Pinned JSON expresses TBF lat=448000 rather than an explicit
limit field. Whole-run competitor offer/liveness checks pass; they do not prove
matched-window delivery. Raw captures/native prefixes, journals and clocks stay
local with hashes. Full inspect/environment dumps and credentials are excluded.
Selected source/binary/script constancy was checked before the subsequent cause-
observation patch; source manifests match the named Git commit byte-for-byte.

## Cause-observation patch and validation

The next opt-in schema adds session_action (30): SessionError plus close-control /
close-sensor / flush-samples bits 1/2/4; and link_lost (31): CONTROL/SENSOR channel
plus reason-specific socket state, security timeout, epoll flags, receive/send
provider error or wire-decode error. transport_stopping retains TransportFault.
Only closing session actions are traced, avoiding per-sample soft-clock noise.
No producer I/O, callback or policy decision is introduced; 128-event owner lanes
remain bounded with unchanged loss/completeness gates. The detail field grows
record layout, so consumers were rebuilt; event-count capacity remains 256.
Wire, worker IPC, journal, command/deadline/lease/start fencing and replay are
unchanged. These fields cannot retroactively identify this case's missing cause.

Five focused native/SDK tests pass, including controlled peer shutdown on IPv4/
IPv6 with a control-link cause and session-close action before receiver teardown.
All 93 host Python tests pass, including cause-field validation and older trace
compatibility. 36 ROS-reported tests pass (32 GTests plus wrappers). No fresh full
68-test SDK/M2 acceptance run is claimed. Separate cause-trace/ records retain a
15-s N0 smoke: eight successes/effects, complete 42/5/5-record traces, zero trace
or PCAP drops, and new cause fields exercised by setup/shutdown. This smoke is
not an N5 retry or qualification replacement.

Next: reproduce the live N5 reset with cause-specific observations and diagnose
its initiator before another full qualification cohort. Retain all historical
UNKNOWNs and recorder failures. N3/N4, default DDS N5 and age/clock/security/
resource gates remain open. M3 is incomplete, PR #2 stays draft, and Intrinsic/M4
is untouched.
