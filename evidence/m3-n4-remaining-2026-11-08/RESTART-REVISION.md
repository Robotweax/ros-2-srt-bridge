# Separate restart observer/lifetime diagnostic

Original c70de04 native suite passes4 and ROS freshness suite passes3, independent
of the original crash suite. Its first before-admission case FAILED: sender did
not regain a qualified new session within40s. Restarted receiver command prefix
shows EndpointFault::worker shortly after startup; exact WorkerFault/old worker
exit were not retained. Later effect/committed cases were NOT EXECUTED. Preserve
all original logs/verdicts, no successful cohort replaces them and no N5 work.

Found fixture defect: live SQLite inspection used a connection context manager,
which handles transactions but does not explicitly close connections. The helper
now uses contextlib.closing and a regression verifies closure even if an external
reference survives. This removes a potential observer lock/lifetime interference;
the original metadata cannot prove it was the sole failure cause.

Also record every receiver/sender state transition's owner/session/worker fault;
fail promptly on an unexpected worker fault. After deliberately killing a bridge,
record its owned worker PID and require that worker to exit or reach zombie state
within5s before launching a replacement. An orphan still running fails the fixture,
not silently killed/rescued. Handle host abort through controlled child cleanup
so failed fixtures retain final metadata. No production/runtime change or rebuild.

After237 host tests and syntax/diff checks pass, freeze source/plan and run exactly
once in a separate root:
`python3 tools/m3_n4_ros.py --output .local/m3-n4-remaining/crashes-observer --crashes`
Same ordered before/effect/committed cases, same original5s budget, one Execute
handoff, persistent external device/journal, new owner/session and10s QUERY-only
post-reconnect observations, all original crash/outcome/unknown/cleanup gates.
Stop at first unexpected failure and leave remaining cases unexecuted. No other
live run/retry or relaxed production/watchdog/deadline/gate is specified. This is
independent corrected-fixture evidence, not an attribution or repaired old result.
