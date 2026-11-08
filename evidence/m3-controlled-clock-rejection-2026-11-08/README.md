# Controlled clock rejection retains uncertainty

All controlled checks pass. The full Release/Werror SDK suite passes71/71 at
`deedc5468be73f93b9e8b59c8378b4b5eae8f9e4`; host267/267 passes. No production
algorithm or runtime changes, no new N5 cohort, no historical failure resolved.
PR2 remains draft, M3 open, Intrinsic/M4 untouched. The [plan](PLAN.md) was frozen
in c9398eb before implementation and execution.

## Protocol boundaries

A new contract invokes production Session and CommandJournal with explicit logical
clock values and normal management handshake/probes. It is not an SRT wire or
ROS experiment. The future case deliberately advances sender logical time200ms
after zero-offset qualification, violating the fixture's clock model without
changing the host clock or bypassing sender envelope creation. Receiver clock
expiry uses a20ms qualification age versus the sender's5s.

| Case | Admission | SessionError | AgeResult error | Clock state |
|---|---|---:|---:|---:|
|Fresh positive control|accepted|none0|none0|none0|
|Receiver qualification expired|rejected|clock_unqualified13|expired2|expired2|
|Origin beyond qualified offset estimate|rejected|clock_unqualified13|future_sample9|none0|

Both negative cases retain the control session. The rejected command consumes the
receive sequence watermark; presenting the identical envelope again yields replay.
A new QUERY remains admissible, including with an expired receiver clock. Empty
receiver journals and NOT_FOUND cannot replace the sender's original LOCAL_QUEUED
entry or renew its saved5s context/deadline through duplicate admission after the
budget. Reopening the sender yields UNKNOWN/reconcile_required without a result
or permission to transmit. This direct composed contract does not claim a real
SDK handoff, physical effect, or automatic handling of errors by an endpoint.

## Real SRT endpoint uncertainty

The extended IPv4 and IPv6 native fixtures each use real production endpoints,
workers, journals and the pinned SRT provider on owned loopback sockets inside
network-none Docker. Only the receiver test configuration changes its qualification
age to150ms while keeping the existing1s probe cadence. Each family runs once in
the full SDK suite, which stops on first failure; no native scenario was retried.

Each fixture observes a COMMAND rejection13 with ClockError/AgeResult expired2,
then sender peer error5 matched to the original request/session/sequence. Explicit
QUERY before and after the original5s deadline returns the local LOCAL_QUEUED
entry alongside a nonauthoritative QUERY/NOT_FOUND peer diagnostic. The entry
retains revision0, original origin/context/deadline and no result.

The test stops and replaces its receiver, restoring the normal5s qualification age
under a new process epoch/session. The still-running sender invalidates its old
context and exposes live UNKNOWN/reconcile_required. Reusing the original command
ID performs reconciliation; the sender never obtains another accepted SDK handoff.
The restarted receiver observes no COMMAND for that ID. Trace populations show
exactly one SDK handoff across the entire fixture, with zero dropped observations.
Old and replacement simulated receivers observe zero effects; this is a controlled
fixture observation, not a general nonexecution inference from absent records.

Four immutable, checkpointed closed journal-pair audits (two protocol negatives,
two native families) retain sender UNKNOWN/reconcile_required/revision0, invalid
result, original5s deadline and an empty receiver journal. Closed receiver absence,
NOT_FOUND and budget expiry still do not authorize replay or a durable negative
outcome. See [closed-journal-audits.json](closed-journal-audits.json).

## Validation and provenance

- [results.json](results.json) extracts three protocol cases and two native cases
  from the original [CTest log](validation/LastTest.log), with full71-test success
  in [sdk.log](validation/sdk.log). Test-source and binary hashes are retained.
- After the successful suite, a fixture-only revision9e174d5 replaces PID-named
  protocol outputs with an exclusively created mkdtemp directory. This prevents
  retained outputs plus later PID reuse from breaking unrelated repeat test runs.
  The changed nonnetwork contract was rebuilt and passed once; original full-suite
  results/source remain unchanged. Separate provenance: [directory-revision.json](directory-revision.json).
- All eight installed runtime hashes match before/after the full suite and after
  the directory-only revision; provider pin unchanged. No install or ROS rebuild.
  ROS41 remains prior validation. Host267, syntax and diff checks pass. The two
  owned validation containers are removed; no WAN profile, capture, shaper, wire
  timing, overhead, resource or hardware-clock qualification is claimed.
- Original SQLite files remain local with hashes and read-only audits. Source
  source_commit/sha256 in [source-verification.json](source-verification.json)
  records the full-suite verification before the later directory-only revision.
  The latter has its own source/binary identity. Validation console copies alone
  normalize trailing whitespace; original/derived hashes are retained in validation/.

The checks reproduce safe uncertainty handling at controlled rejection boundaries.
They do not identify the old seed4211 cause or establish a progress fix. Next
freeze a finite instrumented multi-seed N5 cohort to seek a request-correlated
recurrence, without replay, deadline changes or retry-until-success. Loaded
ROS/N5 discovery and the remaining N3/clock/security/resource gates stay separate.
