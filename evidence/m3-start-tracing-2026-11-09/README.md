# Targeted start-check/grant/worker tracing — 2026-11-09

The new default-off trace distinguishes a coordinator refusal from a worker
consume failure or a second pre-handler gate lapse. Controlled IPv4/IPv6 cases
qualify those observations without changing clock/fence policy or tuning settings.
**75 SDK,41 ROS and364 host tests pass.** The existing installed baseline is
preserved; new matched SDK/ROS builds use separate prefixes.

No new N5 cohort or command34 replay ran. Its historical6/1 outcome and missing
actual grant/consume fields remain unchanged. PR2 stays draft, M3 incomplete,
Intrinsic/M4 untouched.

## Observations and correlation

Enable `TransportConfig::start_diagnostics` together with `command_trace`, or ROS
`start_diagnostics:=true` with `command_diagnostics:=true`. Defaults are false.
Endpoint validation enables its matched worker's local shared observations; direct
`JournalWorker` callers can explicitly set `WorkerOptions::start_diagnostics`.
Missing trace dependency is rejected. Existing command tracing alone does not
enable the new worker/owner observations.

| Point | Producer | Recorded decision |
|---|---|---|
|40 start_submission |Coordinator|Final non-BUSY owner-check submission result and check token|
|41 start_check |Transport owner|Check result/evaluation, clock state/deadline, actual grant flag and deadline, slot/generation|
|42 execute_submission |Coordinator|Final non-BUSY worker submission result and worker token|
|43 worker_start |Coordinator, from matching child reply|Actual consume result/time/deadline, second-gate time/deadline, handler-invocation flag, returned journal state/reason|
|44 start_declined |Coordinator|Post-dispatch decline decision; no execute submission is asserted|

All events retain original request/session/route/origin/request sequence, local
owner epoch and control generation. Check/worker tokens and grant slot/generation
prevent cross-command or reused-slot joins. Actual `grant_deadline_ns` and original
`command_deadline_ns` are separate. The admission clock sample is never substituted
for the actual grant. Worker observations explicitly indicate availability; missing
fields do not mean successful consume or nonexecution.

Consume values:0 unavailable,1 started,2 expired,3 revoked,4 invalid. Second-gate
fields are populated only after successful consume. `handler_invoked` records
entry to the external backend or simulated effect branch, not a guaranteed effect
or successful result. Full command/journal/device audits remain separate authority.
Diagnostic timestamps cannot redefine a deadline or authorize replay.

The existing two128-record SPSC lanes retain their256-event bound and explicit
attempted/drop counters. No new worker/owner I/O, callback, allocation or retry is
introduced for tracing. Output uses a version1 JSON suffix on points40–44 only;
older command records retain their existing JSON fields. The existing reader's
250000-record bound remains. Added observer work can change timing; no performance
or mitigation claim follows.

## Shared worker observation and compatibility

The child writes a fixed POD snapshot into its existing start-fence slot and
publishes the generation with release ordering. The supervisor acquires it only
after the matching IPC reply while retaining the original Record. Generation,
population and unavailable checks prevent reuse from manufacturing observations.
The trusted single child is the sole writer; publication happens once. A child
crash without a reply does not acquire invented consume timestamps.

The pool remains64 slots in a sealed-size shared memfd; no change to one-use CAS,
revocation, original budget, grant calculation or handler-gate outcome policy.
The internal mapping moves to version2 with explicit flags/size checks. Incompatible
mappings fail closed. **Rebuild all C++ consumers, supervisor, SDK worker and ROS
worker/nodes together:** public diagnostic structures also grow, so this is not a
binary-compatible SDK update. Worker socket IPCv3 framing and SRT/protobuf/ROS CDR
wire formats remain unchanged. Existing installed binaries were not replaced.

## Controlled evidence, once per case

[Plan](PLAN.md) precedes the work. The early preparation build passes, but is not
used for qualification. The first complete calibration build catches a fixture
constructor that omitted its required route manifest; it fails before any cases
run. The corrected fixture is built from frozen source into a separate qualified
prefix. Both build logs are retained. There is no failed-case retry.

New endpoint fixtures run once for each IP family as part of the full75-test SDK
suite, with fresh isolated journals and `--network none`:

| Case, each family | Actual trace | Durable outcome / effects |
|---|---|---|
|Normal start|40→41 granted→42 queued→43 started, second gate passes, handler invoked|SUCCEEDED4/0,1 effect|
|Coordinator clock refusal|40→41 error13/clock expired, no grant→44; no42/43|REJECTED6/1,0 effects|
|Second-gate lapse|40→41 granted→42→43 consume started, second gate elapsed, no handler|REJECTED6/1,0 effects|
|Disabled start tracing|Existing command trace complete; zero40–44 events|SUCCEEDED4/0,1 effect|

