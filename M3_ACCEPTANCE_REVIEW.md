# M3 acceptance review — 2026-11-09

The authorized [frozen N3 cohort](evidence/m3-n3-frozen-cohort-2026-11-09/README.md)
finished with8 strict passes and a final-case shutdown FAIL: the operator bridge
exceeded its5s SIGINT wait and required forced kill. No retry or tuning; all29
remaining campaign cases stay disabled. M3 remains open and PR2 stays draft.
The [retained shutdown diagnosis](evidence/m3-n3-shutdown-diagnosis-2026-11-09/README.md)
confirms a pre-signal observation cutoff: the blocked function remains unknown.
No tuning, retry, patch or new experiment followed.


Final comparison and acceptance conclusion:
[M3_COMPARISON_AND_ACCEPTANCE.md](M3_COMPARISON_AND_ACCEPTANCE.md).
The reporting task is complete; the qualification status below remains open.
The concrete [N3/current-build closure plan](M3_CLOSURE_PLAN.md) is prepared,
with the authorized N3 outcome recorded and all later stages disabled.

**M3 is not ready to mark complete or merge.** The current evidence supports a
local Linux amd64/Jazzy simulator development result, with explicit failed and
unqualified gates. M0–M2 remain accepted only in their recorded scope; Intrinsic/
M4 is not started. PR2 stays draft. No new diagnostic cohort is scheduled here.

The milestone contract in [ARCHITECTURE.md](ARCHITECTURE.md) asks for reproducible
impairment evidence, preserved semantics and demonstrated benefit or justified
non-superiority. It does not require tuning DDS until it succeeds. A failed DDS
cold start is a measured comparison outcome; it supplies no steady-window latency,
sensor availability or resource denominator and must not be converted into a
numerical superiority claim.

| Gate | Current evidence and result | Remaining boundary |
|---|---|---|
|Core/ROS command semantics|[M2 acceptance](evidence/m2-ros-jazzy-2026-11-05/ACCEPTANCE.md); [sender reconciliation](evidence/m3-sender-reconciliation-2026-11-09/README.md) implements exact-row UNKNOWN on actual local abandonment; SDK81/ROS41 pass|Simulator only; no historical UNKNOWN replay/nonexecution inference|
|N1/N2 SRT execution|[N1](evidence/m3-srt-n1-full-2026-11-06/README.md), [N2](evidence/m3-srt-n2-full-2026-11-06/README.md): recorded three-seed600s cases and publication-age bounds|Those exact historical build hashes; not a fresh matrix on the latest install|
|N1/N2 DDS execution|[N1](evidence/m3-dds-n1-full-2026-11-06/README.md), [N2](evidence/m3-dds-n2-full-2026-11-06/README.md): full-duration execution evidence|DDS age gate remains open; N2/2903 robot has170,340 filtered vs170,338 file records, so capture population is not reconciled. Realtime Header ages are not SRT ingress interval bounds|
|N3 deterministic repair|[Frozen current-build cohort](evidence/m3-n3-frozen-cohort-2026-11-09/README.md): first8 strict cases pass with zero source skips; case9 two-loss4211 fails operator bridge shutdown|Existing5s SIGINT budget exceeded; forced kill/-9. Case9 accounting/capture revalidation not reached; cohort FAIL, no retry. Older case6 source-skip failure remains unchanged, no splice|
|N4 interruption/start/result/restart|[Failure controls and phase cuts](evidence/m3-failure-n4-2026-11-08/README.md), [remaining bounded cases](evidence/m3-n4-remaining-2026-11-08/README.md) retain passing scoped evidence and earlier failures|Bounded native/ROS fixtures, not every long combined load/hardware case|
|N5 SRT command progress|[Frozen probe cohort](evidence/m3-probe-loaded-cohort-2026-11-09/README.md): N0 8/8, N5 128/128,22 skipped offers|Qualified prior matched probe build, not newest sender-reconcile loaded qualification; SENSOR reduction/accounting is not full freshness/availability acceptance|
|N5 retained SENSOR freshness and bridge slots|[Offline audit](evidence/m3-n5-sensor-retained-audit-2026-11-09/README.md): all27,750 publications covered; exact modeled upper ages178.324341/182.559637ms <250ms; six balances0; fixed one-latest-sample/route/stage storage|Prior probe build/one300s seed only;465 unknown-age rejections and47,287 unobserved source samples retained. No continuous availability, measured queue high-water or hard SDK/process memory peak|
|Default DDS cold startup under N5|[Latest matched-build confirmation](evidence/m3-dds-loaded-confirmation-2026-11-09/README.md): N0 8/8; N5 FAIL before measurement with asymmetric sampled endpoint matching|Current default-DDS cold-start failure confirmed. No steady60s workload result, no unique fragmentation cause or default change|
|Age, CPU, memory and wire comparison|Existing source fences, endpoint/resource accounting and observation scopes retained|No common-origin age equivalence, complete observer/security-cost parity or controlled hardware-performance claim|
|Lifecycle and provenance|Latest DDS cohort: all6 native children exit0,4 containers/2 networks removed;146 raw hashes; matched runtime chain fixed; host407 pass|Does not erase prior missing-footer failures or qualify real robots/cross-host clocks|

## Concrete closure work

1. Freeze the build and scope being accepted. Earlier full matrices remain tied
   to their archived hashes; a passing historical run is not silently assigned to
   a new binary. New sender reconciliation has focused recovery/capacity/result-
   race and full affected SDK/ROS checks, but no new loaded SRT cohort is claimed.
2. The [retained operator shutdown diagnosis](evidence/m3-n3-shutdown-diagnosis-2026-11-09/README.md)
   is complete to its observation limit. Sampler and packet data end before
   SIGINT; absent footer alone does not locate the blocking stage. The operator
   worker is plain SDK, not ROS rate backend. No specific corrective patch is
   justified yet; a narrow stage/blocked-stack visibility design would be the
   discriminating next evidence, subject to a separate scope decision. No new
   instrumentation or experiment is started. Keep8 strict PASS/1 FAIL, the5s
   lifecycle gate and all29 remaining stages disabled; no retry or cohort splice.
3. The retained-run N5 publication-age assessment is now complete in the
   [offline audit](evidence/m3-n5-sensor-retained-audit-2026-11-09/README.md).
   All publication histograms reconcile; unknown/missing populations are explicit,
   and fixed bridge slots are source-established. Keep continuous availability,
   measured occupancy peaks and total SDK/process memory caps unavailable rather
   than upgrading them to passes or launching another experiment. This does not
   promote the old probe build into newest-build/all-seed qualification.
4. The [comparison and acceptance statement](M3_COMPARISON_AND_ACCEPTANCE.md)
   is now complete: default DDS has no latest loaded steady window, age/security/
   resource equivalence is not established, and no general superiority claim is
   justified. Failed/unavailable populations, including the DDS N2 capture
   discrepancy, remain explicit. This reporting closure grants no M3 acceptance,
   changes no source-slot threshold and does not schedule another experiment.

No automatic N3 retry, DDS fallback experiment, provider patch, ARP study or new
tracer follows from this review. Existing no-tuning/no-forced-expiry/no-historical-
replay constraints persist. A scoped acceptance proposal can be reviewed after
these concrete boundaries are resolved; this document grants no waiver, changes
no acceptance threshold and authorizes neither merge nor M4 development.
