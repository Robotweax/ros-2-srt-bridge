# SRT N5 frozen-plan outcome: failed

The plan executed seed 1701 (passed) and seed 2903 (failed), then stopped.
Seed 4211 was not executed. No case is replaced and no capture gate is relaxed.

| Seed | Overall verdict | Attempts | Confirmed successes/effects | Unresolved driver intent | Sender journal UNKNOWN | Skipped slots | Max terminal observation (ms) |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1701 | passed | 131 | 131 | 0 | 0 | 19 | 3666.526 |
| 2903 | failed | 105 | 104 | 1 | 1 | 45 | 5376.374 |

The failed run completed its application source window and six counter balances,
but PCAP lost 2672 robot / 2637 operator kernel records. Written files match
reported captured counts; the zero-drop gate correctly rejects the case. Native
recorders report no reserve/copy loss and independently cover both phases. This
cannot rescue the failed overall capture qualification.

Multiset analysis uniquely identifies every missing PCAP record in the native
IPv4 UDP population, exactly matching the kernel-drop counts. Three late-window
clusters are retained in capture-gap.json. The largest missing clusters span
about 2.7 and 3.1 seconds. Endpoint-sampler gaps do not establish a global pause;
no scheduler/storage or unique root cause is attributed. Existing full-snapshot
TPACKET_V2 fixed-slot capacity remains finite; no buffer/dispatch/tuning change
or hidden retry is made in response to this failure.

Intent 105 remains pending in the driver and UNKNOWN/reconcile-required, revision
0, invalid result in the sender journal. The receiver has no record for that ID;
104 common successful records agree and the final observed device generation/
effects are 104. Missing/NOT_FOUND is not nonexecution, so no expiry, success or
safe replay is invented. The stored reconcile-required state retains uncertainty even though transport
readiness later returns. Begin/end checkpoint session IDs and generations match;
these artifacts do not establish a session-ID rotation or a unique cause for the
transition to UNKNOWN.

Competitor offered-load and liveness gates pass for both executions. Their
process observation and final UDP summaries do not prove matched-window delivery.
All source summaries and eight cgroup endpoint/phase windows replay exactly,
including the failed case's application/counter data; this does not change its
failed recorder verdict. All 161 sources/installed hashes and Python bytes match
the SRT frozen plan after the SRT-only competitor-gate commit. No compiled
bridge/SDK/wire/IPC or command policy changes occur. The separate expected
competitor-stop fault is development coverage, not a positive case.

Paced DDS N5 has a separate completed three-repetition cohort. Default DDS N5
startup, full SRT N5 acceptance, remaining age/clock/model/security alignment,
deterministic N3 and N4 command-phase barriers remain open. Raw packets/prefixes,
journals/clocks remain local with hashes; no full inspect/env dumps are published.
