# Delivery plan — 2026-11-11

**M3 is formally accepted within the documented local simulator/build scope.** The [acceptance decision](M3_ACCEPTANCE_DECISION.md) records the user’s explicit approval of the unchanged [scoped statement](M3_SCOPED_ACCEPTANCE.md), with historical failures and remaining limitations attached. PR2 stays draft/unmerged; all campaign execution and M4 remain disabled. No merge, release, experiment, tuning or retry is authorized by this decision.

The [fresh N1/2903/600s qualification](evidence/m3-fresh-n1-2903-execution-2026-11-11/README.md) **passed** on one invocation of freeze `b3609d03e5ac`. The latest [acceptance update](evidence/m3-fresh-n1-2903-execution-2026-11-11/acceptance-update.json) now records passing evidence for **all 38 planned distinct M3 case IDs**, across separate freezes and harness revisions. The original N1/2903 strict failure and original one-pass/one-fail/seven-not-executed cohort remain immutable. Historical failures are not overwritten.

M3 completion applies only to the exact accepted simulator/build evidence; [PR2](https://github.com/Robotweax/ros-2-srt-bridge/pull/2) remains draft/unmerged, and M4/Intrinsic has not started. No next run or stage is enabled. Historical failures are preserved.

| Milestone | State |
|---|---|
| M0 transport / M1 command contracts / M2 ROS simulator | Accepted within recorded local scope |
| M3 measured network qualification | Formally accepted within documented simulator/build scope |
| M4 Intrinsic integration | Not started; disabled |

The scoped acceptance decision is recorded. No further execution, merge, release or integration step is enabled; subsequent work requires a separate instruction and must preserve the accepted evidence boundaries.

Scope remains local Linux amd64/Jazzy simulation under emulation with a native ARM64 observer. Physical robot, cross-host, real-time and tracing-overhead qualification remain open. N5 retained 83 skipped command opportunities and roughly six-second adjacent intent gaps; it does not establish continuous two-second cadence. DDS loaded cold-start failure remains a measured outcome, with unmatched age/capture populations, security and resources preventing a general transport ranking. Fresh observer evidence does not reconstruct the original missing stack or explain historical hangs.

See [acceptance review](M3_ACCEPTANCE_REVIEW.md) and [closure plan](M3_CLOSURE_PLAN.md).
