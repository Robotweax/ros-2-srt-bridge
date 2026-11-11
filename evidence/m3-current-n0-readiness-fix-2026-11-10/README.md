# Launch-specific N0 readiness fix — offline verification only

**Implemented and verified offline. No N0 rerun or new live experiment.**

This separate candidate harness revision fixes the confirmed stale per-role
readiness defect without modifying the frozen N0 preparation, failed attempt,
retained diagnosis or installed SDK/ROS binaries. No execution grant, campaign
freeze, workload output or automatic follow-on is created. Other28 campaign cases
remain disabled, N0 remains unqualified, M3 open, PR2 draft and M4 untouched.

## What changed

- Each bridge launch, including the deliberate wrong-hash test, gets its own
  random token and immutable record path containing role, launch name and token.
  Negative-test and real-bridge records are kept separately; the old role-level
  file is never a readiness input.
- The parent registers the child PID/start_ticks/parent identity immediately after
  Popen and checks identity stability. The reduced wrapper atomically publishes a
  complete schema/phase/token/name/role/binary record with bracketed process
  identity and its exact capability snapshot.
- Parent attestation requires that exact launch context and registered process
  identity before applying the unchanged zero-capability/NNP/seccomp policy to a
  single current status read. Reused PIDs, wrong tokens, exited children, partial
  records, identity changes and wrong phases fail closed. Missing readiness waits
  only within the original5s startup budget; no fixed extra delay or gate waiver.
- Failure files retain the exact status read used by the failed check, identity
  brackets, expected identity, launch context, phase and error. Read errors are
  explicit. Wrapper reduction/exec failures, registration failure, early exit and
  timeout retain their available snapshots. The first failure per launch/side is
  kept; later observations cannot overwrite it.

Readiness explicitly means `capabilities_reduced_preexec`, not execed bridge
readiness. Exported identity says execed_bridge_attested=false. The existing ROS
session/clock/typed-stream readiness gates still establish application readiness;
no /proc Name or emulated executable-path heuristic is added. A pre-exec record
alone does not prove successful exec or later production behavior.

## Integration and preservation

`scenario.py` preserves the full Benchmark workload body and inherited negative
startup check. Its Diagnostic subclass selects launch-specific readiness and
exports the same validated status snapshot rather than doing an unrecorded second
read. `bridge_exec.py` preserves the original reduce function byte-for-byte at
AST level and uses the new atomic publication/failure capture. `workload.py`
selects the corrected scenario while retaining the single N0/1701/300s guard.
Unchanged capture/runtime/observer helpers are imported from the immutable prior
preparation. No installed/native code, capability policy, rate, queue, clock,
startup/shutdown timeout, observer filter or sampling budget is changed.

This package is a reviewable candidate harness revision, not a new runnable frozen
campaign. The old driver still binds its old immutable inputs and cannot silently
select this fix. A fresh separately prepared freeze and explicit execution grant
are required before any live qualification. No N0 result is replaced or retried.

## Offline verification

**21 targeted tests and all511 existing tests pass.** Tests use temporary synthetic
procfs files, mocked child processes/reduction/exec and the actual extracted
Diagnostic class; no bridge, wrapper process, Linux capability syscall, Docker
object, capture or observer is started. Compile-only syntax checks pass.

The targeted cases cover:

- A valid wrong-hash/legacy marker while the real child is still privileged: no
  status check or early acceptance occurs until the real launch record exists.
- Actual negative/positive Diagnostic.start calls receive different paths/tokens
  and registered child identities; startup waits for the current launch.
- Foreign token/name/PID, PID reuse, identity changes across a status read, child
  exit, unavailable procfs, malformed record and wrong phase are refused.
- Nonzero capability and NNP failures retain the exact single checked snapshot;
  missing-readiness/registration/reduction failures also retain evidence.
- Complete atomic record publication, no duplicate readiness overwrite, immutable
  first failure and correct reduce→publish→exec ordering.
- Original capability-reduction function and combined Benchmark workload ASTs
  remain identical to the frozen preparation.

This proves the modeled readiness binding and failure capture, not live timing,
post-exec capability behavior, performance or successful N0 measurement. The
historical N0 capability values remain unobserved and its failure stays intact.

postflight.json records source/input/build and retained raw/public integrity;
input-hashes.json binds the retained dependencies. Public package hashes cover
the correction and validation logs. No Docker call or native rebuild is needed
or performed for this offline verification. Fresh N3 stays9/9 within its recorded
scope; historical N3 8/1 and all other failed evidence remain unchanged.
