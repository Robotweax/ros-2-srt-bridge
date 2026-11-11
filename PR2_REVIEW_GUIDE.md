# PR2 final review guide — 2026-11-11

PR2 packages M3 network qualification, bounded command recovery, diagnostics and the retained evidence record. **M3 is formally accepted only within the documented simulator/build scope. PR2 remains draft and unmerged; final code review is outstanding. M4/Intrinsic and all campaign execution remain disabled.** No merge, release, new experiment, tuning or automatic retry is authorized by preparing this review.

## Start with the accepted scope

Read [M3_ACCEPTANCE_DECISION.md](M3_ACCEPTANCE_DECISION.md) and [baselines/m3-acceptance.json](baselines/m3-acceptance.json), then the unchanged [scoped statement](M3_SCOPED_ACCEPTANCE.md). The acceptance binds the exact instrumented SDK/ROS/provider build, six separate frozen series and 38 distinct passing case IDs. It is not an all-attempt pass rate, a single statistical trial, approval of rebuilt artifacts or a general SRT-over-DDS conclusion.

The accepted review verified 10,085 artifacts and 60 indexes; identical 14 matched build entries and 87 native inputs are recorded in [matched-build.json](evidence/m3-scoped-acceptance-2026-11-11/matched-build.json). The approval step checked review hashes without rerunning that complete audit. Final-review preparation adds documentation and metadata only; retained native/campaign validation is not a new test execution or hosted CI result.

## Review implementation before the evidence archive

The pre-preparation diff at `e14f98c9a6f3803e13b0c1c9d23668ad18b4f336`, against base `32c53b27839182ec45c448694c60fe1691466118`, contains 13,787 changed files: 13,491 evidence files and 296 other files. [diff-inventory.json](evidence/pr2-final-review-2026-11-11/diff-inventory.json) inventories all non-evidence files and groups the evidence packages. The final-review documentation is additional to that snapshot. This is a navigation inventory, not a line-by-line code approval.

| Review area | Primary files | Focus / retained validation |
|---|---|---|
| Sender receipt and journal recovery | [ticket.hpp](src/robotweax_srt_bridge_core/include/robotweax/srt_bridge/ticket.hpp), [endpoint.cpp](src/robotweax_srt_bridge_transport/endpoint.cpp), [journal.cpp](src/robotweax_srt_bridge_core/src/journal/journal.cpp) | One-use exact-row reconciliation, bounded receipt tracking/BUSY behavior, provisional UNKNOWN, delayed receipt cannot overwrite peer proof. [Sender reconciliation evidence](evidence/m3-sender-reconciliation-2026-11-09/README.md); [receipt tests](tests/native/sender_receipt_tests.cpp), [journal tests](tests/protocol/journal_tests.cpp). |
| Worker and execution fences | [ipc.hpp](src/robotweax_srt_bridge_core/src/worker/ipc.hpp), [runtime.cpp](src/robotweax_srt_bridge_core/src/worker/runtime.cpp), [supervisor.cpp](src/robotweax_srt_bridge_core/src/worker/supervisor.cpp), [execution_pool.cpp](src/robotweax_srt_bridge_core/src/worker/execution_pool.cpp) | Owner/generation/context/start-deadline checks and query-first UNKNOWN semantics. [Execution start tests](tests/native/execution_start_tests.cpp), [worker tests](tests/protocol/worker_tests.cpp). Private worker IPC is version 4; supervisors, SDK consumers and ROS workers must be rebuilt together. Old IPC peers fail closed. |
| Transport and diagnostics | [transport.cpp](src/robotweax_srt_bridge_core/src/transport/transport.cpp), [receiver_retention.hpp](src/robotweax_srt_bridge_core/src/transport/receiver_retention.hpp), [session.cpp](src/robotweax_srt_bridge_core/src/session.cpp), [shutdown_trace.hpp](src/robotweax_srt_bridge_core/include/robotweax/srt_bridge/shutdown_trace.hpp) | Retention/clock/deadline behavior; bounded default-off traces; diagnostics must not grant authority, bypass fences or reinterpret unavailable evidence. [Retention](tests/native/receiver_retention_tests.cpp), [probe](tests/native/probe_trace_tests.cpp), [shutdown trace tests](tests/protocol/shutdown_trace_tests.cpp). |
| ROS publication and lifecycle | [bridge_node.cpp](ros2/robotweax_srt_bridge/src/bridge_node.cpp), [ros_worker.cpp](ros2/robotweax_srt_bridge/src/ros_worker.cpp), [messages/services](ros2/robotweax_srt_bridge_msgs), [simulator scenarios](ros2/robotweax_srt_bridge_demo/scripts) | Publication authorization/metrics, launch identity, warmup/restart and per-launch shutdown trace ownership. [N0 lifecycle evidence](evidence/m3-current-n0-stable-execution-2026-11-10/README.md), [N4 cohort](evidence/m3-current-n4-corrected-execution-2026-11-10/README.md). |
| Qualification and capture tooling | [tools](tools), [frozen fresh N1 harness](evidence/m3-fresh-n1-2903-preparation-2026-11-11), [integrated assessor](evidence/m3-campaign-task-assessment-integration-2026-11-10/README.md) | Exact grants, first-failed-gate stop, no resume/retry, private bound imports, independent task identity/absence evidence, profile/capture/cleanup gates. Historical harnesses remain dated records; generic runners do not replace frozen assessors. |
| DDS comparison | [dds_command_node.cpp](ros2/robotweax_srt_bridge/src/dds_command_node.cpp), [DDS profiles](containers), [historical comparison](M3_COMPARISON_AND_ACCEPTANCE.md) | Keep default and paced configurations separate; preserve failed startup, rejected ages and capture discrepancies. No matched security/resource/cost ranking. |

