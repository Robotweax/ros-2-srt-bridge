# ROS discovery confirmation and extended SRT N5 progress

The frozen six-slot development matrix **FAILED**. Four slots passed, the ROS
fragment-cut transfer hypothesis was contradicted, and SRT N5 seed4211 left one
command unresolved. No slot was retried. Full N5/M3 acceptance remains open.
PR2 stays draft; Intrinsic/M4 is untouched.

Plan: [PLAN.md](PLAN.md). Executed source:
`064152344a05c134b748b51e0b5ad7e5e8232a93`. The two groups were independent;
first failure stops subsequent slots in that group. The ROS group failed on its
last slot and the SRT group on its last slot, so all six slots executed exactly
once. The matrix driver returned1. Original per-run reports are not reclassified.

| Slot | Measurement | Confirmed / attempted | Skipped slots | Verdict |
|---|---:|---:|---:|---|
| ROS system DDS N0 control-first,1701 |15s|8/8|0|PASS|
| ROS system DDS N0 fragment cut,1701 |not started|0/0|not applicable|FAILED hypothesis gate|
| SRT N0 control,1701 |15s|8/8|0|PASS|
| SRT N5,1701 |300s|131/131|19|PASS progress gate|
| SRT N5,2903 |300s|130/130|20|PASS progress gate|
| SRT N5,4211 |300s|11/12|138|FAILED progress gate;1 unresolved|

The two passing N5 rows establish bounded command progress for those seeds, not
continuous2s cadence, latency/service guarantees, sensor delivery qualification,
transport superiority or the full N5 matrix. N5 sensor source/observer totals are
75028/7225,75030/12708 and75034/27249 respectively. Accounting balances are zero;
large SRT-accept-to-receiver gaps remain explicit, not relabeled network drops.
Full sensor categories and observed latency distributions are in [summary.json](summary.json).

## ROS transfer hypothesis was not reproduced

Before either workload driver could submit Execute, the owned selector dropped
exact robot-to-operator IPv4/IHL5 UDP continuation offset185 packets. It recorded
12 drops/8656bytes during the discovery-only fixture. The local-eligibility hold
lasted8.002644087s. Both real ROS coordinators already matched all four command
endpoint counters and were ready; operator HELLO sent/received83/82, robot74/73
at the blocked checkpoint. This contradicted the predeclared expectation that
operator endpoint discovery would remain incomplete.

The selector was removed and verified absent before the assertion rejected the
case. `controlled-discovery.json` retains its last internal stage
`awaiting_recovery`; that is not a successful recovery verdict. No restored
barrier file was published, no sensor workload measurement began, both fresh
closed command journals are empty, and all11 sampled typed-count snapshots per
role are zero with one coordinator process epoch each. All three owned native
children shut down cleanly; scenario failure is the expected parent abort.

This test uses unburdened ROS N0 with telemetry paused, not the standalone native
probe's4096-byte discovery metadata and not loaded N5. The earlier native
fragment-loss mechanism remains valid within its own fixture. Neither result
uniquely explains the historical loaded ROS discovery failure. See the original
[cut state](ros-N0-fragment-cut/controlled-discovery.json),
[journal audit](ros-N0-fragment-cut/closed-journal-audit.json) and timelines.

## Seed4211: unresolved command under continuing context

The original SRT harness reports PASS because its safety/accounting gates permit
unresolved commands; the stricter frozen progress gate reports FAILED. Capture
population reconciliation and command/provider diagnostic footer gates pass.
Closed journals confirm11 successful effects. Intent12 has exactly one SDK
handoff and the original5s sender start budget. No accepted command was replayed.

Live polling retained LOCAL_QUEUED/revision0 through its last observation, about
280.099s after submission;1337 polls,172 NOT_FOUND status observations. History
retains first/last32 polls and reports1273 omitted polls. An early retained poll
has local clock_unqualified7/peer clock_unqualified5. The exposed status does not
identify COMMAND versus QUERY, so this is a lead rather than a proven admission
rejection cause. Final status contains local not_found2/peer NOT_FOUND3.

After shutdown the sender journal is UNKNOWN/reconcile_required/revision0 and the
receiver journal has no matching entry. Shutdown/session invalidation can create
that sender state; no live UNKNOWN transition was observed. Neither the closed
receiver absence nor elapsed budget nor NOT_FOUND proves nonexecution or permits
replay. The live command remained pending, blocking138 later slots; the driver's
`commands_paused_after_unknown` is false because it never observed a terminal
UNKNOWN response.

Complete trace populations contain no session-change/invalidation/session-action/
link-loss event (points2,3,4,30,31) during publication resume to command cutoff.
Sender intent12 records admission, submit-result and one provider_sent; the
existing receiver trace has no request-admission instrumentation, so lack of a
receiver request trace is not evidence of nonreceipt. Provider_sent means SDK
acceptance, not peer delivery. The exact rejection/delivery/clock cause remains
unproven. Read-only checks and original observation history:
[seed4211-closed-analysis.json](seed4211-closed-analysis.json),
[closed_analysis.py](validation/closed_analysis.py),
[post-run command audits](post-run-command-audits.json).

## Evidence and validation

- [execution.json](execution.json) preserves the original cohort verdicts; the
  separate post-run audits also cover4211, whose failing gate did not attach a
  proof object to that original row.
- Both tcpdump children were confirmed alive and listening before applications
  started. Closed file/filter/footer/kernel populations and optional stable drain
  checks passed for all slots. This uses tcpdump, not a filter-before-bind
  AF_PACKET guarantee or realtime PCAP latency authority.
- [source-verification.json](source-verification.json) verifies original per-run
  source hashes against frozen0641523. All eight production runtime hashes match
  before/after/post-run; provider archive matches its pin. No production rebuild
  or protocol, replay, clock, lease, expiry-seal or timeout-policy change.
- Host265 tests pass before and after live execution; syntax and diff checks pass.
  Prior SDK70/ROS41 remain earlier validations, not new runs. No builds/tests
  overlapped live slots. Owned containers, networks and selector are removed.
- Raw PCAPs, SQLite journals, resource inputs and provider sample streams remain
  local. [local-artifact-hashes.json](local-artifact-hashes.json) records their
  hashes except the removed ephemeral credential. Public `run-selected.json`
  copies omit repetitive provider sample arrays/adjacent deltas; bridge
  `*-selected.log` copies omit only PROVIDER_STATS samples. Trace and provider
  footers remain verbatim. [public-selection.json](public-selection.json) records
  every selected source hash, omitted field and derived hash; original local
  reports/logs are unchanged. The six-line host progress display alone has trailing
  whitespace normalized, recorded in validation/display-normalization.json.
  Archive/selection scripts are retained in validation/.

Next: instrument request kind and receiver admission/clock rejection boundaries
without changing outcomes or replay policy, freeze a focused diagnostic plan,
then investigate seed4211. Separately design loaded ROS/N5 discovery confirmation
with endpoint/callback observations. Preserve these failures; do not retry until
success or turn the N0 contradicted hypothesis into a DDS-default fix.
