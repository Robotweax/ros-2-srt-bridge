# M3 comparison and acceptance statement — 2026-11-09

**The evidence comparison is complete within the scope below. M3 is not accepted
as complete under the unchanged qualification plan.** PR2 remains draft; no merge,
M4 start, threshold change or waiver follows from this statement. M0–M2 keep their
recorded local Linux amd64/Jazzy simulator acceptance.

This statement uses retained reports and audits only. No experiment, traffic,
runtime build, tuning, journal recovery, expiry or command replay was performed.
It records demonstrated capabilities, failed gates and unavailable measurements
without converting one category into another. The decision record and hashed
source-report index are in
[evidence/m3-comparison-acceptance-2026-11-09](evidence/m3-comparison-acceptance-2026-11-09/).

## Comparison conclusion

The SRT bridge demonstrates protected selective telemetry transport, conservative
publication authorization, deterministic repair behavior in the recorded fault
subcases, durable command outcomes and query-first recovery. It sustained command
progress while reducing telemetry in the retained N5 case. Default DDS completed
the recorded healthy control; its latest loaded simultaneous cold start failed
before a measurement window or command workload could begin.

**These observations do not establish general SRT superiority, DDS equivalence,
or an intrinsic transport speed/resource advantage.** The workloads share target
rates and nominal impairment profiles, but age origins, security configuration,
process topology, observer cost, builds and run times are not fully equivalent.
A failed DDS startup is a valid comparison outcome, not an obligation to tune DDS
until successful. It supplies no steady-window denominator for latency,
throughput or resource ratios. No transport ranking or improvement percentage is
justified by this record.

## Recorded outcomes

The following counts describe separately frozen series. They are not pooled
success probabilities, contemporaneous matched trials or current-build guarantees.

| Retained series | Command outcomes | Qualification boundary |
|---|---|---|
|SRT N1,3 seeds x600s|900 attempts,900 successes/effects,0 skipped offers|Historical pinned series; publication upper-age bucket max119ms, not physical sensor age|
|SRT N2,3 seeds x600s|900 attempts,900 successes/effects,0 skipped offers|Historical pinned series; publication upper-age bucket max168ms|
|Default DDS N1,3 seeds x600s|892 attempts,890 successes/effects,2 receiver-backed expiries without dispatch;8 skipped offers|Seed1701 age estimates unqualified; no common SRT/DDS age comparison|
|Default DDS N2,3 seeds x600s|843 attempts,830 successes/effects,12 receiver-backed expiries without dispatch,1 nonadmission;57 skipped offers|Age gate open; seed2903 robot PCAP has170,340 filtered versus170,338 captured/file records despite0 kernel drops|
|SRT N5/1701,300s prior probe build|128/128 successes/effects;22 skipped offers|One retained build/seed; progress is not a continuous2s service or availability guarantee|
|Default DDS N0/1701,15s current matched build|8/8 successes/effects;0 skipped offers|Healthy control only; separate run/build from the prior SRT N5 observation|
|Default DDS N5/1701,60s requested current matched build|No measurement window;0 commands submitted/effects; empty journals|FAIL at45s sender-readiness wait; performance populations unavailable, not a0% success ratio|

The N1/N2 totals come from the original
[SRT N1](evidence/m3-srt-n1-full-2026-11-06/totals.json),
[SRT N2](evidence/m3-srt-n2-full-2026-11-06/totals.json),
[DDS N1](evidence/m3-dds-n1-full-2026-11-06/totals.json) and
[DDS N2](evidence/m3-dds-n2-full-2026-11-06/totals.json) reports. Success, expiry,
nonadmission, uncertainty and skipped offers remain separate. Original execution
PASS labels do not supersede the explicit age/capture limitations in those
reports, including the [DDS N2 population discrepancy](evidence/m3-dds-n2-full-2026-11-06/pcap-populations.json).

In the [latest DDS cold-start case](evidence/m3-dds-loaded-confirmation-2026-11-09/README.md),
the operator sampled no robot CONTROL/HELLO publishers or received HELLOs. The
robot sampled all four endpoint matches and407 received HELLOs but stayed unready.
Load/capture/controlled-shutdown checks passed. This establishes a sampled
readiness failure on that build, not a unique fragmentation, ARP, scheduler or
provider cause. Earlier native fragment-loss evidence and the contradicted ROS
N0 transfer hypothesis retain their original scopes.

## Supported bridge properties

- The [retained N5 SENSOR audit](evidence/m3-n5-sensor-retained-audit-2026-11-09/README.md)
  covers all27,750 publications using full RPC checkpoint histogram deltas.
  Exact modeled upper-age maxima are178.324341ms IMU and182.559637ms joints,
  below250ms. This is bridge-ingress to the check immediately before publication,
  under the original clock assumptions, not physical source-to-observer age.
  Six accounting residuals are0. Of75,037 produced samples,47,287 are unobserved;
 539 receiver rejections include465 age-unqualified/invalid and74 unclassified.
  No percentile or unique loss cause is assigned to missing/unknown populations.
- Frozen source establishes one latest queued sample per configured sensor route
  at each persistent bridge stage. Empty start/end checkpoints and sampled SDK
  gauges do not establish continuous high-water marks, a whole-stack memory cap
  or uninterrupted delivery. N5 allows sample reduction; reduction alone is not
  failure of its freshness contract.
