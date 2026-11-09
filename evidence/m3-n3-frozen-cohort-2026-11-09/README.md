# Strict frozen N3 cohort — 2026-11-09

**FAIL: eight strict passes, final case failed the owned-child shutdown gate.**
No retry, tuning, rebuild, deadline/buffer/source-rate change, forced expiry or
historical command replay. All29 non-N3 campaign cases remain disabled and were
not launched. M3 is not accepted as complete, PR2 stays draft and M4 is untouched.

The user explicitly authorized exactly the strict nine-case N3 cohort. The
original complete campaign freeze matches byte-for-byte before/after all cases:
`sender-reconcile-929d1f7c7727`,13 candidate entries,86 native inputs, preserved
build chain, image/provider, helpers and all frozen source hashes. No frozen tool,
assessor, scenario, native library or binary was changed for this run.

## Execution and stop boundary

The general dispatcher accepts a full38-case grant. To keep this narrower scope,
`run-n3-only.py` uses its unchanged frozen single-case adapters, strict assessor
and stop controller, with a separately hash-bound nine-case grant. It cannot
schedule a non-N3 case. The full38-case freeze was not edited and no38-case grant
was created. Two offline controls, with mocked dispatch, demonstrate nine-only
scope even on complete success and no advancement after strict rejection.
Previous440 Python checks remain retained evidence, not rerun during capture.

Seeds1701,2903,4211 each ran baseline, one-loss, then two-loss,30 nominal source
seconds per case. The strict verdict and recorded cleanup preceded each subsequent
launch. The first failed gate was case9; consequently no N3 slot remained to skip.
The disabled29 N0/N4/N1/N2/N5 slots are explicit in the campaign and grant.

| Case | Strict outcome | Source fence / failure |
|---|---|---|
|N3-baseline-1701|PASSED|30.055706514s; zero skips|
|N3-one-loss-1701|PASSED|30.053640556s; zero skips|
|N3-two-loss-1701|PASSED|30.053400722s; zero skips|
|N3-baseline-2903|PASSED|30.057820014s; zero skips|
|N3-one-loss-2903|PASSED|30.055009847s; zero skips|
|N3-two-loss-2903|PASSED|30.054004389s; zero skips|
|N3-baseline-4211|PASSED|30.05930018s; zero skips|
|N3-one-loss-4211|PASSED|30.057656972s; zero skips|
|N3-two-loss-4211|FAILED|operator bridge shutdown deadline exceeded; forced kill|

The first8 passes include the original zero-skipped-slot and1% source cadence
contract,30..31s fences, source/SDK/typed accounting with six residuals0, native/full
PCAP population and trace footers, selected fault identities/counters/parity,
repair/absence proof and child/lab cleanup. Their fences span30.053400722..
30.059300180s; publication-age histogram upper-bucket maxima are60ms IMU and37ms
joints, below250ms. These are observed publication bounds, not physical sensor
ages, lossless delivery or continuous availability. Per-case missing/reduced
populations remain visible in gate-report.json.

## Failure and cleanup

The two-loss4211 scenario wrote endpoint results and selected-source drop evidence,
then `operator-bridge-0` failed to exit within the existing5s SIGINT shutdown wait.
The retained child report records forced_kill=true, returncode=-9, and about
5.011041044s from signal start to reaping. The robot source and bridge both exited0
without forced kill. The scenario returned nonzero; frozen strict assessment
refused advancement. No internal hang/deadlock cause is established by this run.

Both selected classifiers recorded one drop and were restored. Source/SDK/typed
accounting and measurement-capture revalidation for case9 were not reached after
the child-exit failure, so they are not promoted to PASS from partial results.
The case and cohort stay FAIL even if a later offline analysis finds passing
measurement subgates. No shutdown budget extension or automatic rerun follows.

Recorded cleanup passes for all9 cases. Postflight confirms all owned containers
and networks are absent and no fixture credential remains. The two-loss4211 child
reports and scenario error are copied in failure/. The final failed gate differs
from the older cohort's source-skip failure; neither cohort replaces the other.
All9 older result hashes still match; no old five-case prefix was spliced into
this cohort.

## Retained evidence and next step

- authorization.json, preflight.json and hash-bound driver: exact prospective scope.
- campaign.json and gate-report.json:8 PASS/1 FAIL, stop boundary, disabled stages.
- assessments/: eight original independent strict proof records.
- failure/: original failed result, both child reports and scenario error.
- local-artifact-hashes.json:913 retained local files,301,054,024 bytes, including
  full source/SDK/typed logs, packets, endpoint results and per-case provenance.
- postflight.json: original freeze, owned cleanup and old-result integrity.

The requested execution is complete. Next engineering work is diagnosis of the
operator shutdown failure from retained evidence/source, followed by a separate
fix/validation decision if needed. Do not retry case9, splice cohorts, relax the
5s shutdown or zero-skip gates, or proceed to another campaign stage automatically.
