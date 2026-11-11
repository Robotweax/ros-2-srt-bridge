# M3 closure disposition — 2026-11-11

The retained-evidence review is complete and the [scoped acceptance statement](M3_SCOPED_ACCEPTANCE.md) is prepared. It recommends accepting the recorded simulator qualification on the exact matched instrumented build, while preserving historical failures and explicit limitations. All 38 planned distinct IDs have passing evidence across separate freezes and harness revisions; they are not an all-attempt pass rate or a single statistical trial.

1. Formal scoped milestone acceptance is the remaining decision. This prepared statement does not grant approval or waive historical failures.
2. PR2 remains draft/unmerged. Any later merge or release decision must preserve the exact evidence/build scope and exclusions.
3. All campaign execution and M4/Intrinsic remain disabled. No new experiment, tuning, automatic retry, forced expiry or historical replay is queued. Subsequent integration scope requires a separate instruction.

Historical shutdown causes, original stack-evidence failures, N5 scheduling gaps, unresolved historical command results and DDS age/capture/security/resource limitations remain explicit in the statement. Hardware, production WAN, hard real-time, cross-host clocks, whole-stack memory peaks and observer-free performance are unqualified. These restrict acceptance claims; they do not authorize further work or invent a requirement to make DDS pass.

The [review package](evidence/m3-scoped-acceptance-2026-11-11/README.md) records hash verification of 10,085 retained artifacts and 60 indexes, identical 14 build entries/87 native inputs across six series, the 38-ID verdict mapping and preserved original N1 failure/cohort. Previous frozen statements and ledgers remain unchanged.
