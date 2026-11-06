# SRT N1 full-duration results

Frozen-plan status: **passed**; executed 3 of three planned
600-second cases. Complete duration/seed execution with runner gates: **true**.
This is SRT N1 execution evidence, not complete M3 acceptance, physical delivery,
controlled resource qualification or an SRT/DDS superiority result.

| Seed | Attempts | Successes | Effects | Expired | Receiver expiries without dispatch | Rejected | Failed | UNKNOWN observed | Unresolved | Not admitted | Skipped slots | Maximum terminal observation (ms) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1701 | 300 | 300 | 300 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 923.544 |
| 2903 | 300 | 300 | 300 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 264.239 |
| 4211 | 300 | 300 | 300 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 467.177 |

Totals: 900 attempts, 900 confirmed successes,
900 effects, 0 observed expiries,
0 rejected, 0 failed,
0 observed UNKNOWN, 0 unresolved,
0 not admitted, 0 skipped slots.
Closed-journal states remain separate from driver observations in
command-outcomes.json and journal-audits.json. A missing record or NOT_FOUND is
not nonexecution. Generation checks withhold final equality across uncertainty.
No retry/replay or policy change is introduced.

Terminal observation includes service, journal, transport and reconciliation waits
and any bounded result drain. It is not network transit or execution latency.
Full per-state/reason p50/p95/p99/maxima remain in command-outcomes.json; no uncertain
population is silently reclassified as success. This does not use DDS's offline
journal-clock decomposition on SRT's clock-mapped contexts.

## Source-fenced populations and publication-age bounds

The three measured source windows each cover at least 600 seconds. Every command
is SUCCEEDED/revision 3 in both journals with matching result generation. Actual
source IMU rate is 199.107 Hz for seed 1701 versus approximately 200 Hz for the
other seeds; this variation is retained rather than normalized away.

The checkpoint accounting reproduces six conservation equations per completed
case. Every local admission/replacement/rejection population is retained below.
The SRT accept-to-receiver gap is not automatically network loss or isolated FEC
benefit. Different age origins, transport packing/pacing/reconciliation, crypto
and host conditions prevent a transport-advantage inference from the DDS cohort.

| Seed | Source-enabled seconds | Produced | Bridge published | Observer received | Missing | Actual IMU/joints Hz |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| 1701 | 600.093151 | 149484 | 110267 | 110064 | 39420 | 199.107/49.994 |
| 2903 | 600.153512 | 150038 | 111112 | 111047 | 38991 | 199.999/50.001 |
| 4211 | 600.141223 | 150036 | 111381 | 111300 | 38736 | 200.000/50.002 |

Bounds below cover the source-fenced published population. Their origin is bridge
callback ingress, not physical sensor sampling or DDS Header emission time. The
250-ms publication gate and conservative clock-model assumptions remain intact;
these bounds do not establish all-source delivery, cross-transport age equivalence
or physical network delay. Histograms round up to 1 ms.

| Seed | Route | Published count | p50 upper (ms) | p95 upper (ms) | p99 upper (ms) | Maximum upper bucket (ms) |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| 1701 | imu | 80850 | 43 | 52 | 57 | 87 |
| 1701 | joint | 29417 | 53 | 67 | 73 | 119 |
| 2903 | imu | 81575 | 44 | 52 | 55 | 63 |
| 2903 | joint | 29537 | 53 | 66 | 71 | 83 |
| 4211 | imu | 81865 | 43 | 51 | 54 | 63 |
| 4211 | joint | 29516 | 52 | 65 | 70 | 85 |

