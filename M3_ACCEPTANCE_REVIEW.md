# M3 acceptance review — 2026-11-11

**M3 is formally accepted within the documented local simulator/build scope.** The [acceptance decision](M3_ACCEPTANCE_DECISION.md) records the user’s explicit approval of the unchanged [scoped statement](M3_SCOPED_ACCEPTANCE.md), with historical failures and remaining limitations attached. PR2 stays draft/unmerged; all campaign execution and M4 remain disabled. No merge, release, experiment, tuning or retry is authorized by this decision.

The [fresh N1/2903/600s qualification](evidence/m3-fresh-n1-2903-execution-2026-11-11/README.md) **passed** on one invocation of freeze `b3609d03e5ac`. The latest [acceptance update](evidence/m3-fresh-n1-2903-execution-2026-11-11/acceptance-update.json) now records passing evidence for **all 38 planned distinct M3 case IDs**, across separate freezes and harness revisions. The original N1/2903 strict failure and original one-pass/one-fail/seven-not-executed cohort remain immutable. Historical failures are not overwritten.

M3 completion applies only to the exact accepted simulator/build evidence; [PR2](https://github.com/Robotweax/ros-2-srt-bridge/pull/2) remains draft/unmerged, and M4/Intrinsic has not started. No next run or stage is enabled. Historical failures are preserved.

| Planned coverage | Passing distinct IDs |
|---|---:|
| N0 baseline | 1 |
| N3 repair | 9 |
| N4 interruption | 19 |
| N1/N2/N5 LONG | 9 |
| Total | 38 / 38 |

The fresh N1/2903 source window was 600.123054899 seconds: 300/300 successful commands and matching effects, no UNKNOWN/unresolved/not-admitted or skipped slots; six SENSOR balances zero; publication-age upper bounds 224 ms IMU / 235 ms joints below 250 ms. Observer: 100 readable stacks, zero unavailable reads, 19 supported task absences, with clean unforced positive-launch shutdowns. Frozen integrity and independent cleanup checks pass.

The original failed assessment SHA-256 remains `e9cf84c7b6beffe584cfc06134d44c263b4884fcf166b3e113a7430cdedd7d30`; its inner workload passed but strict assessment failed (`live target kernel stack unavailable`). Today's fresh pass adds separate evidence and does not reinterpret that failure. Historical N3 shutdown and N4 assessor failures likewise remain retained.

Scope remains local Linux amd64/Jazzy simulation under emulation with a native ARM64 observer. Physical robot, cross-host, real-time and tracing-overhead qualification remain open. N5 retained 83 skipped command opportunities and roughly six-second adjacent intent gaps; it does not establish continuous two-second cadence. DDS loaded cold-start failure remains a measured outcome, with unmatched age/capture populations, security and resources preventing a general transport ranking. Fresh observer evidence does not reconstruct the original missing stack or explain historical hangs.

The immutable [pre-attempt consolidation](evidence/m3-acceptance-consolidation-2026-11-11/README.md) remains the 37-pass/one-failure snapshot bound by this freeze. The [new verdict mapping](evidence/m3-fresh-n1-2903-execution-2026-11-11/acceptance-update.json), [source hashes](evidence/m3-fresh-n1-2903-execution-2026-11-11/acceptance-sources.json) and [audit](evidence/m3-fresh-n1-2903-execution-2026-11-11/acceptance-audit.json) record the subsequent 38-ID coverage. See [closure steps](M3_CLOSURE_PLAN.md) and [historical comparison](M3_COMPARISON_AND_ACCEPTANCE.md). The separate [formal decision](M3_ACCEPTANCE_DECISION.md) accepts M3 within this scope; no merge, release or M4 is authorized.
