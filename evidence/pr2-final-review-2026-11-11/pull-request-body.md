## Result and scope

This PR adds reproducible network qualification, conservative publication/accounting diagnostics and bounded command recovery to the ROS 2 SRT bridge. A sender command abandoned before SDK handoff can now reconcile its exact durable row to provisional UNKNOWN instead of remaining locally queued; peer-proved results are preserved, and uncertainty never authorizes replay or forced expiry. Worker start/context fences, bounded default-off tracing, ROS lifecycle visibility and frozen capture/assessment tooling support the recorded qualification.

**M3 is formally accepted only within the documented local Linux amd64/Jazzy simulator scope on the exact pinned instrumented SDK/ROS/provider build. PR2 stays draft and unmerged. Merge/release, all campaign execution and M4/Intrinsic remain disabled.**

## Review entry points

- [Final review guide](https://github.com/Robotweax/ros-2-srt-bridge/blob/dev/m3-network-qualification/PR2_REVIEW_GUIDE.md): implementation map, compatibility boundary, evidence order and reviewer decisions.
- [Formal acceptance decision](https://github.com/Robotweax/ros-2-srt-bridge/blob/dev/m3-network-qualification/M3_ACCEPTANCE_DECISION.md) and [machine-readable baseline](https://github.com/Robotweax/ros-2-srt-bridge/blob/dev/m3-network-qualification/baselines/m3-acceptance.json).
- [Unchanged scoped statement](https://github.com/Robotweax/ros-2-srt-bridge/blob/dev/m3-network-qualification/M3_SCOPED_ACCEPTANCE.md) and [exact matched build record](https://github.com/Robotweax/ros-2-srt-bridge/blob/dev/m3-network-qualification/evidence/m3-scoped-acceptance-2026-11-11/matched-build.json).

Review the source paths before the large evidence archive: journal/ticket/endpoint reconciliation; worker IPC/runtime/supervisor/execution fences; transport/session/retention/tracing; ROS publication/lifecycle; then frozen harnesses and DDS comparison. Private worker IPC is now version 4: SDK consumers, supervisors and ROS workers must be rebuilt together; old peers fail closed. The pinned SRT provider is unchanged. The guide inventories the diff and maps focused tests to these areas; it is not an approving code review.

## Retained validation

All 38 distinct planned case IDs have passing evidence: N0 1, N3 9, N4 19 and LONG N1/N2/N5 9. Six separate frozen series bind the same 14 matched build entries and 87 native inputs, with each harness/observer revision retaining its own scope. They are not one statistical trial or an all-attempt success rate. The completed acceptance review verified 10,085 artifacts and 60 indexes.

Named component reports retain SDK81/ROS41/host399 and later task-assessor integration25/assessor42/existing511 offline passes. These are historical results for their named revisions, not fresh tests on this final-review documentation head. Full case results, raw hashes and public/local export boundaries are linked in the guide. No new live experiment, runtime, build, tuning, retry, expiry forcing or command replay is performed for this preparation.

At pre-preparation head `e14f98c`, GitHub reported no commit-status contexts or PR-triggered workflow runs, and no submitted reviews or inline threads. No branch workflow configuration is present. This does not claim passing hosted CI, required-check satisfaction, branch-protection compliance or human code approval. Those review/merge decisions are separate from scoped M3 acceptance.

## Historical failures and remaining limits

- Preserve the original N3 source-slot/stop-boundary failure and two-loss/4211 shutdown hang, failed N0 readiness/identity/trace attempts, N4 JSON assessor failure, and original N1/2903 missing-stack failure. Its original cohort stays one pass, one failure and seven not executed. Fresh passing series do not rewrite these failures, reconstruct missing stacks or prove the old hang fixed.
- Historical intent118 remains UNKNOWN/reconcile_required and unreplayed. New-session successes do not settle old commands or uniquely establish ARP/qdisc/clock/probe/provider causes.
- N5 retains83 skipped command opportunities and roughly6s adjacent-intent gaps; continuous2s service is not established. Zero SENSOR accounting imbalance is not loss-free delivery. Modeled publication ages do not qualify physical source-to-observer ages.
- DDS age/capture-population/security/resource/topology/observer differences and failed loaded cold startup remain explicit. No general SRT superiority, equivalent DDS pass or steady-window denominator is invented.
- Physical robots, production WANs, cross-host clocks, hard real-time, continuous availability/high-water, whole-stack memory peaks/leak freedom, observer-free performance, general security certification and Intrinsic runtime qualification remain outside acceptance. Large raw captures/full traces remain indexed local-only; public exports are selected.

The previous chronological PR description is preserved verbatim in `evidence/pr2-final-review-2026-11-11/github-before.json`; frozen reports, prior decisions and failure evidence are unchanged. This concise description reflects the final implementation and accepted scope. Keep draft; do not merge, release, enable further campaign execution or start M4 without a separate instruction.
