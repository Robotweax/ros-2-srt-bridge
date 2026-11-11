# N5 close-cause reproduction: no active reset observed

One preselected 300-second N5 diagnostic execution at 4a49595 used the tested
cause-event runtime fd0107e, label 1701, native v2 capture and command/recorder
diagnostics. Source and eight selected installed file inventories were frozen
before launch and verified afterward. There were no retries, replacements,
impairment changes or tuning. The no-reset outcome is retained without replacing
any earlier failed cohort or claiming a completed N5/M3 qualification.

| Diagnostic result | Observation |
| --- | --- |
| Active-window close/reset | **Not observed** |
| Command attempts / successes / effects | 133 / 133 / 133 |
| Unresolved / UNKNOWN / nonadmission | 0 / 0 / 0 |
| Skipped command slots | 17 |
| Complete trace records | Operator 417, robot incarnations 5 / 5 |
| Diagnostic / PCAP kernel losses | 0 / 0 |
| Source / published / observer samples | 75041 / 2327 / 2327 |
| Maximum publication-age upper bucket | IMU 162 ms, joint 159 ms |

All 133 common closed-journal records agree in the compared immutable/status
fields. Source conservation summaries and four cgroup phase windows replay
exactly. Source-to-publication deficits remain explicit and are not isolated WAN
loss or transport superiority. Age observations are conditional bridge-ingress
bounds under the existing shared-VM model, not physical sampling/delivery bounds.
All realtime packet windows remain withheld by the original clock checks. No
resource-cost or latency advantage follows from this single execution.

summary.json classifies close events only inside the actual command measurement
window. Setup and teardown actions remain in the original traces but are not
misclassified as a reproduction. The run and plan are unchanged. The initiating
cause of historical intent 15's live context loss remains unproven; its UNKNOWN
and all prior recorder/diagnostic failures remain retained.

## Controlled admission-before-commit peer-loss regression

A separate native test now reproduces the uncertainty pattern with a known fault.
It waits for the receiver journal admission_before_commit barrier after transport
receipt, stops that receiver, reconnects a new receiver epoch/session, and queries
the original intent. The sender retains UNKNOWN/reconcile_required, revision 0,
invalid result. Peer NOT_FOUND is observed without manufacturing nonexecution,
expiry or success. After the original 5000-ms budget, the intent remains uncertain.
Exactly one sender SDK handoff is recorded, with no replay or handler effect.
Control-link loss and same-owner UNKNOWN provenance remain trace-complete.

Both IPv4 and IPv6 command_endpoint CTests pass, 195 checks each. These include
the new admission-loss case and the existing normal/lifecycle, committed-result
recovery, running-handler uncertainty, timeout and bounded-shutdown cases.
The test uses the explicitly simulated native handler and an existing worker
barrier; no production hook or runtime behavior changed. This is admission-phase
fault coverage, not proof of the natural N5 initiator or complete N4/ROS/hardware
qualification. No new full SDK, ROS or host-Python suite rerun is claimed for this
test-only change; their previous results retain their original scope.

Raw packet/native-prefix/journal/clock/resource data stay local with hashes.
Closed-journal reads are immutable and before/after hashes are checked. Full
inspect/environment dumps and credentials are excluded. Source/binary constancy
was verified for the diagnostic before the later test-only commit. Archive
reanalysis does not modify the original verdicts or synthesize missing records.

Next: use a prospectively bounded diagnostic/fault plan to distinguish provider
connection loss from a local session/clock decision. The new cause events and
admission-loss regression provide that foundation. Preserve all historical
uncertainty; full N5/M3, remaining N3/N4, default DDS N5, age/clock/security and
controlled resource gates remain open. PR #2 stays draft; Intrinsic/M4 is untouched.
