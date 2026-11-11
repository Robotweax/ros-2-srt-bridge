# Fresh N1/2903/600s qualification — prepared only

One separately scoped N1/2903 combined case, 600 seconds, using the unchanged matched SDK/ROS build and calibrated task visibility harness. All other 37 case IDs and other campaign stages are disabled. No authorization file is created. No execution, tuning, retry, build, or historical verdict change occurs in preparation.

The original failed assessment and cohort are hash-bound and retained. New output, journals, container prefix and read-only six-file observer bundle are isolated from all historical runs. Existing output is refused; the driver has no resume or automatic retry. Execution requires a separately supplied exact authorization for this freeze, a quiescent runtime, immutable input checks, and stops at the first failed gate. The 600-second source window retains the existing 840-second host watchdog and five-second child wait.

`case-plan.json`, `freeze.json` and `readiness.json` declare the scope and disabled execution state. `run.py` is the guarded entry point; do not invoke it during preparation. `plan.py` defines the exact future authorization shape, not an authorization grant. Existing grants for older campaigns and calibrations are rejected.

27 offline regressions cover exact scope, prior-grant rejection, immutable failure reference, acceptance ledger consistency, calibrated metadata assessment, runtime import order, fail-stop behavior, cleanup, watchdog and provenance checks. Mocked driver and retained/model assessment checks do not constitute a native 600-second run. Earlier calibration/test logs remain bound through retained indexes; their counts are not new test executions.

The immutable consolidated acceptance record is under `evidence/m3-acceptance-consolidation-2026-11-11/`. M3 remains open pending this gap and a scoped milestone decision. Historical failure is preserved regardless of a future fresh result. PR2 remains draft; M4/Intrinsic is disabled.
