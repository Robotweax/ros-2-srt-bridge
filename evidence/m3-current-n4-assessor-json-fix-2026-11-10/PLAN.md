# N4 crash assessor JSON boundary fix — offline only

**10 new regressions,20 preparation tests and511 existing tests PASS.** The
candidate assessor consistently reassesses all17 retained started cases offline.
The original assessor still reproduces `ROS crash audit differs`. Original live
cohort decisions remain16 PASS/1 FAIL/2 NOT EXECUTED; no failed run is relabelled.
No live cases, Docker calls, builds, tuning, automatic retries, new freeze or
execution grant. Two remaining N4 crash cases and nine other unexecuted campaign
cases stay disabled; completed10 N0/N3 cases excluded. M3 open/PR2 draft/M4 untouched.

## Change

The frozen assessor compared freshly recomputed Python crash proof dictionaries
with dictionaries loaded from result.json. Command trace point_names/reason_names
use integer keys in memory, which JSON serializes as strings. The real retained
crash-before case therefore passed check_crash but failed persisted-proof equality.

This separate assess.py candidate changes only that comparison boundary: it
JSON-round-trips the recomputed crash proof, then requires exact equality with
the saved proof. Nonfinite recomputed values are refused via allow_nan=False.
There is no filtering of proof fields, outcome substitution, relaxed equality,
new execution authority or change to check_crash. Source/build provenance,
phase/deadline/effect/replay checks, native and freshness assessments, shutdown
and cleanup are unchanged. No baseline tools or frozen preparations were edited.
assessor-binding.json records exact original and candidate paths/hashes.

The candidate is not silently selected by any live driver. This package has no
execution driver or authorization file. A separate future preparation must bind
its exact bytes to a fresh freeze before any explicitly authorized live use.
The stopped freeze and grant cannot resume or retry the failed case.

## Regression coverage

The tests exercise the actual candidate assess_case with persisted result.json
boundaries and controlled crash-check proofs for before/effect/committed modes.
They reproduce failure with the original assessor and include the actual retained
command trace schema. They verify proof immutability and stable second JSON
persistence. Changed journal hashes, deadlines, state/reason/result validity,
effects, trace counts/completeness/name mappings, controlled crash/exit evidence,
and request identity remain rejected. Missing/extra/reordered evidence, original
checker exceptions, failed inner result/shutdown and nonfinite proof values are
refused; failed checks cannot reach cleanup/success. Exact source comparison
limits the candidate change to the crash JSON boundary.

These synthetic comparisons do not run check_crash for effect/committed live
cases or qualify those unexecuted cases. The actual retained17-case audit below
covers the real production checkers and raw files available from the stopped run.

## Retained assessment and integrity

validation/reassess_retained.py calls the actual candidate assessor over each of
the17 closed outputs:13 native phase cases,3 ROS freshness cases and crash-before.
All17 return passed as offline consistency results. It separately reproduces the
original strict crash comparison failure. It never launches or dispatches a case,
writes into retained runs or changes original strict/cohort decisions. The last
two absent case directories are explicitly checked, not supplied synthetic runs.
retained-reassessment.json retains all original statuses and diagnostic results.

Before and after assessment, source/input/current14/preserved13/full native SDK/
ROS/provider chain/native87/fixture37 and all retained public/raw hashes are
verified. The exact original cohort and17 strict decision files remain unchanged.
The frozen preparation and execution package indexes verify unchanged, including
all1018 raw files from the stopped run. No production/helper/worker/ROS workload,
rate, queue, clock, wait, observer/filter or gate tuning. Offline checks do not
establish live scheduling, new crash recovery, physical outcome or M3 acceptance.

input-hashes.json binds code and prior indexes; public-artifact-hashes.json binds
this complete package and logs. postflight.json records offline verification only.
The existing511-test and preparation20-test logs are new offline runs; prior live
results and all historical failures retain their original scope.