| Seed | Attributed stage | Count |
| --- | --- | ---: |
| 1701 | upstream_dds | 266 |
| 1701 | validation | 0 |
| 1701 | admission | 173 |
| 1701 | ingress_replaced | 191 |
| 1701 | ingress_flushed | 0 |
| 1701 | input_rejected | 0 |
| 1701 | outbound_replaced | 5140 |
| 1701 | outbound_expired | 0 |
| 1701 | outbound_flushed | 0 |
| 1701 | srt_accept_to_receiver_gap | 288 |
| 1701 | receiver_rejected | 22227 |
| 1701 | receive_replaced | 10932 |
| 1701 | receive_flushed | 0 |
| 1701 | poll_expired | 0 |
| 1701 | publication_rejected | 0 |
| 1701 | observer_dds | 203 |
| 2903 | upstream_dds | 1 |
| 2903 | validation | 0 |
| 2903 | admission | 132 |
| 2903 | ingress_replaced | 0 |
| 2903 | ingress_flushed | 0 |
| 2903 | input_rejected | 0 |
| 2903 | outbound_replaced | 5012 |
| 2903 | outbound_expired | 0 |
| 2903 | outbound_flushed | 0 |
| 2903 | srt_accept_to_receiver_gap | 296 |
| 2903 | receiver_rejected | 22646 |
| 2903 | receive_replaced | 10839 |
| 2903 | receive_flushed | 0 |
| 2903 | poll_expired | 0 |
| 2903 | publication_rejected | 0 |
| 2903 | observer_dds | 65 |
| 4211 | upstream_dds | 0 |
| 4211 | validation | 0 |
| 4211 | admission | 160 |
| 4211 | ingress_replaced | 1 |
| 4211 | ingress_flushed | 0 |
| 4211 | input_rejected | 0 |
| 4211 | outbound_replaced | 4725 |
| 4211 | outbound_expired | 0 |
| 4211 | outbound_flushed | 0 |
| 4211 | srt_accept_to_receiver_gap | 333 |
| 4211 | receiver_rejected | 22591 |
| 4211 | receive_replaced | 10845 |
| 4211 | receive_flushed | 0 |
| 4211 | poll_expired | 0 |
| 4211 | publication_rejected | 0 |
| 4211 | observer_dds | 81 |

## Integrity and qualification scope

6 closed journals pass integrity/immutable-command checks. Authoritative
terminal agreement is checked where both sides hold terminal records; missing/
unknown/divergent observations remain explicit. Receiver successes agree with
device effects. Original sources match the frozen 161-file inventory,
eight selected installed application/worker/capture/SDK hashes and installed demo
Python bytes. All 56 compiled production sources are unchanged from d2912fc.

Strict PCAP zero-kernel-drop/written-file-integrity and native v2 reserve/copy/
coverage gates pass for passed cases. Filter-received population reconciliation
is independent and preserved per endpoint. All six PCAP endpoints reconcile their reported filter/captured/file populations
here, with zero kernel drops and no file-integrity failure. This is not a universal
capture-population completeness proof. Every realtime packet window is withheld
for clock qualification; native coverage remains independent. See
pcap-populations.json for actual retained bytes and the new nominal file limit.
Realtime windows require both clock
and population qualification; native counts do not confer realtime or physical
wire/delivery qualification. 12 cgroup endpoint/phase windows replay exactly
from archived projections, and the three source-fenced summaries replay exactly
where completed. Diagnostic held-state unqualified/not-ready durations include
startup/tails/gaps; no exact source-window availability bound is inferred.

All 83 host Python tests pass, including rejection of mixed rotating-file
retention configurations in study comparisons. Capture tooling now records and
uses sixteen 16-MB files (256,000,000 nominal bytes), while installed binaries,
SDK, kernel buffer, snapshots and command/publication policies remain unchanged. No new ROS GTest/full M2 build is claimed. Raw captures, prefixes,
journals, clocks and sampler files remain local with hashes; no full inspect/env
dumps are published. The plan has no retries or removed cases. The retention preflight occurred before
its first child; the smaller-volume overwrite probe remains separate from these
bridge workloads and does not establish an arbitrary-duration storage guarantee. Full DDS N1, remaining
age/security/semantic alignment, long v2 N5, deterministic N3, N4 command-phase
barriers and controlled resources remain open. Intrinsic/M4 is unchanged;
PR #2 remains draft.
