# Loaded probe tracing complete; move to reconciliation implementation

The single predeclared cohort passes both slots. It closes the current
instrumentation loop under [DELIVERY_PLAN.md](../../DELIVERY_PLAN.md); no follow-up
run or new tracer is scheduled automatically. The next deliverable is a bounded,
authoritative sender submission receipt and conservative journal reconciliation.

Frozen source `1fdf7cb9a661284ba295ca377fa3ebf22da99b25`, exact calibrated
probe-tracing SDK/ROS binaries, no rebuild/tuning/forced expiry/historical118
replay. Older failed cohorts and the stopped4211 slot retain their verdicts.

| Slot | Commands / effects | Skipped offers | Harness / strict / durable |
|---|---|---:|---|
|N0/1701/15s|8/8 succeeded,8 effects|0|PASS / PASS / PASS|
|N5/1701/300s|128/128 succeeded,128 effects|22|PASS / PASS / PASS|

No new unresolved, UNKNOWN, expired or unadmitted command. This is one diagnostic
cohort, not the full M3 comparison matrix or production/hardware acceptance.

## Decision-relevant probe evidence

N5's complete recorded lifecycles, including setup and drain, contain:

-615 timer attempts:443 emitted probes and172 probe_busy results.
-443 exact cross-peer probe/reply joins:398 qualified mapper admissions and45
  rejected replies. All45 are old echoed t1 values arriving while a different,
  newer t1 is pending.45 natural tick clears are recorded; no expiry was forced.
-886 successful local SDK handoffs, with no SDK error/would-block observation.
  Local queue-to-SDK wait maximum0.950125ms. SDK-call-end to peer application
  admission maximum3514.765669ms, on the proven common VM clock. This interval
  includes SRT buffering/recovery, ordering and peer owner admission; it is not
  a unique network/drop cause or physical-wire transit measurement.
-Maximum accepted probe round trip1934.701543ms; minimum rejected round trip
 2009.280043ms. The unchanged2s/pending-echo admission rule is behaving as defined.
-Two sender clock defer/recovery pairs (fresh counters49 and85); both keep their
  original command budgets and close succeeded. No pending-input deadline drop
  occurs in this cohort, so that journal gap remains a source-established target,
  not a newly reproduced outcome.

427 of443 N5 probe attempts begin inside the source publication window. Whole-run
totals above deliberately retain setup/drain; the compact lifecycle file records
window membership per attempt. N0 has50 qualified probe joins, no busy/rejected/
pending-clear observations, and30 probes beginning inside its source window.
All native/command/provider/path capture gates pass, with complete traces and no
active-window context-loss observations. Raw SENSOR age/conservation metrics
remain in the gate report; sample drops under overload are not alone a failed
freshness/boundedness contract.

We have enough evidence to distinguish timer attempts, queueing, local SDK
acceptance and rejected echoes. Repeating broad ARP/packet archaeology would not
change the selected correctness/status fix. No probe-rate/timeout or queue tuning
is justified or performed by this report.

## Compact evidence and preservation

[`gate-report.json`](gate-report.json) contains original gate outcomes, counters,
stage delays and SENSOR metrics. `command-proofs.json` retains every original
attempt's closed journal proof; `probe-lifecycles.json` retains all493 probe
lifecycle summaries, and `probe-examples.json` includes two full representative
N5 joins (late reply and near-limit accepted reply). No selected stream is
misrepresented as the complete raw stream.

All303 new raw files remain locally retained by exact hash, including complete
run/execution reports, logs, PCAP/native/provider/SQLite/sample streams. Their
explicit disposition is recorded.798 earlier raw files and all selected/new/older
runtime and observer inventories match before/after checks. Both owned networks,
containers, observer rules and credentials are removed; roots/features match
before/after. No heavy work overlaps live capture.

Host398 checks passed before the run; exact SDK79/ROS41 qualification was reused.
The runner changed only to select the explicit probe-tracing cohort/layout and
enforce its existing positive diagnostic gate. No runtime/provider implementation
changed. Post-closure work is the short read-only `validation/close.py` script.

M3 remains open and PR2 draft. Historical118 stays UNKNOWN/reconcile_required;
this successful cohort cannot retroactively settle118/34/98/12. Intrinsic/M4
is untouched. Proceed with the implementation contract in DELIVERY_PLAN.md,
then the remaining N3/DDS acceptance gates—not another open-ended probe study.
