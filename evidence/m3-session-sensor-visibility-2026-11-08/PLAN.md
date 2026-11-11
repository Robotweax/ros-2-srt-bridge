# Session2903 reproduction and targeted SENSOR visibility

Preserve the original2903 unresolved intent98 and every prior verdict. Read-only
provider52be7c8 source/API only; never edit .deps/srt or enclosing repository.
PR2 stays draft; M3 incomplete; Intrinsic/M4 untouched. No tuning, clock/budget,
wire, queue policy, journal or accepted-command replay changes.

Add separate default-off bounded SENSOR provider observations through the pinned
existing non-clearing srt_bstats API. Reuse bounded SPSC storage with independent
cadence/budget/footer, read brackets, source owner/session, SENSOR generation and
socket/state, plus before-close sample. Observe cumulative DATA/unique counters,
loss/drop/undecrypt, FEC extra/supply/loss and queue/flight/flow gauges. Keep old
CONTROL stream/parser compatible and reject incomplete SENSOR evidence. Expose
only available API semantics: aggregate drop cannot identify exact retirement or
insert rejection reason; no per-message delivery counter or typed encrypted mapping
exists. Record those unavailable internal dimensions explicitly rather than zero.
Provider mutex/bookkeeping and observer overhead are part of this new cohort.

Implement/test first, freeze source/build/runtime hashes before live. Full SDK
Release/Werror, ROS tests, host parser/native guards before live; no tests/builds/
heavy analysis while live. All8 installed artifacts fixed across runs; provider
archive pinned unchanged. Native positive SENSOR traffic and independent streams,
close samples, bounded queues/budgets and parser loss/unavailable/reset/saturation/
channel identity guards must pass. Preserve any failed preparation/measurement.

New cohort exactly once, serial, no retry: N0 seed2903 15s; N5 seed2903 300s.
Same dynamic neighbors,512kbit shaping/16packet child/128Kbit competitor,
200/50Hz sources,2s offered commands,original5s budgets,8s result drain as original.
Add kernel-monotonic v2 passive capture, CONTROL and SENSOR provider streams,
command traces and tcpdump readiness/drain. This is changed observation workload,
not a replay of the original measurement or a mitigation. Stop after any capture/
provider/runtime/integrity or selected durable-completion failure. Always report
strict all-success and success-or-qualified-durable-expiry separately, skips and
unresolved intents; passing recurrence cannot close original intent98.

After closure, correlate all >=1s old-CONTROL-flow source gaps and all active
CONTROL link/session losses against same-generation provider brackets and native
v2 capture, using existing strict mapping/time/identity guards. Report withheld
mappings and censored boundaries. Compare SENSOR snapshots by connection/side
without inventing application-window deltas at different read times; cumulative
DATA/unique/filter/drop/undecrypt and queue gauges are not typed SAMPLE accounting.
Reconcile taps and application balances independently. A failed reproduction
remains failed; a pass means recurrence not observed, not fixed. No diagnosis from
PCAP realtime, zero counters, NOT_FOUND or absent receiver rows alone.

Archive original run manifest, selected logs, source/runtime proofs, all raw-file
hashes and exact public omissions, including before/after unavailable snapshots.
Remove owned containers/networks/credentials. No provider patch or mitigation in
this cohort. Remaining internal reason/delivery visibility requires a separately
reviewed upstream surface; no dependency modification is part of this plan.
