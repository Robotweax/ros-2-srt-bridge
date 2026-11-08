# Real failure detection and native N4 command boundaries

The nine real-process/recorder controls classify correctly. A corrected nine-case
native N4 cohort and three additional durable-dispatch cases pass:12 phase/direction
cases total. Two earlier fixture attempts remain FAILED, with their unexecuted
cases retained explicitly. No production SDK/ROS/provider/worker code changed.
This is native simulated-handler command evidence, not complete N4/M3 acceptance.

## Real failure controls

Frozen source326c2c0 runs the actual installed ROS bridge without a peer/workload
and the actual packet recorder. Seven deliberate negatives are rejected and two
clean controls accepted. A real witness child always exits cleanly even after a
failed bridge child. Source logs are preserved; the missing-footer mutation uses
a separately named copy of a clean real process's log.

| Control | Observed outcome | Detector result |
| --- | --- | --- |
| Clean bridge |SIGINT exit0, complete actual zero-event footer|Accepted|
| SIGABRT bridge |exit-6, missing footer|Rejected|
| SIGKILL bridge |exit-9, missing footer|Rejected|
| Premature clean bridge exit |initial exit0 before cleanup, valid footer|Rejected as unexpected preexisting exit|
| SIGSTOP bridge |diagnostic0.3s SIGINT deadline, forced SIGKILL/exit-9|Rejected; witness still cleaned|
| Removed-footer copy |original clean exit0 and valid footer; copy missing footer|Copy rejected|
| Clean recorder |six synthetic outgoing UDP records, exit0, reconciled counts/hash|Accepted|
| Killed recorder |exit-9, no complete artifact status|Rejected|
| Write-limited recorder |owned-process RLIMIT_FSIZE64 after readiness, exit120|Rejected; parent preserves injection/exit evidence|

These known negative controls validate failure detection; they are not accepted
failure-containing captures or a diagnosis of the historical missing receiver
footer. The write-limited child can fail while writing its own log/status; the
parent's independent record remains available. Core dumps were disabled for the
bridge controls. Abrupt-child descendant cleanup ultimately relies on teardown of
the owned PID namespace; witness exits are directly recorded. All owned containers/
networks/passphrases were removed. No host process, qdisc or resource limit changed.

## Preserved fixture-development failures

1. Original native gate40bf968, admission/both: FAILED before outage installation
   because the strict kernel-executable/stopped-state child lookup did not identify
   the worker. Remaining eight cases unexecuted. The revised peer30441d3 records
   actual owned-child argv, stopped state, PID/start ticks and kernel executable.
   New observations show `/run/rosetta/rosetta` rather than the worker target in
   `/proc/exe`; exact worker/mode argv and child ownership remain valid. The bounded
   readiness wait also covers the paused-notification/SIGSTOP transition. Original
   rejected-child facts were not recorded, so no unique retrospective cause is
   manufactured. Revised identity is verified again before resuming the same child.
2. Identity-revised admission/both: FAILED after interruption due to an incorrect
   fixture deadline equality assertion. Sender expiry537601704201ns vs receiver
   local expiry537595890394ns: receiver is5813807ns EARLIER. Production ClockMapper
   conservatively maps sender budget into the receiver domain. The fixture now
   preserves exact sender ingress+5s, verifies original owner/session/hash/origin,
   and requires receiver local expiry>origin and<=sender expiry on the proven
   shared VM clock. Fresh resume/dispatch checks use the receiver limit. This fixes
   a test assumption, not production deadlines. Remaining eight cases unexecuted.

Both original verdicts/logs/provenance remain unchanged. Corrected source d6c2cbb
runs a separately frozen nine-case cohort once; source90d3ae4 adds three separately
planned dispatch-before-start cases. No other live attempts/retries or changes to
production code, queues, crypto, command budget or replay policy occurred.

## Native N4 matrix

Each case uses fresh owned internal Docker peers, common boot/zero-time-namespace
proof, permanent neighbors, initial N0, one route100 command requesting100Hz with
generation0->1 and original5s budget. Existing worker test hooks hold exact phases;
no test controls are added to the production ROS node. The installed endpoint owns
the real SRT transport and supervised journal process, with an explicit simulated
rate handler. No SENSOR source or ROS publication-age acceptance is claimed.

