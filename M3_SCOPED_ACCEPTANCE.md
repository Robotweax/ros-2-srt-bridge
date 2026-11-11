# Proposed scoped M3 acceptance — 2026-11-11

**Recommendation: accept M3 for the recorded local Linux amd64 / ROS Jazzy simulator, on the exact matched instrumented SDK/ROS build and pinned SRT provider identified below.** The retained evidence supports reproducible impairment testing, the specified command and SENSOR contracts in the recorded cases, and a documented comparison that does not establish general SRT superiority over DDS.

This is a prepared technical acceptance recommendation. Formal milestone acceptance remains pending; it does not merge or publish a release. PR2 remains draft/unmerged, M4/Intrinsic remains disabled, and no campaign case, experiment, tuning, retry, expiry forcing or historical command replay is authorized. M0–M2 retain their existing scoped acceptance.

## Evidence and build boundary

The [38-ID verdict mapping](evidence/m3-fresh-n1-2903-execution-2026-11-11/acceptance-update.json) contains a passing retained result for every case in the closure plan. It spans six frozen series, including the original LONG series from which only N1/1701 receives passing credit. Historical failures remain failures; distinct passing IDs are not an all-attempt success rate.

| Coverage | Passing IDs | Retained series / freeze prefix |
|---|---:|---|
| N3 deterministic repair | 9 | [Fresh strict cohort](evidence/m3-strict-n3-execution-2026-11-10/README.md), `45036de78761` |
| N0 baseline, 300 s | 1 | [Stabilized lifecycle](evidence/m3-current-n0-stable-execution-2026-11-10/README.md), `98a357e418c2` |
| N4 interruption / freshness / crash | 19 | [Corrected fresh cohort](evidence/m3-current-n4-corrected-execution-2026-11-10/README.md), `ecb0d1346932` |
| N1/1701, 600 s | 1 | [Original LONG cohort](evidence/m3-current-long-execution-2026-11-10/README.md), `868a21578a61`; later failure excluded from passing credit |
| Remaining N1/N2/N5 | 7 | [Fresh seven-case cohort](evidence/m3-current-remaining-execution-2026-11-11/README.md), `df3cfbabfe3b` |
| N1/2903, 600 s | 1 | [Fresh single case](evidence/m3-fresh-n1-2903-execution-2026-11-11/README.md), `b3609d03e5ac` |

N1/N2 each cover three predeclared seeds at 600 seconds; N5 covers the same three seeds at 300 seconds. N3 contains baseline/one-loss/two-loss cases for each seed. N4 comprises 13 native command-boundary/query cases, three ROS freshness cases and three ROS crash cases. Bounded N3/N4 tests are not long combined-load or hardware tests.

The [build record](evidence/m3-scoped-acceptance-2026-11-11/matched-build.json) verifies the same 14 matched build entries and 87 native inputs across these series. The installed layout is `install/bridge-socket-disposition` with `install/m3-socket-disposition-ros`. Provider revision is `52be7c86ee1f303cbb0c8718c364217e4dd97a36`, archive SHA-256 `3fa56e487e6c6408d9e41779d18aba9ff866978892ddbe3b88ac12fc51141673`. The amd64 workload runs under Docker Desktop emulation; the later independent observer is native ARM64. Per-series freezes retain image, source, input, settings, fixture, observer and assessor identities.

Harnesses and assessment instrumentation evolved between series. The calibrated per-thread metadata assessor is qualified by its own later calibration and executions, not retrospectively assigned to N3, N4 or the original failed N1 capture. Native build identity does not imply identical instrumentation coverage. No claim extends automatically to a rebuilt or changed artifact, other platforms, untested seeds, or all future executions.

## Basis for the recommendation

| Architectural criterion | Supported conclusion | Boundary |
|---|---|---|
| Reproducible impairment artifacts | Frozen profiles/seeds/durations, exact binaries, raw evidence, strict assessments and cleanup records are retained. The review reverified 10,085 artifacts and 60 indexes. | Selected proofs are public; large captures/full traces and some raw records remain indexed local-only. Review verified hashes and verdict mappings; it did not rerun packet validators or native tests. |
| Conservative SENSOR freshness and bounds | Passing source/checkpoint/accounting/publication-age gates, explicit missing/rejected populations, and fixed latest-only bridge slots support the configured contract. | Zero residual is accounting closure, not zero loss. Publication-age bounds depend on the recorded clock model; they are not physical sampling or typed-observer arrival ages. No continuous high-water or whole-stack memory guarantee. |
| N3 repair semantics | Exactly selected one-DATA loss is repaired with the original typed payload; selected two-DATA loss is irreparable at the drained cutoff while later progress remains observed. | Deterministic selected rows, not arbitrary loss-pattern recovery probabilities or general FEC advantage. |
| Command integrity / N4 recovery | Durable success proofs, single original handoffs/effects, query-first recovery and conservative UNKNOWN handling pass their declared cases. Deliberate crash-before/effect cases correctly retain uncertainty; crash-after-commit retains the original proved success. | UNKNOWN and NOT_FOUND never authorize replay or prove nonexecution. Simulator effects are not physical-device outcome proof. |
| Lifecycle | Required owned-child shutdown and cleanup checks pass in each accepted series, with the launch/observer evidence applicable to that series. | Clean fresh runs do not explain or prove removal of the historical shutdown hang; observed latencies are not general bounds. |
| DDS comparison / benefit or justified non-superiority | Protected selective SRT telemetry and durable CONTROL progress are demonstrated under recorded impairments. The retained DDS comparison is reportable with an explicit inconclusive superiority conclusion. | Unequal age/security/topology/resource/observer conditions prevent causal transport rankings, improvement percentages or equivalent pass claims. |

