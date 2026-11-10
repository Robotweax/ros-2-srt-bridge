# N0 startup capability-attestation diagnosis — retained evidence only

**Confirmed harness defect: a readiness file from the negative startup test is
reused for the real robot bridge.** This is the best-supported explanation for
premature capability attestation. The exact failing capability fields and child
transition remain unobserved; no runtime privilege failure is established.

No tuning, fix, test execution, retry or new experiment was performed. Frozen
source/helpers/builds and the failed run remain unchanged. Other28 campaign cases
remain disabled; N0 has no qualifying measurement, M3 open, PR2 draft, M4 untouched.

## Evidence chain

1. The inherited combined robot scenario launches a deliberate `wrong-hash`
   bridge_node, waits for exit1, checks its expected type-hash error and writes
   robot-ready.json before accepting the real start request. See
   ros2/robotweax_srt_bridge_demo/scripts/m2_scenario.py:204–224.
2. Diagnostic.start wraps **every** bridge_node launch, including that negative
   test. Its destination depends only on role: robot-bridge-preexec.json. It does
   not include launch name, token, current PID or start_ticks in the filename.
   See the frozen N0 scenario.py:343–350.
3. bridge_exec.py:32–35 reduces capabilities, checks its own status, writes that
   file and then execs the requested bridge. Thus a successful negative-test
   wrapper writes the same readiness file before the expected type-hash failure.
4. Diagnostic.start_bridge:352–359 starts the real child, then accepts **file
   existence** as readiness. It never reads or matches the marker PID to the
   current child, never removes/separates the earlier marker and does not attest
   the execed bridge phase. It immediately checks the new child's /proc status.
5. Retained wrong-hash.log contains the expected type-hash failure;
   robot-ready.json confirms wrong_hash_rejected=true; control.json requests the
   real `start`. Saved pre-exec PID127 has zero capability sets/NNP1. Its retained
   file mtime precedes the real start request by1,512,270,762ns. The actual robot
   bridge log is empty and robot failure occurs at the immediate capability check.
   No refreshed pre-exec record or robot identity for the real child is retained.

These facts identify a concrete synchronization bug: an earlier launch can
satisfy the readiness predicate for a new launch. The earlier zero-capability
record therefore does not contradict a failing status read of the current child.
A check before that child's capability reduction is a supported timing explanation,
not a directly captured scheduler or syscall sequence. No arbitrary capability
relaxation follows from this diagnosis.

Filesystem mtimes are retained metadata, recorded in analysis.json for comparison;
they are not kernel-monotonic lifecycle events and were not bound by the original
content-only raw hash index. Source control flow, negative-test success and shared
marker identity establish the reuse defect independently of precise mtime offsets.

## Why prior passing evidence did not cover this path

The N3 SENSOR fixture calls its measure method and starts one bridge per role;
it does not execute the inherited combined robot negative-test launch sequence.
Its nine recorded passes remain preserved, but do not test readiness across this
multi-launch N0 path. The N0 offline suite checked the unchanged Benchmark body,
capability-wrapper equality, scope/release/stop controls and mocked processes. It
did not model the inherited wrong-hash launch followed by the real robot start.
Those tests cannot supply startup qualification for the missing integration path.

The operator's saved identity reports Name=python3 and zero capability sets.
That is a recorded status snapshot, not positive execed-bridge identity evidence;
the source readiness predicate contains no exec-phase condition. Under the pinned
emulated target, Name alone is not used here to establish an exact exec transition.

## Observation limit and future repair boundary

The failing /proc snapshot, real child PID/start_ticks and event timing were not
saved. We cannot name the differing capability field, prove failed cap-drop
syscalls, show later privileged bridge execution or reconstruct the exact race.
The robot's old pre-exec JSON proves only that recorded launch's checked state.
The failed N0 remains FAIL; capture/final-status failures and emergency cleanup
are preserved without waiver. No clean shutdown or measurement credit is added.

A future narrowly scoped harness repair should use immutable per-launch readiness
records with an explicit token and current child identity, validate an atomic
complete record before checking a single retained capability snapshot, distinguish
wrapper readiness from bridge exec readiness, and retain the actual failed status
and phase. Negative-test evidence should remain separate. Merely relaxing the
zero-capability gate or waiting a fixed extra delay would not fix identity binding.

Proposed offline regressions should cover a stale negative-test marker, wrong PID/
launch identity, partial file, pre-drop child, exited child and missing post-exec
phase before any separately authorized live calibration. No such implementation,
new test run, new freeze or live case was created by this diagnosis.

## Integrity and artifacts

analysis.json separates observations, confirmed code defects, inference and limits.
input-hashes.json binds the exact retained source/artifacts read. retained/ adds
public copies of the small negative-test/ready/control records omitted from the
previous compact publication; their original raw hashes still verify.
postflight.json records a read-only integrity audit of frozen source/inputs,
current14 binaries/native87 and prior raw/public indexes, including all64 files
from the failed N0 attempt and1,092 files from the fresh N3 cohort. No Docker call,
process fixture or live-state change was used. Public hashes bind this diagnosis.
