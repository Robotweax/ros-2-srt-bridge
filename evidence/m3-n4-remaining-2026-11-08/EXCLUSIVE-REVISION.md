# Respect exclusive journal ownership during restart fixture inspection

The observer-revision before case reaches a new ready/clock-qualified receiver with
worker_fault0 (now recorded), but FAILED during final fixture inspection with
sqlite3.OperationalError: database is locked. Later effect/committed cases were
unexecuted. The production journal uses exclusive SQLite locking intentionally.
A fresh reader can fail while the active worker owns it; that is not permission
to weaken production locking or to invent an empty/missing record.

Correct the fixture only: final observations inspect journals after normal child
shutdown. Before/committed whole-bridge crashes inspect old journal state after
the old owned worker has exited. Before-case pre-kill ground truth remains the
active100% cut, SDK handoff1, effects0; absent journal is checked at that crash
boundary with no intervening receive/execute path.

For after-effect-before-commit, observe external effects1, SIGSTOP the exact owned
ROS rate worker, verify stopped child/PID identity, copy its now-stable DB and WAL
to a private local directory, inspect only that copy and require DISPATCHING.
Then SIGKILL the same stopped worker. No application recovery API runs on the live
journal and no original DB/WAL is changed by inspection. The copy can undergo
SQLite WAL recovery only (not bridge state recovery); raw contents remain local
with hashes. Private-copy immutability and reader closure regressions pass.
This creates an explicit effect1/DISPATCHING crash fence without exposing any
production test parameter. The declared response delay2500ms still keeps final
handler acknowledgment pending; any premature result commit fails the state gate.

Persist operator QUERY observations before final RPC cleanup so a later fixture
error cannot discard them. All other source/owner/new-session, original5s deadline,
QUERY-only/no-replay/effect/closed-proof/cleanup gates stay unchanged. No production
SDK/ROS C++/worker/provider changes or rebuild, no changed locks or deadlines.

After238 host tests, syntax/diff checks and this source/plan are frozen, execute
exactly once:
`python3 tools/m3_n4_ros.py --output .local/m3-n4-remaining/crashes-exclusive --crashes`
Same before/effect/committed order, stop at first unexpected failure, preserve
originals and leave later cases unexecuted. No N5 run or additional retry specified.
Earlier two crash-cohort failures remain failed separate fixture evidence; native
and ROS freshness suites remain independent. No historical missing-footer cause
is inferred and no full N4/M3 acceptance is claimed by this plan.
