# SRT N2 full-duration results

Frozen-plan status: **passed**; executed 3 of three planned
600-second cases. Complete duration/seed execution with runner gates: **true**.
This is SRT N2 execution evidence, not complete M3 acceptance, physical delivery,
controlled resource qualification or an SRT/DDS superiority result.

| Seed | Attempts | Successes | Effects | Expired | Receiver expiries without dispatch | Rejected | Failed | UNKNOWN observed | Unresolved | Not admitted | Skipped slots | Maximum terminal observation (ms) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1701 | 300 | 300 | 300 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1106.214 |
| 2903 | 300 | 300 | 300 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1309.764 |
| 4211 | 300 | 300 | 300 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1110.049 |

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

All 900 commands are SUCCEEDED/revision 3 in both closed journals, with matching
results/generations and 300 effects per device. No expiry, UNKNOWN, unresolved,
nonadmission or skipped slot occurs. No repeated application intent is introduced.

The checkpoint accounting reproduces six conservation equations per completed
case. Every local admission/replacement/rejection population is retained below.
The SRT accept-to-receiver gap is not automatically network loss or isolated FEC
benefit. Different age origins, transport packing/pacing/reconciliation, crypto
and host conditions prevent a transport-advantage inference from the DDS cohort.

| Seed | Source-enabled seconds | Produced | Bridge published | Observer received | Missing | Actual IMU/joints Hz |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| 1701 | 600.149477 | 150036 | 64233 | 64176 | 85860 | 199.997/50.001 |
| 2903 | 600.101959 | 150026 | 64037 | 63980 | 86046 | 199.999/50.002 |
| 4211 | 600.140695 | 150036 | 64183 | 64125 | 85911 | 200.000/50.002 |

Bounds below cover the source-fenced published population. Their origin is bridge
callback ingress, not physical sensor sampling or DDS Header emission time. The
250-ms publication gate and conservative clock-model assumptions remain intact;
these bounds do not establish all-source delivery, cross-transport age equivalence
or physical network delay. Histograms round up to 1 ms.

| Seed | Route | Published count | p50 upper (ms) | p95 upper (ms) | p99 upper (ms) | Maximum upper bucket (ms) |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| 1701 | imu | 44244 | 99 | 120 | 127 | 143 |
| 1701 | joint | 19989 | 112 | 136 | 145 | 168 |
| 2903 | imu | 44089 | 97 | 118 | 126 | 144 |
| 2903 | joint | 19948 | 110 | 134 | 144 | 164 |
| 4211 | imu | 44128 | 101 | 120 | 127 | 141 |
| 4211 | joint | 20055 | 114 | 137 | 146 | 163 |

| Seed | Attributed stage | Count |
| --- | --- | ---: |
| 1701 | upstream_dds | 5 |
| 1701 | validation | 0 |
| 1701 | admission | 148 |
| 1701 | ingress_replaced | 2 |
| 1701 | ingress_flushed | 0 |
| 1701 | input_rejected | 0 |
| 1701 | outbound_replaced | 4830 |
| 1701 | outbound_expired | 0 |
| 1701 | outbound_flushed | 0 |
| 1701 | srt_accept_to_receiver_gap | 35350 |
| 1701 | receiver_rejected | 39549 |
| 1701 | receive_replaced | 5919 |
| 1701 | receive_flushed | 0 |
| 1701 | poll_expired | 0 |
| 1701 | publication_rejected | 0 |
| 1701 | observer_dds | 57 |
| 2903 | upstream_dds | 0 |
| 2903 | validation | 0 |
| 2903 | admission | 183 |
| 2903 | ingress_replaced | 1 |
| 2903 | ingress_flushed | 0 |
| 2903 | input_rejected | 0 |
| 2903 | outbound_replaced | 4846 |
| 2903 | outbound_expired | 0 |
| 2903 | outbound_flushed | 0 |
| 2903 | srt_accept_to_receiver_gap | 35278 |
| 2903 | receiver_rejected | 39731 |
| 2903 | receive_replaced | 5950 |
| 2903 | receive_flushed | 0 |
| 2903 | poll_expired | 0 |
| 2903 | publication_rejected | 0 |
| 2903 | observer_dds | 57 |
| 4211 | upstream_dds | 4 |
| 4211 | validation | 0 |
| 4211 | admission | 180 |
| 4211 | ingress_replaced | 5 |
| 4211 | ingress_flushed | 0 |
| 4211 | input_rejected | 0 |
| 4211 | outbound_replaced | 4812 |
| 4211 | outbound_expired | 0 |
| 4211 | outbound_flushed | 0 |
| 4211 | srt_accept_to_receiver_gap | 35223 |
| 4211 | receiver_rejected | 39890 |
| 4211 | receive_replaced | 5739 |
| 4211 | receive_flushed | 0 |
| 4211 | poll_expired | 0 |
| 4211 | publication_rejected | 0 |
| 4211 | observer_dds | 58 |

## Integrity and qualification scope

6 closed journals pass integrity/immutable-command checks. Authoritative
terminal agreement is checked where both sides hold terminal records; missing/
unknown/divergent observations remain explicit. Receiver successes agree with
device effects. Original sources match the frozen 161-file inventory,
eight selected installed application/worker/capture/SDK hashes and installed demo
Python bytes. All 56 compiled production sources are unchanged from fd23de6.

Strict PCAP zero-kernel-drop/written-file-integrity and native v2 reserve/copy/
coverage gates pass for passed cases. Filter-received population reconciliation
is independent and preserved per endpoint. All six PCAP endpoints reconcile their reported filter/captured/file populations,
with zero kernel drops; this is not a universal capture-population completeness
proof. Realtime clock qualification fails for both phases in every case, so no
realtime packet-window totals are emitted. Native records remain independently
qualified. Realtime windows require both clock
and population qualification; native counts do not confer realtime or physical
wire/delivery qualification. 12 cgroup endpoint/phase windows replay exactly
from archived projections, and the three source-fenced summaries replay exactly
where completed. Diagnostic held-state unqualified/not-ready durations include
startup/tails/gaps; no exact source-window availability bound is inferred.

The unchanged 83-test host suite is previous validation, not newly expanded
coverage. No new ROS GTest/full M2 build is claimed. Raw captures, prefixes,
journals, clocks and sampler files remain local with hashes; no full inspect/env
dumps are published. The plan has no retries or removed cases. Full N1, remaining
age/security/semantic alignment, long v2 N5, deterministic N3, N4 command-phase
barriers and controlled resources remain open. Intrinsic/M4 is unchanged;
PR #2 remains draft.
