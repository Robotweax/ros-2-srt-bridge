# M3 acceptance review — 2026-11-11

The complete retained-evidence review is finished. The [proposed scoped M3 acceptance statement](M3_SCOPED_ACCEPTANCE.md) recommends accepting the recorded local simulator qualification on the exact pinned instrumented build, with historical failures and limitations attached. **Formal acceptance remains pending; PR2 stays draft/unmerged, all campaign execution and M4 remain disabled.** No new experiment, tuning or retry was performed or authorized.

The [fresh N1/2903/600s qualification](evidence/m3-fresh-n1-2903-execution-2026-11-11/README.md) **passed** on one invocation of freeze `b3609d03e5ac`. The latest [acceptance update](evidence/m3-fresh-n1-2903-execution-2026-11-11/acceptance-update.json) now records passing evidence for **all 38 planned distinct M3 case IDs**, across separate freezes and harness revisions. The original N1/2903 strict failure and original one-pass/one-fail/seven-not-executed cohort remain immutable. Historical failures are not overwritten.

M3 remains open pending an explicit scoped acceptance decision; [PR2](https://github.com/Robotweax/ros-2-srt-bridge/pull/2) remains draft/unmerged, and M4/Intrinsic has not started. No next run or stage is enabled. No tuning or automatic retries occurred.

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

The immutable [pre-attempt consolidation](evidence/m3-acceptance-consolidation-2026-11-11/README.md) remains the 37-pass/one-failure snapshot bound by this freeze. The [new verdict mapping](evidence/m3-fresh-n1-2903-execution-2026-11-11/acceptance-update.json), [source hashes](evidence/m3-fresh-n1-2903-execution-2026-11-11/acceptance-sources.json) and [audit](evidence/m3-fresh-n1-2903-execution-2026-11-11/acceptance-audit.json) record the subsequent 38-ID coverage. See [closure steps](M3_CLOSURE_PLAN.md) and [historical comparison](M3_COMPARISON_AND_ACCEPTANCE.md). No automatic milestone acceptance, merge or M4 follows.