All8 captures are complete with zero dropped trace records. Source and new
binaries are verified frozen immediately after capture. Individual folders retain
their process IDs; IP family is not an invented event field. Full CTest commands
and both passing family tests are retained in
[SDK LastTest](validation/sdk-LastTest.log).

The coordinator fixture pauses at the existing durable-dispatch barrier and
resumes after its explicitly synthetic500ms clock lease, before the next existing
1s probe. The second-gate fixture pauses after consume across a synthetic1.5s
lease. These are named loopback stimuli, not production clock tuning. The3s
operation timeout,5s command budget and all production defaults remain unchanged.
Only a test-enabled atomic resume request was added to the coordinator; no
CLI/environment/wire input enables test barriers in production.

The existing execution-start IPv4/IPv6 tests additionally enable and validate the
new direct-worker observations while retaining their seven existing scenarios.
There are12 returned observations across the two families. Both session revocation
and pre-consume clock-lease lapse report actual consume3/revoked: the owner can
revoke an elapsed unconsumed grant before the worker resumes. This is why a revoked
enum alone is **not a session-loss cause**. Original-budget expiry also reports
revoked consume in this calibration, but durable7/3; the observed result is not
renamed to consume2. Running completion and crash/UNKNOWN behavior remain intact.
The crash case has no final consume reply to fabricate.

New shared-memory tests verify disabled/unpopulated observations, wrong slot or
generation, once-only publication, reuse clearing, late old-generation rejection,
old mapping version/unknown flags rejection and cross-process publication.
Consume2/expired and4/invalid have contract/parser negative coverage; no full-worker
sample with those values was forced by repeating a race.

[All event joins](calibration-joins-final.json),
[closed journal extracts](closed-journals.json),
[direct-worker observations](worker-consume-calibration.json),
[SDK/ROS/host results](validation/results.json).

## Reader and harness guards

`m3_start_trace_analysis.py` joins tokens and immutable context rather than event
arrival order: the two producer lanes may interleave. It validates schema, enums,
actual grant/clock/command bounds, availability, consume and gate timestamps,
matching worker tokens and slot generations. Missing required successful-start
stages and mismatched records fail diagnostics.

It also preserves legitimate distinctions: a coordinator may decline after an
earlier owner grant was revoked/canceled before polling; a canceled owner check
may lack an owner-decision observation, which is explicitly marked unavailable.
An actual failed execute submission has no worker token or consume result. Those
are not fabricated consume failures. These reader-only guards were added after
closed capture, tested and rejoined without changing any recorded case outcome;
original reader Git blobs/source hashes are verified.

ROS exposes `start_diagnostics` default false. Scenario and `run_m3.py` expose
`--start-diagnostics`, requiring `--command-diagnostics`. The scenario omits the
new ROS parameter entirely when disabled, preserving old default invocations.
The harness requires complete new start observations when requested: an older
binary that ignores the override and emits no new records fails diagnostics,
instead of producing a false enabled report. Use matching rebuilt binaries; do
not treat `--skip-build` against the old installed baseline as a qualified run.

## Validation, preservation and next step

- Full new isolated SDK75/75, ROS41/41 and host364/364 pass. The SDK suite ran
  sequentially once with stop-on-failure, including all controlled captures.
  No tests/builds/heavy analysis overlap those captures. ROS build/tests and
  closed reader updates follow SDK closure.
- Original8 runtime/2 native observer/ARP tracer baseline and all14 binaries from
  the preceding diagnosis remain unchanged. New builds live in
  `build/m3-start-trace-qualified`, `install/bridge-start-trace-qualified`,
  `build/m3-start-trace-ros`, `install/m3-start-trace-ros`.
- Provider archive/commit fixed; no dependency or enclosing repository edit.
  All563 prior raw artifact hashes rechecked. [154 new raw hashes](local-artifact-hashes.json)
  include controlled journals/ownership markers; [every public omission](public-disposition.json)
  is explicit. Complete controlled SQLite/compiler/ROS XML metadata remain local
  by hash. Pinned-image test containers are removed.
- [Source provenance](source-verification.json) separates frozen producer/C++
  tests from three post-closure reader/harness/host-test edits; original Git
  blobs verified. [Matched new binaries and preserved baseline](binary-verification.json).

The tracing is ready for a separately frozen prospective loaded cohort using the
matched new baseline. It can distinguish a future start-stage rejection; it cannot
recover command34's missing original fields. No new N5 cohort, tuning, historical
reclassification or replay occurred here. FullM3/N3/N5, default loaded DDS,
clock/security/resource/hardware/comparison gates and UNKNOWN98/12 remain open.
PR2 draft, Intrinsic/M4 untouched.
