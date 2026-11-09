# Intent 118: sender clock deferral and journal reconciliation

The pending-input/journal discrepancy is explained by two separate paths. The
transport drops the volatile input at its original deadline without a journal
RPC. The sender remains locally queued in the driver's observations. Later,
after the observation window, session invalidation converts the outstanding
sender entry to **UNKNOWN / reconcile_required**, revision 0. This is an
unresolved result, not an expiry or permission to replay.

This audit uses only retained N5/1701 evidence from
`.local/m3/20261109T125820284511Z`. No new cohort, command, journal recovery,
fault injection, policy change, forced expiry or runtime build was performed.
N5/4211 remains unexecuted under the stopped plan; PR2 remains draft and M3 open.

## Original identity and sequence

Request `76000000000000000000000000000000`, session
`07df7a9f7b7838545fdce0e6333fe8c0`, owner/source epoch
`311614daf9a3672822c7a75da1dc73f4`, route 100. All times below are retained
monotonic nanoseconds; the audit checks the captured source hashes.

| Event | Time / observation |
|---|---|
| Original ingress | 341341538487; original deadline 346341538487 (5 seconds) |
| Durable sender admission | 341345271070; trace5 local_queued at 341349663362 |
| Volatile transport admission | trace6 queued at 341349673487 |
| First sender clock deferral | trace29 at 341358498612, origin +16.960125 ms |
| Original pending input dropped | trace21/deadline at 346344162614, deadline +2.624127 ms |
| Last driver status | 371404447417; cached local_queued, revision0, local not_found/peer NOT_FOUND |
| Observation window ends | 374237012044 |
| Session change / invalidate requested | trace2 at 374642701836 / trace3 at 374642706752 |
| Invalidation completes successfully | trace4/value0 at 374653670794, 28.309508180 s after input drop |
| Endpoint stopping / stopped | 375187708586 / 375200369336 |
| Closed sender journal | UNKNOWN8 / reconcile_required2 / revision0 / invalid result |

The complete trace includes teardown. The earlier cohort's statement of **no
active-window context loss** remains true; it does not mean no teardown session
change. The scenario finishes the peer before stopping the sender. The observed
session invalidation chain, together with the unchanged implementation, explains
the closed row without invoking application recovery. No per-entry mutation
trace was recorded, so the chain is a source-supported explanation, rather than
a newly observed journal commit timestamp.

## Clock diagnosis and its limit

`Session::make_control(COMMAND)` checks `ClockMapper::check(now)` before creating
the envelope. SessionError13 is returned for exactly the two soft clock errors:
`unqualified` and `expired`. A hard clock error takes the clock_invalid path.
At this deferral, transport point29 records SessionError13 only. Its generic
clock_error0/deadline0 fields are unused defaults, not a qualified clock sample.

An expired probe-age lease and an offset interval exceeding its width bound
therefore remain indistinguishable in this historical event. An unqualified
mapper can also have no accepted probe. Retained wall/monotonic clock samples
are capture alignment samples, not the bridge's four-timestamp probes. Receiver
clock observations belong to the other mapper and cannot fill this gap.
The diagnostic emits once per pending command, not once per failed check: the
single point29 does not count checks or establish continuous unqualification.
No ARP, qdisc, scheduler or unique network cause is established.

## Why the journal does not follow the volatile drop

- `endpoint.cpp` obtains a one-use durable ticket on fresh sender admission.
  `SubmitResult::queued` reports bounded volatile admission, then the coordinator
  clears its current job. It does not mean SDK acceptance or peer admission.
- `transport.cpp` claims the proof, retains the pending command unchanged when
  make_control reports clock_unqualified, and checks the original context,
  proof liveness and deadline on later iterations. The original input is dropped
  at its deadline; `release_pending_command()` resets the slot. It sends no
  worker/journal completion to the endpoint. No timeout extends the command.
- GET/QUERY can read/reconcile status but cannot mint a new ticket. The peer's
  NOT_FOUND error is not authoritative expiry and does not mutate the sender
  entry into a result. Driver history retains 64 of 158 observations, explicitly
  omitting 94; the final cached local_queued row is not a closed-journal read.
- Session change queues `invalidate_session`; its successful worker completion
  is recorded after observation. Sender invalidation changes outstanding states
  to UNKNOWN/reconcile_required without adding a peer result or revision.
- Normal journal destruction only closes SQLite. Opening a journal through the
  application constructor also conservatively recovers nonterminal records, but
  this audit never calls that API. Scenario inspection and this audit use SQLite
  reads, not application recovery. The original files were not reopened for write.

There are zero recorded original SDK handoffs, no receiver COMMAND/start and no
receiver journal entry. These local diagnostics do not authorize nonexecution,
manufacturing a receiver expiry or replay. Older UNKNOWN98/12 had SDK handoffs;
their failure scope remains different. Historical command34 remains unchanged.

## Reproduction and validation

[`analysis.json`](analysis.json) records the minimal original stage events,
teardown chain, closed sender row, source hashes and fixed runtime inventory.
The read-only tool checks all 303 retained raw hashes before and after, validates
every trace incarnation as complete, reads closed journals immutably and verifies
the calibrated matched SDK/ROS binaries and preserved baseline twice.

```
python3 tools/m3_sender_pending_diagnosis.py \
  --run .local/m3/20261109T125820284511Z \
  --manifest evidence/m3-start-broader-seeds-2026-11-09/local-artifact-hashes.json \
  --out .local/intent118-new-audit.json
python3 -m unittest discover -s tests -p 'test_*.py'
```

The new output must not exist and must be outside the retained run. All 380 host
tests pass, including guards against context substitution, active-window
invalidation, failed/missing teardown, SDK handoff and invented terminal status.
SDK75/ROS41 qualifications remain those of the unchanged matched binaries; they
were not rerun or rebuilt for this read-only audit.

Next diagnostic work: observe the sender owner's actual clock error, evaluation
time and qualification deadline at deferral, plus pending-input release and
coordinator receipt, in a separately calibrated prospective diagnostic build.
Keep these observations separate from outcome authority. Any durable resolution
of a proven pre-send drop needs an explicit proof/acknowledgment design; elapsed
time, NOT_FOUND and these traces alone must not become automatic expiry or replay.
