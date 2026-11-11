# M3 acceptance review — 2026-11-11

The [consolidated acceptance record](evidence/m3-acceptance-consolidation-2026-11-11/README.md) maps all 38 planned M3 case IDs to retained verdicts: **37 passing IDs and the original N1/2903 strict failure**. Results span multiple freezes and harness revisions. M3 remains open; [PR2](https://github.com/Robotweax/ros-2-srt-bridge/pull/2) stays draft/unmerged. M0–M2 retain their recorded simulator acceptance; M4/Intrinsic has not started.

A separate [fresh N1/2903/600s qualification](evidence/m3-fresh-n1-2903-preparation-2026-11-11/README.md) is **prepared, not run**, on freeze `b3609d03e5ac`. It uses the unchanged matched build and calibrated harness. No authorization grant exists; all other 37 case IDs and other campaign stages are disabled. No tuning, automatic retries, or historical failure revision is authorized. Execution must await a separate instruction and stop at the first failed gate.

| Planned coverage | Passing distinct IDs | Recorded outstanding gap |
|---|---:|---|
| N0 baseline | 1 | None within recorded scope |
| N3 repair | 9 | Historical shutdown failure retained separately |
| N4 interruption | 19 | Historical assessor failure retained separately |
| N1/N2/N5 LONG | 8 | Original N1/2903/600s strict failure |
| Total | 37 / 38 | One distinct slot without a passing result |

The original N1/2903 workload passed its inner checks but failed strict assessment (`live target kernel stack unavailable`). Its assessment SHA-256 remains `e9cf84c7b6beffe584cfc06134d44c263b4884fcf166b3e113a7430cdedd7d30`. Its original cohort remains one pass, one failure and seven not executed. The seven later fresh cases passed in a separate cohort, and do not fill the old run directories or replace its verdicts.

The scope remains local Linux amd64/Jazzy simulation under emulation with a native ARM64 observer. Physical robot, cross-host, real-time and tracing-overhead qualification remain open. N5 retained 83 skipped command opportunities and roughly six-second adjacent intent gaps; it does not establish continuous two-second cadence. The DDS loaded cold-start failure remains a measured outcome; unmatched age/capture populations, security and resources prevent a general transport ranking. Task absence metadata does not reconstruct original missing stacks or prove unseen exit causes.

The machine-readable [matrix](evidence/m3-acceptance-consolidation-2026-11-11/acceptance.json), [source hashes](evidence/m3-acceptance-consolidation-2026-11-11/evidence-sources.json) and [offline audit](evidence/m3-acceptance-consolidation-2026-11-11/verification.json) are authoritative for this snapshot. Prior root summaries are [archived byte-for-byte](evidence/m3-acceptance-consolidation-2026-11-11/archived-documents.json). The [historical comparison](M3_COMPARISON_AND_ACCEPTANCE.md) remains available with its limitations. A future fresh pass would add evidence; it would not erase failure history or automatically accept M3, merge PR2, or start M4.
