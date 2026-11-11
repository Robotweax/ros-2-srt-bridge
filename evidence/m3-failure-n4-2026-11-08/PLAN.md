# Real failure detection, then native N4 command-phase interruptions

Freeze this source/plan after228 host tests, Python syntax/diff checks and the
standalone N4 peer Release/Werror build pass. Production SDK/ROS/provider sources
and binaries are unchanged. Previous SDK70/ROS41 remain the last full validation,
not new runs. The added peer links the installed endpoint and supervised journal
worker, with an explicitly simulated rate handler; it is never linked into ROS.

Execute exactly once:
`python3 tools/m3_n4.py --output .local/m3-failure-n4/failure --failure-controls`
Only if all nine controls classify as planned, execute exactly once:
`python3 tools/m3_n4.py --output .local/m3-failure-n4/n4`
Stop at the first unexpected failure; retain its original verdict and leave the
remaining cases unexecuted. No automatic retries, changed selectors or substituted
passing cohorts. Later work requires a separate frozen diagnostic plan.

## Failure-detection controls

Real installed bridge processes initialize via a metrics RPC, without a peer or
sensor/command workload. Unique ROS domains, fresh journals, controlled owned
witness child and core dumps disabled. Six controls run in order: clean shutdown;
SIGABRT; SIGKILL; clean exit before cleanup; SIGSTOP/stalled shutdown; clean exit
followed by intentional footer removal in a separately named copy of its log.
The source log is preserved untouched for that copy-mutation control.

Clean process control requires controlled SIGINT exit0 and complete actual sample
status (zero events in this standalone setup). Aborted/killed processes require
recorded negative signal exit and missing status. Premature clean exit requires
initial exit0 detected as failed shutdown even with its valid footer. Stalled
child uses a diagnostic0.3s SIGINT deadline, requires forced SIGKILL and failed
shutdown/missing footer. The witness must always be cleaned normally, demonstrating
that a failed child does not abandon remaining children. The missing-footer copy
must be rejected even though the original real process exited cleanly. These known
negative fixtures are expected to be rejected, not accepted qualification captures
or diagnoses of the historical missing receiver footer.

Three real packet recorder controls follow: clean six-datagram capture; SIGKILL
after readiness; actual write failure after readiness via RLIMIT_FSIZE=64 on only
the owned recorder process. The clean recorder must exit0 and strictly reconcile
six records with valid file/hash/status. Killed/write-limited recorders must exit
nonzero and fail artifact acceptance. Parent records injection and exit evidence
even when the failed recorder cannot write status/logs. Synthetic outgoing UDP
only, no SRT delivery claim. No host namespace/resource-limit changes.

## Nine native N4 cases

Order: admission-{both,to-robot,to-operator}, started-{both,to-robot,to-operator},
committed-{both,to-robot,to-operator}. Each is a new owned internal Docker network
and pair, common boot/zero-time-namespace proof, permanent neighbors and initial
N0 readback. One command request ID/route100,100Hz, generation0->1, original5s
budget; no SENSOR load, no ROS publication-age acceptance. Initial endpoints must
be ready/clock-qualified. Only network payloads carry command/status/query data.
Shared files coordinate known fixture phases, never relay execution/results.

Use existing compile-time fixture configuration of worker barriers:
- admission: receiver journal admission_before_commit, no visible committed entry;
- started: after atomic execution start, before simulated effect, durable
  DISPATCHING visible and effects0;
- committed: result_committed, durable SUCCEEDED/result visible before outage.

The paused worker must be the peer's unique actual stopped journal-worker child,
verified from its own /proc thread child list and executable before SIGCONT.
Production endpoint and worker APIs are unchanged. Coordinator watchdog20s permits
the deliberately held worker (same existing test convention); the command budget
remains5s and is checked unchanged in events and both closed journals. No command
retry/replay after SDK acceptance: exactly one execute admission/handoff; subsequent
reconciliation is QUERY only, with exactly one provider_sent command trace.

Install root netem100% loss in both or one egress direction as named; verify seed,
loss, queue and actual drops on each cut interface. Hold for two seconds on the
proven VM monotonic clock; the guaranteed common interval from last install-end
to first restore-begin must be>=2s. Restore/read back N0, then resume the same
paused worker; original deadline is never extended. Drain endpoint events and
bounded command traces throughout; trace counts must match attempted, zero drops.
Observe an additional2s after outcome to detect a second effect/handoff. Stop and
join endpoints/workers within5s, no remaining running transport/worker. Require
clean peer exit and closed checkpointed journals, hashes unchanged across audit.

Expected outcome rules are fixed before execution:
- Before admission and after start: durable matching success is allowed only
  with exactly1 effect/generation1 and matching100Hz result, and resume before
  the original deadline. Admission dispatch must occur after resume and before
  deadline. Otherwise authoritative context rejection/deadline expiry must have
  no valid result/effect/generation change. Packet cuts shorter than the budget
  need not force rejection if the same context and start remain valid.
- After result commit: sender must reconcile the original durable SUCCEEDED
  proof, exactly1 effect and no second command handoff. The outage must not erase
  committed success.
- Both journals must agree on ID/route/hash/original source epoch/session/origin/
  deadline/state/reason/revision/result. Temporary UNKNOWN is allowed during
  interruption; pure packet cuts with live same-owner workers must ultimately
  reconcile to durable success/rejection/expiry. UNKNOWN+NOT_FOUND alone is never
  treated as nonexecution, expiry or success. Crashes/ambiguous execution are a
  separate gate and no SDK-accepted command is replayed.

Audit live barriers via read-only WAL-aware SQLite in the robot VM, with no
recovery/mutation API. Audit closed journals only after both peers have stopped;
original DB/WAL contents remain local with hashes, extracted proof metadata only
is archived. Record source commit and pinned image/runtime hashes before/after.

Preserve original results/negative classifications, source provenance, peer event/
trace/lifecycle logs, journal metadata/hashes, phase/outage kernel readback and VM
brackets, tests/build and cleanup. Remove all owned containers/network/credentials.
Exclude secrets, raw journal records, full inspect/environment dumps or core dumps.
These are native simulated-handler command-phase development gates, not complete
N4 ROS sensor freshness, DDS parity, crash/restart matrix or M3 acceptance. N5 and
remaining M3 issues follow later. Historical unknowns remain unchanged; PR2 stays
draft and Intrinsic/M4 untouched.
