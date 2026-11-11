# Sustained mixed-route two-loss and observed child shutdown

The original first run FAILED its trace-completeness gate. Its remaining two seed
cases were not executed. A separately planned child-lifecycle diagnostic and two
separately planned repetitions passed. These are distinct evidence, not a repaired
original cohort. Full N3/M3 remains incomplete; PR2 stays draft, Intrinsic/M4 untouched.

## Original failure and evidence limits

Frozen source/plan cb2468b, `.local/m3-multiroute-two-loss/1701`: the sender trace
has4944 records and a complete final status. The receiver log has2427 event lines
but **no final SAMPLE_TRACE_STATUS**. The original result remains FAILED with
`missing or duplicate final sample status`. Original2903/4211 runs are NOT EXECUTED
under the stop-on-first-failure plan. They are not replaced by the later fixtures.

The inherited scenario cleanup silently discarded child exit codes and whether
its five-second SIGINT wait required a kill. There is no original child lifecycle
record. Missing receiver footer does not establish a crash, timeout, kill, lost
log write or another exact process cause. That cause remains UNKNOWN.

Original post-hoc diagnostics remain separately labelled: measured200.027338 /
50.031701Hz with no source skips,2514 sources,2429 SDK SAMPLE accepts, metric receiver
population2427 and2426 typed observations; all six aggregate balances0. Loss terms
are BUSY3, outbound replacement82, SDK-to-receiver gap2 and observer DDS1. Strict
measurement captures reconcile2427 source+607parity =3034 records per endpoint.
The unqualified receiver prefix lacks candidates7/8, but cannot establish complete
receiver-decision absence. These independent source/metrics/capture checks do not
supply its missing footer, qualify the two-loss run or replace its failed verdict.

## Observed-cleanup fixtures

Source5d9b9f3 adds post-window Python child-lifecycle records, preserving the
five-second SIGINT wait and recording pre-signal process status, VM signal bracket,
exit code and any forced kill. Preexisting exits (even0), nonzero exits, deadline
or forced-kill outcomes fail the fixture while all owned children are cleaned.
A bounded kill wait and host peer wait25s permit reporting for two children;
production and measurement deadlines do not change. Missing footers stay fatal.
No SDK/ROS C++/provider/source-scheduler/runtime changes or rebuilds were made.

- DIAGNOSTIC-PLAN.md: one execution at seed1701, source5d9b9f3.
- REPETITIONS-PLAN.md: two fresh conditional executions at2903/4211,
  source053c9bf, only after the diagnostic passed.
- No other live execution/retry/selector change. All three observed-cleanup cases
  pass and record all three children initially live, then exit0 under SIGINT with
  no forced kills and complete source/sender/receiver final statuses.
- Their success does not explain the original failure or demonstrate that its
  underlying cause was fixed. The diagnostic adds observability and strict gates.

| Separate case | Measured seconds | Actual IMU /joint Hz | Source IMU /joints | Typed observed IMU /joints | Source IDs unobserved |
| --- | --- | --- | --- | --- | --- |
| Lifecycle1701 |10.054406713|200.011802 /50.027815|2011 /503|1930 /496|88|
| Lifecycle2903 |10.054392755|200.012079 /50.027885|2011 /503|1931 /497|86|
| Lifecycle4211 |10.054154421|200.016820 /50.029070|2011 /503|1934 /497|83|

Each source meets the1% measured-cadence gates with zero skipped slots. Underlying
N0 qdisc seeds are base/base+1, with zero random delay/loss; these are independent-
start repeatability checks, **not random-loss seed coverage**. Permanent neighbors,
local Docker emulation and observers remain explicit fixture interventions.
Different local loss populations do not establish causal performance differences.

| Aggregate loss term |1701|2903|4211|
| --- | --- | --- | --- |
| Upstream DDS |2|1|1|
| BUSY admission |5|2|1|
| Ingress replacement |0|0|1|
| Outbound replacement |79|79|78|
| SDK-to-receiver gap |2|2|2|
| Receive replacement |0|1|0|
| Observer DDS |0|1|0|
| All other stage terms |0|0|0|