N5 retains **83 skipped command opportunities** across the fresh three-seed cohort and roughly six-second maximum adjacent-intent gaps. Its admitted commands succeed while telemetry is reduced; this supports recorded progress, not uninterrupted two-second service or a hard scheduling/latency SLA. No scheduling requirement was relaxed in this review. The fresh N1/2903 result is 300/300 confirmed successes/effects, no skipped slots, six zero accounting residuals and 224/235 ms IMU/joint publication-age upper maxima under the unchanged 250 ms gate.

## Historical failures and unresolved results remain explicit

- The [earlier N3 30-second matrix](evidence/m3-n3-thirty-second-matrix-2026-11-09/execution-matrix.json) remains failed: its zero-skip failure and three later executions outside the corrected stop boundary are not promoted to a passing frozen cohort.
- The [original frozen N3 two-loss/4211 failure](evidence/m3-n3-frozen-cohort-2026-11-09/gate-report.json) remains eight passes plus one failed shutdown. The operator exceeded the five-second wait and was killed. [Retained diagnosis](evidence/m3-n3-shutdown-diagnosis-2026-11-09/README.md) cannot recover the blocked function/root cause. Later diagnostics and a fresh nine-case pass do not prove that cause fixed.
- Failed N0 attempts retain their [capability-attestation](evidence/m3-current-n0-execution-2026-11-10/gate-report.json), [identity-binding](evidence/m3-current-n0-corrected-execution-2026-11-10/gate-report.json) and [trace-lifecycle](evidence/m3-current-n0-bound-execution-2026-11-10/gate-report.json) failures. The later stabilized fresh pass does not rewrite them.
- The [original N4 cohort](evidence/m3-current-n4-execution-2026-11-10/gate-report.json) remains 16 passes, one JSON-type assessor failure and two unexecuted cases. A separately frozen corrected 19-case cohort supplies new coverage.
- The [original N1/2903 strict failure](evidence/m3-current-long-execution-2026-11-10/cases/N1-combined-2903/strict-assessment.json) remains failed for unavailable live-target stack evidence, despite its inner workload pass. SHA-256 stays `e9cf84c7b6beffe584cfc06134d44c263b4884fcf166b3e113a7430cdedd7d30`; its original cohort stays one pass, one failure, seven not executed. No old directory is repopulated. The fresh N1/2903 pass does not reconstruct the missing stack.
- Historical clock deferral, admission/session and probe-renewal failures retain their original diagnostic limits. [Intent 118](evidence/m3-sender-pending-diagnosis-2026-11-09/README.md) remains UNKNOWN/reconcile_required with an invalid result; no expiry forcing, recovery mutation or replay occurred. New-session successes and the sender-reconciliation fix do not settle that original command or uniquely attribute ARP, qdisc, scheduling or provider causes.
- [DDS N1/N2 age limitations and the DDS N2 capture discrepancy](M3_COMPARISON_AND_ACCEPTANCE.md) remain unqualified. The [latest loaded default-DDS cold start](evidence/m3-dds-loaded-confirmation-2026-11-09/README.md) failed before measurement; it supplies no steady-window latency/throughput/resource denominator. A paced DDS candidate stays a distinct configuration. Making DDS pass is not a prerequisite invented by this review.

## Limits carried with any scoped acceptance

This recommendation does not certify physical robots, a production WAN, cross-host clocks, hard real-time motion, continuous availability, whole-stack/SDK/kernel/RMW memory peaks, leak freedom, observer-free performance, security-cost equivalence, or Intrinsic runtime integration. CPU/RSS and wire/FEC observations retain their sampling, capture and population bounds; no unavailable peak, unknown age or missing sample is silently imputed. Configured bridge slots do not prove continuous allocator or kernel occupancy bounds. Recorded protected-profile and negative checks do not establish a general security certification or equivalent DDS encryption/authentication cost.

The historical comparison remains a dated source; later SRT coverage does not make its DDS observations contemporaneous or equivalent. The recommended disposition closes the recorded simulator qualification task only, with these exclusions and residual historical risk attached. It is not a declaration that every prior attempt passed or that no latent shutdown/protocol defect can exist.

## Review artifacts and disposition

The machine-readable [statement](evidence/m3-scoped-acceptance-2026-11-11/statement.json), [source hashes](evidence/m3-scoped-acceptance-2026-11-11/source-reports.json), [reviewed indexes](evidence/m3-scoped-acceptance-2026-11-11/reviewed-indexes.json) and [verification](evidence/m3-scoped-acceptance-2026-11-11/verification.json) bind this review. Earlier frozen ledgers and decisions remain unchanged.

**Disposition prepared: scoped acceptance recommended; formal approval pending. PR2 remains draft, merge is not authorized, all campaign execution is disabled and M4 remains disabled.** No new experiment or tuning is proposed as an automatic next action.