| Phase | WAL-aware read at barrier | Both directions | Operator→robot cut | Robot→operator cut |
| --- | --- | --- | --- | --- |
| Admission before commit |No committed receiver entry|PASS|PASS|PASS|
| Durable dispatch before execution grant/start |DISPATCHING, effects0|PASS|PASS|PASS|
| Handler atomically started before effect |DISPATCHING, effects0|PASS|PASS|PASS|
| Result already committed before reply |SUCCEEDED with valid result|PASS|PASS|PASS|

Root netem100% loss is installed in the named directions, with actual kernel seed/
loss readback and positive drop counters on every cut interface. The VM hold is2s;
configuration/readback overhead produces measured guaranteed common outage
intervals2.483631168..2.597214710s. They meet the predeclared minimum, not an exact
2.000s duration claim. N0 is restored/read back before the held worker is resumed.

All12 reconcile to matching durable SUCCEEDED, exactly one simulated effect,
100Hz/generation1, one accepted execute/provider command handoff and no replay.
Sender queries are observed; this does not isolate whether a particular final
proof arrives via direct STATUS or QUERY response. Subsequent application requests
are QUERY only. Each case includes a further2s settled observation, restored
ready/clock qualification, trace attempted==recorded with zero drops and bounded
stop/join of all transports/workers. In the nine-case cohort maximum measured
endpoint stop is24.845042ms, below the5s limit. Additional three stops also satisfy
that limit; original snapshots and monotonic brackets are archived.

Both closed checkpointed journals agree on command ID/route/hash/source identity/
original session/origin and final state/reason/revision/result. Sender expiry is
unchanged origin+5s. Receiver expiry is conservatively earlier (about5..6ms in
these fixtures); it is not required to equal a timestamp from another configured
clock domain. Fresh resumed work uses the receiver expiry and the test rejects any
extension, stale resume, duplicate effect, changed proof/owner/ingress or fabricated
success. Read-only live barrier inspection never opens the journal recovery API.
Closed audits verify integrity, hashes and unchanged artifacts after peer stop.

The20s coordinator watchdog is an explicit test allowance for the held journal
worker; original production watchdogs and5s command budget remain unchanged.
Premature/abnormal peer failure or missing final stopped/trace metadata still fails
the fixture. Runtime library/provider/worker hashes remain unchanged. Standalone
fixture hashes differ between preserved revisions and the added dispatch phase,
with separate source/binary provenance and post-run inventories.

## Validation and remaining work

The archived initial CMake configure/build text strips trailing whitespace only;
its original local byte count/hash and archive hash are preserved in
validation/build-log-provenance.json. Measurement logs/verdicts are untouched.

231 host tests pass, including original/mapped deadline guards, owner/session/
command/ingress proof, success vs safe decline, phase placement, restored
qualification, replay/effect negatives and truncated artifact detection. Standalone
C++ fixture builds Release with Werror; Python syntax and diff checks pass. SDK70
and ROS41 remain the previous full validations, not new runs; installed production
code/binaries were not rebuilt. No new full M2 acceptance.

All plans, original failure and successful cohort verdicts, extracted barrier/
journal/command-trace metadata, VM outage brackets/kernel readback, failure-control
injection/exit/witness records, runtime provenance, builds/tests and cleanup are
archived. Original journals, synthetic PCAP contents and core/full environment/
inspect dumps are not archived; local artifact hashes retain provenance. No
credentials remain. No physical age, hardware, fair-resource, superiority or full
N4 acceptance claim is made.

Next in the agreed order: N4 with ROS sensor freshness, explicit deadline overrun,
withheld-result/query recovery and crash/restart/UNKNOWN boundaries; then SRT N5
progress and DDS discovery. Longer N3/comparison work follows those priorities.
The historical missing receiver-footer cause stays UNKNOWN; original failed and
skipped cohorts are never replaced. PR2 remains draft; Intrinsic/M4 untouched.
