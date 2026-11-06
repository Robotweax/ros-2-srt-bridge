# Explicit paced-DDS N5: current-capture repetitions

Frozen-plan status: **passed**. Executed 3 of three planned
300-second cases. All planned duration/seed cases completed with execution/capture gates:
**true**. This describes explicit paced DDS N5 execution coverage,
not N5 age-gate qualification, complete M3 acceptance, SRT N5, or equivalence of age/security/transport costs.

Command totals: 450 attempts, 450 confirmed successes,
450 effects, 0 observed expiries
(0 receiver expiry records without dispatch),
0 UNKNOWN, 0 unresolved,
0 not admitted, 0 rejected, 0 failed
and 0 skipped cadence slots.
These populations remain separate. Skipped slots are not silently retried.
A terminal expiry is not a success. Missing/unknown state is not nonexecution.

| Seed | Attempts | Successes | Effects | Expired | Expired without dispatch | UNKNOWN | Unresolved | Not admitted | Skipped slots | Max terminal observation (ms) | History polls omitted |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1701 | 150 | 150 | 150 | 0 | 0 | 0 | 0 | 0 | 0 | 229.705 | 0 |
| 2903 | 150 | 150 | 150 | 0 | 0 | 0 | 0 | 0 | 0 | 227.678 | 0 |
| 4211 | 150 | 150 | 150 | 0 | 0 | 0 | 0 | 0 | 0 | 232.252 | 0 |

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
| 1701 | 300.121123 | 75031 | 19216 | 199.999/50.003 | true |
| 2903 | 300.114763 | 75027 | 19073 | 199.993/50.001 | true |
| 4211 | 300.117721 | 75026 | 19188 | 199.988/50.000 | true |

| Seed | Clock steps | Max observed offset step (ms) | Max offset deviation (ms) |
| --- | ---: | ---: | ---: |
| 1701 | 0 | 0.232430 | 1.363899 |
| 2903 | 0 | 0.199806 | 1.273567 |
| 4211 | 0 | 0.465805 | 1.368761 |

| Seed | Route | Accepted | Stale | Invalid | Clock rejected | Missing before callback |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| 1701 | imu | 11791 | 0 | 0 | 0 | 48233 |
| 1701 | joints | 7425 | 0 | 0 | 0 | 7582 |
| 2903 | imu | 11686 | 0 | 0 | 0 | 48335 |
| 2903 | joints | 7387 | 0 | 0 | 0 | 7619 |
| 4211 | imu | 11792 | 0 | 0 | 0 | 48228 |
| 4211 | joints | 7396 | 0 | 0 | 0 | 7610 |

## Integrity and scope

6 closed journals pass SQLite integrity and immutable-command checks;
receiver successes agree with effect counts. Sender-only, receiver-only and status
divergences, if any, remain explicit in journal-audits.json/command-outcomes.json.
Sources match the frozen 161-file inventory; nine selected
installed application/worker/capture/SDK/provider-probe hashes and installed demo Python bytes remain constant.
The 56 compiled production sources are unchanged from 1bf9bfe.
No new ROS GTest/full M2 build is claimed; the previously passing 83-test host suite
is unchanged rather than claimed as newly expanded coverage.

For passed cases, strict PCAP zero-drop/file-integrity gates and native v2
reserve/copy/coverage gates passed. 12 cgroup endpoint/phase windows
replay exactly from archived projections. coverage.json retains native offload
interpretation and PCAP population reconciliation separately. No physical wire,
checksum, packet-delivery or isolated resource-overhead qualification follows.
Source/callback populations, terminal waits and the shared emulated host prevent
an SRT/DDS performance-advantage claim. Seeded netem does not make independently
started executions deterministic at the application level.

Raw PCAPs, native prefixes, clocks, samplers and journals remain local with hashes.
The preserved plan has no retries or removed cases. The N1/N2 execution cohorts and unresolved age/clock gates remain separate.
N5 seeds label repetitions, without stochastic delay/loss in this profile. Full SRT N5, default DDS N5 discovery, deterministic N3, N4 phase barriers, other devices/offload
paths, controlled resources and semantic/security alignment remain open.
Intrinsic/M4 is unchanged; PR #2 remains draft.

## Tuned profile and competitor proof

All three repetitions confirm 150 commands/effects each, no skipped or uncertain
intents. Six journals agree and twelve cgroup windows replay exactly. All shared-
VM age estimates qualify in these runs; realtime packet windows remain withheld.
Each child verifies native applied QoS/controller settings in a separate network-
none preflight, with the provider probe frozen as the ninth selected binary.
The measured profile uses sensor-only asynchronous 1600-controller-bytes/50-ms
pacing, 1200-byte packetization, KeepLast(1); control settings are unchanged.

All competitor clients remain live through scenario polling. Whole-run offered
rates are 128000.016 / 128019.300 / 128002.557 bits/s against the 128000-bit/s target.
Projected interval/setup/total data are retained per case; this does not prove
matched-window delivery/loss. Source production/callback counts are 75031/19216,
75027/19073 and 75026/19188. The reduction includes intentional middleware pacing/
replacement and other stages, not isolated WAN loss. N5 seeds label repetitions
without stochastic loss/jitter. Default DDS N5 discovery remains open.

This cohort was completed/replayed with all 161 sources matching 1bf9bfe before
the subsequent SRT-only competitor validation change. It is not compared as a
controlled cost or transport-superiority result against that separate SRT cohort.
