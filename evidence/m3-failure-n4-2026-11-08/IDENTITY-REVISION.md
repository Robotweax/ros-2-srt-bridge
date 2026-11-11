# Separate N4 fixture identity revision

The original40bf968 N4 cohort FAILED its first admission/both case before any
outage was installed: the peer's strict kernel-executable/stopped-state child
lookup could not identify the paused worker. Remaining eight cases are unexecuted.
Original logs/verdicts remain unchanged. This is fixture failure, not passing N4
or proof of a production endpoint defect. Original lookup did not record its
rejected child metadata, so exact failure mechanism is not retrospectively proven.

The standalone test peer now bounds its paused-child readiness wait to1s and
uses its actual /proc thread child ownership, exact installed worker argument +
IPC mode tokens, stopped state and PID/start-tick identity before SIGCONT. It
records kernel executable path/match and child facts; emulation may expose an
emulator path through /proc/exe. Multiple matching stopped children fail closed.
No production SDK/API/worker/ROS/network/deadline/outcome gate changed. The
standalone fixture binary is rebuilt Release/Werror; current host229 passed.

Commit this source and plan, then run the same nine phase/direction cases once in
a separate root:
`python3 tools/m3_n4.py --output .local/m3-failure-n4/n4-identity`
Stop at first unexpected failure, retaining that new original result and leaving
remaining cases unexecuted. All PLAN.md and N4-FREEZE.md gates stay mandatory.
This is a separately planned corrected-fixture cohort, not a replacement first
cohort or cause proof. No more live runs are specified by this revision.
