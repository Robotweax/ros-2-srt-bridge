# M3 closure plan — 2026-11-11

The [consolidated acceptance record](evidence/m3-acceptance-consolidation-2026-11-11/README.md) maps all 38 planned M3 case IDs to retained verdicts: **37 passing IDs and the original N1/2903 strict failure**. Results span multiple freezes and harness revisions. M3 remains open; [PR2](https://github.com/Robotweax/ros-2-srt-bridge/pull/2) stays draft/unmerged. M0–M2 retain their recorded simulator acceptance; M4/Intrinsic has not started.

A separate [fresh N1/2903/600s qualification](evidence/m3-fresh-n1-2903-preparation-2026-11-11/README.md) is **prepared, not run**, on freeze `b3609d03e5ac`. It uses the unchanged matched build and calibrated harness. No authorization grant exists; all other 37 case IDs and other campaign stages are disabled. No tuning, automatic retries, or historical failure revision is authorized. Execution must await a separate instruction and stop at the first failed gate.

1. Preserve the original failed capture, strict verdict and original cohort. Keep the prepared fresh attempt isolated in its new output directory and journals.
2. If separately authorized, run exactly the prepared N1/2903/600s attempt after quiescent runtime and frozen-input checks. Stop at the first failed gate. No tuning, resume, automatic retry, or additional campaign stage.
3. Retain the result and raw evidence under a new execution package. A failure requires diagnosis from its captures; a pass adds a distinct fresh result while preserving the original failure.
4. Review the complete acceptance record against the stated simulator scope and unresolved limitations. Make an explicit scoped milestone decision; merge and M4 are separate decisions.

The scope remains local Linux amd64/Jazzy simulation under emulation with a native ARM64 observer. Physical robot, cross-host, real-time and tracing-overhead qualification remain open. N5 retained 83 skipped command opportunities and roughly six-second adjacent intent gaps; it does not establish continuous two-second cadence. The DDS loaded cold-start failure remains a measured outcome; unmatched age/capture populations, security and resources prevent a general transport ranking. Task absence metadata does not reconstruct original missing stacks or prove unseen exit causes.

No new DDS tuning or physical/hardware claim is implied by preparing this case. [Current acceptance review](M3_ACCEPTANCE_REVIEW.md); [previous closure history](evidence/m3-acceptance-consolidation-2026-11-11/prior-root-documents/M3_CLOSURE_PLAN.md).
