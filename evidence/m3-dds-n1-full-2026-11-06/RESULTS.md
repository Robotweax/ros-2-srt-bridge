# Full-duration DDS N1 results

Frozen-plan status: **passed**. Executed 3 of three planned
600-second cases. All planned duration/seed cases completed with execution/capture gates:
**true**. This describes default DDS N1 execution coverage,
not N1 age-gate qualification, complete M3 acceptance, or equivalence of age/security/transport costs.

Command totals: 892 attempts, 890 confirmed successes,
890 effects, 2 observed expiries
(2 receiver expiry records without dispatch),
0 UNKNOWN, 0 unresolved,
0 not admitted, 0 rejected, 0 failed
and 8 skipped cadence slots.
These populations remain separate. Skipped slots are not silently retried.
A terminal expiry is not a success. Missing/unknown state is not nonexecution.

| Seed | Attempts | Successes | Effects | Expired | Expired without dispatch | UNKNOWN | Unresolved | Not admitted | Skipped slots | Max terminal observation (ms) | History polls omitted |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1701 | 297 | 296 | 296 | 1 | 1 | 0 | 0 | 0 | 3 | 5350.575 | 0 |
| 2903 | 297 | 296 | 296 | 1 | 1 | 0 | 0 | 0 | 3 | 5316.245 | 0 |
| 4211 | 298 | 298 | 298 | 0 | 0 | 0 | 0 | 0 | 2 | 2473.593 | 0 |

Both expiries are receiver-backed revision 1, invalid result and zero dispatch;
later distinct intents continue without advancing generation for those expiries.
All six closed journals agree on immutable commands and authoritative terminal
results. No sender-only/receiver-only/status divergence is observed.

Terminal observation spans driver invocation to observed terminal status, including
service/middleware/reconciliation waits and the bounded post-cutoff result drain.
It is not handler start/execution or network transit latency. Per-state/reason
p50/p95/p99/maxima and omitted/uncertain populations are in command-outcomes.json
and the original manifests. Timelines split matching original-owner successes
only, using journal timestamps before mutations/commits. Recovered/missing/unknown
records retain uncertainty. No deadline/freshness or replay policy was changed.

## Sensor populations and age qualification

Source-fenced counters, callbacks and acceptance remain distinct. A callback
deficit includes source/middleware/queue/network/observer stages, not isolated WAN
loss. Age estimates are shared-VM realtime observations, not conservative SRT
clock intervals. Unqualified age distributions must not be interpreted as age
bounds. Per-route histograms, stale/invalid/clock-rejected/missing counts remain
available, including unqualified populations.

| Seed | Source-enabled seconds | Produced | Received callbacks | Actual IMU/joints Hz | Age estimates qualified |
| --- | ---: | ---: | ---: | --- | --- |
| 1701 | 600.115900 | 150010 | 112123 | 199.968/50.000 | false |
| 2903 | 600.118402 | 150024 | 112928 | 199.991/50.000 | true |
| 4211 | 600.132039 | 150026 | 111710 | 199.988/50.001 | true |

| Seed | Clock steps | Max observed offset step (ms) | Max offset deviation (ms) |
| --- | ---: | ---: | ---: |
| 1701 | 4 | 25.965389 | 34.616970 |
| 2903 | 0 | 0.924931 | 1.597276 |
| 4211 | 0 | 0.804555 | 1.271829 |

| Seed | Route | Accepted | Stale | Invalid | Clock rejected | Missing before callback |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| 1701 | imu | 64687 | 0 | 0 | 17809 | 37508 |
| 1701 | joints | 23224 | 0 | 0 | 6403 | 379 |
| 2903 | imu | 83350 | 0 | 0 | 0 | 36668 |
| 2903 | joints | 29578 | 0 | 0 | 0 | 428 |
| 4211 | imu | 82105 | 0 | 0 | 0 | 37914 |
| 4211 | joints | 29605 | 0 | 0 | 0 | 402 |

## Integrity and scope

6 closed journals pass SQLite integrity and immutable-command checks;
receiver successes agree with effect counts. Sender-only, receiver-only and status
divergences, if any, remain explicit in journal-audits.json/command-outcomes.json.
Sources match the frozen 161-file inventory; eight selected
installed binary/SDK hashes and installed demo Python bytes remain constant.
The 56 compiled production sources are unchanged from e3c5c70.
No new ROS GTest/full M2 build is claimed; the previously passing 83-test host suite
is unchanged rather than claimed as newly expanded coverage.

For passed cases, strict PCAP zero-drop/file-integrity gates and native v2
reserve/copy/coverage gates passed. 12 cgroup endpoint/phase windows
replay exactly from archived projections. coverage.json retains native offload
interpretation and PCAP population reconciliation separately. No physical wire,
checksum, packet-delivery or isolated resource-overhead qualification follows.
All six PCAP populations reconcile here with zero kernel drops and matching
captured/file counts. Every realtime packet window is withheld by the clock
model; native coverage remains independent. This does not prove universal
capture-population completeness or physical delivery. See pcap-populations.json.
Source/callback populations, terminal waits and the shared emulated host prevent
an SRT/DDS performance-advantage claim. Seeded netem does not make independently
started executions deterministic at the application level.

Raw PCAPs, native prefixes, clocks, samplers and journals remain local with hashes.
The preserved plan has no retries or removed cases. The N1/N2 duration/seed cohorts and the unresolved age/clock gates are summarized
separately. Long v2 N5, deterministic N3, N4 phase barriers, other devices/offload
paths, controlled resources and semantic/security alignment remain open.
Intrinsic/M4 is unchanged; PR #2 remains draft.

## N1/N2 duration/seed execution coverage

execution-matrix.json records all four separate cohorts: SRT N1/N2 and default
DDS N1/N2, three seeds and at least 600 source-enabled seconds each. This closes
the duration/seed execution item only. Current DDS N1 seed 1701 age estimates fail
after four observed clock steps, maximum 25.965389 ms, with 24,212 clock-rejected
callbacks. The earlier DDS N2 seed-1701 age failure is retained independently.
The two qualified current seeds do not replace either failed qualification.
Realtime packet-window clocks remain unqualified, and age origins, crypto,
pacing, capture retention and host conditions differ across cohorts. No combined
performance-advantage claim or full M3 acceptance is supported.