## Follow the acceptance evidence in order

| Record | Credit and limit |
|---|---|
| [Fresh N3](evidence/m3-strict-n3-execution-2026-11-10/README.md) | 9/9 deterministic selected DATA-loss cases. Original skip/stop-boundary failure and separate two-loss/4211 shutdown hang remain failed. |
| [Stabilized N0](evidence/m3-current-n0-stable-execution-2026-11-10/README.md) | One 300-second combined case; original readiness/identity/trace failures remain retained. |
| [Corrected N4](evidence/m3-current-n4-corrected-execution-2026-11-10/README.md) | 19 bounded native/ROS cases, including correct UNKNOWN crash outcomes. Original 16-pass/one-fail/two-unexecuted assessor cohort is unchanged. |
| [Original LONG](evidence/m3-current-long-execution-2026-11-10/README.md) | Passing credit only for N1/1701. Original N1/2903 strict missing-stack failure and stopped cohort remain unchanged. |
| [Fresh remaining seven](evidence/m3-current-remaining-execution-2026-11-11/README.md) | Seven distinct N1/N2/N5 passes; N5 retains 83 skipped opportunities and roughly six-second adjacent-intent gaps. |
| [Fresh N1/2903](evidence/m3-fresh-n1-2903-execution-2026-11-11/README.md) | Separate 600-second strict pass; does not reconstruct or repair the original missing stack. |
| [Acceptance review](evidence/m3-scoped-acceptance-2026-11-11/README.md) and [formal decision](evidence/m3-acceptance-decision-2026-11-11/README.md) | Latest verdict/source mapping and explicit user approval within scope. Earlier pending/failed milestone statements are dated history. |

Historical intent 118 remains UNKNOWN/reconcile_required and unreplayed. Fresh successes do not establish its outcome, explain the original shutdown hang, or uniquely attribute clock/probe/ARP/qdisc/provider failures. Accounting closure is not loss-free delivery. Age results retain their modeled bridge-publication/clock/population assumptions; they are not physical source-to-observer ages. Large raw captures and full traces remain indexed local-only; selected proofs and closed synthetic simulator journals are public, not every raw file.

## Checks and review state

At reviewed head `e14f98c`, GitHub reports draft/open/unmerged and mergeable, with no submitted reviews or inline threads. The status endpoint returned no commit-status contexts and the workflow endpoint returned no PR-triggered runs. No `.github/workflows` directory is present in this branch. These observations do not establish passing hosted CI, required-check satisfaction, branch-protection compliance or approval to merge. The workflow endpoint is scoped to PR-triggered runs; it is not an audit of every external check provider.

Retained validation includes SDK 81 / ROS 41 / host 399 in the sender-reconciliation component report, and later 25 integration / 42 assessor / 511 existing offline tests in the task-assessor integration report. Those counts refer to their named historical revisions, not fresh tests on the final PR head. Live calibration and 38-ID campaign results retain their exact builds, freezes and assessors. This preparation performs document/link/hash/inventory checks only; it starts no runtime or validation campaign.

## Final reviewer decisions

- Review the implementation and private IPC compatibility boundary, including boundedness, exact-row fences, authoritative result preservation and diagnostic authority isolation.
- Confirm the accepted scope and retained validation apply to the reviewed artifacts; distinguish the host documentation head from the accepted native build hashes.
- Preserve every failed/UNKNOWN/unexecuted historical record, N5 cadence losses, DDS gaps and selected-public/local-raw boundary.
- Carry hardware, production WAN, cross-host-clock, hard-real-time, continuous availability/high-water/memory-peak, overhead and general security exclusions into any later release discussion.
- Treat human code approval and any required hosted checks as outstanding decisions. This guide is not an approving PR review, does not request reviewers automatically and does not authorize merge or M4.
