# Separate child-lifecycle diagnostic after original failed run

The original cb2468b/seed1701 execution remains FAILED: sender footer complete,
receiver2427 trace lines but no final SAMPLE_TRACE_STATUS. Legacy cleanup does not
record child exit code or whether its five-second wait forced a kill. No original
child exit/kill event was recorded, so its process/shutdown cause is UNKNOWN.
Original seed2903/4211 cases are NOT EXECUTED: stop-on-first-failure applies.
Post-hoc accounting/capture diagnostics do not qualify or replace that failed run.

After218 host tests and syntax checks pass, commit this separate diagnostic plan
and source. Execute exactly once:
`python3 tools/m3_ros_multiroute.py --output .local/m3-multiroute-two-loss/lifecycle-1701 --capture --losses 2 --seed 1701`
No other live execution or retry is authorized by this diagnostic plan. Same pinned
seven runtime artifacts, nominal ten-second200/50Hz source, source/sample traces,
fixed message7/8 classifier and all original two-loss/source/accounting/capture
gates. No production, SDK/provider, ROS C++ or source schedule change. The added
Python child-lifecycle observations occur during post-window cleanup.

New controlled cleanup records each owned child's pre-signal poll result, VM
SIGINT bracket, final exit code, forced-kill flag and time bounds. A preexisting
exit (even0), nonzero exit, deadline or kill is a failure; all owned children are
still cleaned. SIGINT wait remains five seconds. A bounded five-second kill wait
and host peer wait25s ensure abnormal cleanup can be reported for two children;
no production or measurement deadline is changed. Preserve child-shutdown reports
and scenario errors even if the trace/footer gate cannot be reached. Require clean
controlled shutdown and one complete final source/sample trace status per process
for a passing diagnostic; never synthesize/append a missing status.

If the diagnostic passes, it is independent evidence under the stronger observed
cleanup, not proof of the original failure's cause or a replacement original seed
cohort. If it fails, preserve the actual exit/kill outcome and stop live work under
this plan. Any subsequent measurement needs a new frozen plan justified by the
recorded findings. Raw capture/resource/journal contents stay local, original
verdicts/logs remain untouched, owned fixtures/credentials are removed. Full N3,
remaining seed cases, N4/M3 and Intrinsic/M4 stay incomplete.