All six balances are0; stable pending queues are empty, all observed typed
hashes/stamps/order match source. Aggregate replacements do not identify the exact
stage of each unmatched ID. BUSY consumes no SDK index, and source counter mapping
must use actual admission stamps rather than publish indices.

## Exact mixed-route two-source cutoff result

Each classifier is installed before source arming with both initial counters0.
Final counters show one dropped packet per rule; parity message0 is excluded.
Actual SDK row5/6/7 is IMU,8 joints. Targets7/8 span both routes:

| Case | SDK7 source | SDK8 source | SDK SAMPLE accepts | Decoded receiver | ROS publications | Typed observations |
| --- | --- | --- | --- | --- | --- | --- |
|1701|IMU counter6|joint counter2|2428|2426|2426|2426|
|2903|IMU counter5|joint counter2|2432|2430|2429|2428|
|4211|IMU counter5|joint counter2|2433|2431|2431|2431|

At the drained cutoff exactly messages7/8 have no receiver decision; all other
receiver decisions are accepted. Their original source counters/hashes/envelope
indices remain explicit. Neither selected typed source is observed, while both
routes subsequently publish fresh data before cutoff. Row parity arrives before
the receiver cutoff, which precedes classifier removal; target SDK brackets follow
both installs. This is a bounded missing-source result with two losses in a
four-source/one-parity row, not a permanent-absence guarantee, internal provider
expiry event or generic irrecoverable-loss counter claim. The earlier selected
one-loss repair evidence remains independent.

## Captures, age, validation and provenance

| Per endpoint | Native/full-PCAP source | Parity | File/dispatch/kernel records | Source/sender/receiver trace records |
| --- | --- | --- | --- | --- |
|1701|2426|607|3033|2514 /4941 /2426|
|2903|2430|608|3038|2514 /4946 /2430|
|4211|2431|608|3039|2514 /4947 /2431|

Identity capture is separately closed at8/8 per endpoint in each fixture. Actual
SDK/ISN source and complete-row parity keys match native/full-PCAP multisets at
both endpoints; only selected source7/8 are excluded. Native observers start
first, close last and cover the source window; recorders attach final BPF before
bind with initial kernel0, stabilize equal counts and verify file size/hash, with
zero kernel/native losses, truncation or exhaustion. Features remain unchanged.
These are separate capture phases, not one continuous capture. Realtime PCAP
clock is not age authority, native monotonic records are skb observations.

Accepted-publication upper-age maxima (IMU/joints ns) are21441943/32156726,
14827528/28653399 and15522998/30660836; route histograms match publications.
Clock/QoS/session/owner/generations/isolation pass. Ages are callback-ingress
bounds under the existing clock model, not physical sensor ages. No lossless,
cryptographic-FEC, overhead-free, resource-parity or superiority claim is made.

218 host tests pass, including missing/extra receiver gaps, selected typed absence,
subsequent route progress, parity/cutoff/classifier ordering and clean/abnormal/
preexisting/timeout/kill child lifecycle outcomes. Python syntax/diff checks pass.
Previous SDK70 /ROS41 remain the latest full validation, not newly rerun; no new
full M2 acceptance. Seven runtime hashes are unchanged across all four fixtures.
All owned containers/network and passphrases were removed.

Plans, original verdicts, separately labelled post-hoc diagnostics, execution
matrix, source/sample metadata, typed hashes/metrics, selected shutdown/capture/
clock/qdisc/fault/lifecycle status, validation, inventory and local-artifact hashes
are archived. Raw PCAP/native prefixes, journals and resource/endpoint details stay
local; credentials and full inspect/environment dumps are excluded.

Next: baseline/one-loss seed repetitions under observed cleanup and predeclared
long-window N3 budgets (source trace capacity10000), then remaining N4/M3 gates.
Original missing-footer cause and historical capture/reset/UNKNOWN issues remain
open. Current short fixtures do not replace the full controlled comparison matrix.