- [N3 fault subcases](evidence/m3-n3-thirty-second-matrix-2026-11-09/README.md)
  demonstrate one selected source repaired with the original typed payload and
  two selected sources absent at the drained cutoff with later route progress.
  These subcase results do not repair the failed frozen cohort described below.
- [N4 boundary evidence](evidence/m3-failure-n4-2026-11-08/README.md) and
  [bounded freshness/deadline/restart cases](evidence/m3-n4-remaining-2026-11-08/README.md)
  support their recorded interruption, start/result and query/restart semantics.
  They are not every phase under every long combined workload or hardware setup.
- [Sender reconciliation](evidence/m3-sender-reconciliation-2026-11-09/README.md)
  now carries proved local abandonment to the exact sender row as provisional
  UNKNOWN without a new ticket, unrelated-row invalidation or overwriting newer
  peer results. Its SDK81/ROS41 checks and latest host413 audit checks are retained
  validation, not newly executed tests in this documentation step.

No historical UNKNOWN is reclassified as nonexecution or permission to replay.
Earlier failed cohorts, omitted/skipped slots and stopped N5/4211 remain recorded.
A success result in a different fresh session does not resolve an old intent.

## Explicit comparison limitations

| Dimension | What is established | What is not established |
|---|---|---|
|Age origin|SRT conservative bridge-ingress upper bounds; DDS shared-VM ROS Header realtime estimates with clock-rejection populations|A common-origin cross-transport percentile, physical sampling age, cross-host clock qualification or equal age acceptance in all series|
|Command semantics|Recorded durable results and original start budgets; unknown/missing/nonadmitted/expired outcomes distinguished|A poll-independent execution latency, continuous2s service, or proof that expiry-seal/reconciliation costs and failure semantics are identical|
|Security|Pinned SRT protected profile/GCM/SESSIONAUTH qualification in its recorded scope|An equivalent authenticated/encrypted DDS configuration or equal security cost; no security-throughput ranking|
|Topology and observers|SRT bridge/worker path versus direct typed DDS plus command coordinator; trace/capture/sampler interventions documented|Isolated transport cost, observer-free speed, or ratios across different builds, startup modes and runs|
|CPU and memory|Existing scoped process/cgroup observations and sampled RSS; fixed bridge slots|Hard total allocator/FEC/kernel/RMW peaks, leak absence, hardware-independent efficiency or comparative memory superiority|
|Wire and FEC|Recorder-qualified observations where each file/dispatch/kernel gate passes; deterministic repair subcases|Every historical capture qualified, realtime-PCAP latency authority, isolated physical-wire cost, or assigning every aggregate gap to WAN loss/FEC|
|Coverage|Specified image, amd64 emulation, local VM clocks, seeds/durations and exact recorded binary hashes|Promotion to the latest binary, all seeds/profiles, real hardware/offloads, production WAN, real-time motion or Intrinsic runtime qualification|

Unavailable hard memory peaks and physical hardware guarantees are limitations on
claims; this statement does not invent new acceptance thresholds for them. The
unreconciled DDS N2 capture is excluded from a qualified file-population/wire
comparison. Clock-rejected DDS ages are not silently dropped into favorable
percentiles. Previous capture-clock failures remain failures of those mappings;
newer monotonic observations do not retrospectively qualify them.

## M3 acceptance decision

**Decision: do not mark M3 complete on the present record.** This is a completed
technical acceptance assessment, not a waiver or a declaration that all bridge
properties failed. The architecture calls for reproducible impairment evidence,
preserved semantics and documented benefit or justified non-superiority; the
comparison conclusion above meets the reporting task, but does not erase these
outstanding qualification boundaries:

1. The frozen30s N3 cohort remains **FAIL**: five prefix cases pass, the sixth
   skips3 IMU source slots despite average cadence within1%, and three later
   actual executions fall outside its intended stop boundary. The harness guard
   was corrected. No zero-skip relaxation, retry or retrospective PASS is applied.
2. The newest sender-reconcile build has its recorded SDK/ROS and focused recovery
   validation, but no complete loaded SRT/full profile/seed qualification matrix.
   Earlier successful long matrices remain valid evidence for their own hashes;
   they cannot be silently assigned to the new candidate. A complete release
   candidate matrix is not established by combining different build variants.
3. The full SRT/DDS comparison remains limited as listed above: DDS N1/N2 age
   qualification is incomplete, one DDS N2 capture population is unreconciled,
   and the latest default-DDS N5 steady window never began. These outcomes must
   remain failed/unavailable in any completion review, not be labelled equivalent
   passing measurements. Making DDS pass or asserting universal superiority is
   not a prerequisite introduced by this statement.

The retained-run N5 publication-age assessment and fixed bridge-slot conclusion
are supported and need no new experiment to be documented. Continuous queue
peaks/availability and whole-stack memory bounds remain unavailable rather than
being automatically upgraded to required experiments. M0–M2 acceptance is not
revoked; full M3 acceptance is not granted. No safety/physical robot deployment,
merge, M4 work or new experiment is authorized here.

## Disposition

The comparison and acceptance statement is delivered. No further diagnostic
cohort, tuning change, DDS fallback, provider patch or historical replay is queued
automatically. A future change to the N3 source scheduling qualification contract
must be prospective and explicit. Any future completion proposal must identify
the exact build/scope being accepted and account for the open gates; this
statement changes neither contract nor measurements.
