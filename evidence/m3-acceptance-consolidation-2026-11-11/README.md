# Consolidated M3 acceptance record

The retained matrix contains **37 passing case IDs and one strict failure out of 38**. M3 remains open. Results span separate freezes and harness revisions; they are not a single statistical trial. This record does not waive failures or authorize execution, merge, or M4.

| Coverage | Passing IDs | Remaining gap |
|---|---:|---|
| N0 | 1 | None in recorded scope |
| N3 | 9 | Historical two-loss-4211 failure remains retained |
| N4 | 19 | Historical assessor failure remains retained |
| N1/N2/N5 LONG | 8 | Original N1/2903/600s strict failure |

`acceptance.json` maps every ID to its retained assessment. `evidence-sources.json` binds the source files by SHA-256 and size. `verify_record.py` checks verdicts, counts, immutable original failure, archived history, and absence of milestone/execution authority. `verification.json` records its offline result. Previous root summaries are preserved byte-for-byte under `prior-root-documents/`, indexed by `archived-documents.json`.

The original N1/2903 inner workload passed but strict assessment failed because live target kernel stack evidence was unavailable. The original failure and original cohort (one pass, one failure, seven not executed) remain unchanged. The seven later fresh cases passed separately; their results do not populate or revise the original run. A separately prepared fresh N1/2903 qualification will use new output and journals, not resume the failed run.

Limits remain explicit: local Linux amd64/Jazzy simulator execution under emulation; native ARM64 observer; no physical robot, cross-host or hard real-time qualification, or measured tracing-overhead bound. N5 had 83 skipped command opportunities and roughly six-second maximum adjacent intent gaps, so it does not establish continuous two-second cadence. DDS loaded cold-start failure is a measured outcome; steady-window age/capture populations, security and resource equivalence remain unqualified. No general SRT-over-DDS ranking follows. Task absence metadata does not prove an unseen exit cause or reconstruct original missing stacks. M0–M2 remain accepted only within their recorded scope. PR2 stays draft/unmerged; Intrinsic/M4 has not started.
