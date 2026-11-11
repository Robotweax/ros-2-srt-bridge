# M3 acceptance decision — 2026-11-11

**M3 is formally accepted within the documented local Linux amd64 / ROS Jazzy simulator scope, on the exact matched instrumented SDK/ROS build and pinned SRT provider.** This records the user's explicit approval of the [scoped acceptance statement](M3_SCOPED_ACCEPTANCE.md), reviewed at commit `a99d7ba`. The statement's evidence boundaries, historical failures and remaining limitations are part of this decision without qualification being broadened.

PR2 remains **draft and unmerged**. M4/Intrinsic and all campaign execution remain **disabled**. This acceptance authorizes no merge, release, deployment, new experiment, tuning, automatic retry, forced expiry, journal recovery or historical command replay. M0–M2 keep their existing scoped acceptance.

## Accepted scope and evidence

The accepted evidence comprises 38 distinct planned case IDs: N0 baseline (1), deterministic N3 repair (9), bounded N4 interruption/freshness/crash cases (19), and N1/N2/N5 LONG cases (9). Six separately frozen series bind the same 14 matched build entries and 87 native inputs. Their harness, fixture and observer revisions retain their respective recorded scopes; they are not one statistical trial or an all-attempt pass rate.

The accepted installed layout is `install/bridge-socket-disposition` with `install/m3-socket-disposition-ros`. Exact artifact hashes, image identities and per-series freeze hashes are in the [machine-readable decision](baselines/m3-acceptance.json) and [matched build record](evidence/m3-scoped-acceptance-2026-11-11/matched-build.json). Provider revision is `52be7c86ee1f303cbb0c8718c364217e4dd97a36`; archive SHA-256 is `3fa56e487e6c6408d9e41779d18aba9ff866978892ddbe3b88ac12fc51141673`. Acceptance does not automatically transfer to rebuilt or modified artifacts.

The retained review verified 10,085 artifacts and 60 indexes. This decision records approval of that review and checks its hashes and the original failure references; it does not rerun native tests or packet validators. Large raw captures/full traces retain their indexed local-only boundary; selected proofs remain public.

## Preserved failures and limits

Historical N3 source-slot/stop-boundary and two-loss/4211 shutdown failures, N0 launch/readiness/identity/trace failures, N4 JSON assessor failure, and original N1/2903 missing-stack failure remain unchanged. The original N1 failed assessment remains SHA-256 `e9cf84c7b6beffe584cfc06134d44c263b4884fcf166b3e113a7430cdedd7d30`; its cohort remains one pass, one failure and seven not executed. Separate fresh passes do not repair old verdicts, reconstruct missing stacks or prove the original shutdown hang fixed. Historical intent 118 remains UNKNOWN/reconcile_required and is not replayed or declared resolved.

N5's 83 skipped command opportunities and roughly six-second adjacent-intent gaps remain explicit; continuous two-second service is not established. SENSOR accounting closure is not loss-free delivery. Publication-age claims retain the original model/clock/population assumptions and do not certify physical source-to-observer age. Fixed bridge slots do not establish continuous queue high-water or whole-stack memory peaks.

DDS age/capture-population, security, resource, topology and observer limits remain attached. The loaded default-DDS cold-start failure supplies no steady-window denominator. No general SRT superiority, equivalent DDS pass or requirement to tune DDS follows. Physical robots, production WANs, cross-host clocks, hard real-time motion, continuous availability, leak freedom, observer-free performance, general security certification and Intrinsic runtime qualification remain outside this acceptance.

The complete failure history and exclusions in [M3_SCOPED_ACCEPTANCE.md](M3_SCOPED_ACCEPTANCE.md) are incorporated into this decision. The earlier proposal, review, frozen cohorts and comparison statements remain unchanged as dated records. Their pending/failed labels describe their original state; this separate decision closes M3 only within the stated scope.

## Recorded disposition

**Accepted within documented scope. PR2 draft/unmerged; no merge or release authorized; all campaign execution and M4 disabled.** The [decision package](evidence/m3-acceptance-decision-2026-11-11/README.md) binds the approval, prior review and integrity checks. No additional development or experiment is started by this decision.
