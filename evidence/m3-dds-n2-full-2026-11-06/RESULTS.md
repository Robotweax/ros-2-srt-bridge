# Full-duration DDS N2 results

Frozen-plan status: **passed**. Executed 3 of three planned
600-second cases. All planned duration/seed cases completed with execution/capture gates:
**true**. This describes default DDS N2 execution coverage,
not N2 age-gate qualification, complete M3 acceptance, SRT N2, or equivalence of age/security/transport costs.

Command totals: 843 attempts, 830 confirmed successes,
830 effects, 12 observed expiries
(12 receiver expiry records without dispatch),
0 UNKNOWN, 0 unresolved,
1 not admitted and 57 skipped cadence slots.
These populations remain separate. Skipped slots are not silently retried.
Seed 4211 intent 268 received BUSY (submission 1), was not queued, and has
no entry in either closed journal. The explicit admission response and send
counters remain separate from generic journal absence; no absence-only
nonexecution inference is made. A later distinct intent proceeds at the same
expected generation. See admission-rejections.json and generation-proofs.json.
A terminal expiry is not a success. Missing/unknown state is not nonexecution.

| Seed | Attempts | Successes | Effects | Expired | Expired without dispatch | UNKNOWN | Unresolved | Not admitted | Skipped slots | Max terminal observation (ms) | History polls omitted |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1701 | 282 | 277 | 277 | 5 | 5 | 0 | 0 | 0 | 18 | 8463.640 | 0 |
| 2903 | 285 | 281 | 281 | 4 | 4 | 0 | 0 | 0 | 15 | 5610.490 | 0 |
| 4211 | 276 | 272 | 272 | 3 | 3 | 0 | 0 | 1 | 24 | 5895.465 | 0 |

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
| 1701 | 600.140972 | 150030 | 68642 | 199.990/50.002 | false |
| 2903 | 600.125613 | 150015 | 68393 | 199.971/50.001 | true |
| 4211 | 600.138117 | 149997 | 68897 | 199.939/49.998 | true |

| Seed | Clock steps | Max observed offset step (ms) | Max offset deviation (ms) |
| --- | ---: | ---: | ---: |
| 1701 | 6 | 6.206431 | 9.055105 |
| 2903 | 0 | 0.696055 | 2.957607 |
| 4211 | 0 | 0.899361 | 2.030983 |

| Seed | Route | Accepted | Stale | Invalid | Clock rejected | Missing before callback |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| 1701 | imu | 19544 | 0 | 0 | 25435 | 75043 |
| 1701 | joints | 10218 | 0 | 0 | 13445 | 6345 |
| 2903 | imu | 44898 | 0 | 0 | 0 | 75110 |
| 2903 | joints | 23495 | 0 | 0 | 0 | 6512 |
| 4211 | imu | 45306 | 0 | 0 | 0 | 74685 |
| 4211 | joints | 23591 | 0 | 0 | 0 | 6415 |

## Integrity and scope

6 closed journals pass SQLite integrity and immutable-command checks;
receiver successes agree with effect counts. Sender-only, receiver-only and status
divergences, if any, remain explicit in journal-audits.json/command-outcomes.json.
Sources match the frozen 161-file inventory; eight selected
installed binary/SDK hashes and installed demo Python bytes remain constant.
The 56 compiled production sources are unchanged from eb46aba.
No new ROS GTest/full M2 build is claimed; the previously passing 83-test host suite
is unchanged rather than claimed as newly expanded coverage.

For passed cases, strict PCAP zero-drop/file-integrity gates and native v2
reserve/copy/coverage gates passed. 12 cgroup endpoint/phase windows
replay exactly from archived projections. coverage.json retains native offload
interpretation and PCAP population reconciliation separately. No physical wire,
checksum, packet-delivery or isolated resource-overhead qualification follows.
Seed 2903 robot PCAP has 170,340 filter-received versus 170,338 captured/file
records, with zero kernel drops and valid written-record integrity. Its filter
population is explicitly unreconciled; no universal capture-population completeness
or causal attribution follows. All realtime windows are withheld by clock checks;
this additional population flag remains separate. See pcap-populations.json.
Source/callback populations, terminal waits and the shared emulated host prevent
an SRT/DDS performance-advantage claim. Seeded netem does not make independently
started executions deterministic at the application level.

Raw PCAPs, native prefixes, clocks, samplers and journals remain local with hashes.
The preserved plan has no retries or removed cases. Full SRT N2 and both N1
matrices, long v2 N5, deterministic N3, N4 phase barriers, other devices/offload
paths, controlled resources and semantic/security alignment remain open.
Intrinsic/M4 is unchanged; PR #2 remains draft.
