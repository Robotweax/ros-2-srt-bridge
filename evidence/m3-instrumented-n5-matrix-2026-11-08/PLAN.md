# Finite instrumented three-seed N5 progress matrix

Freeze source and this plan before live execution. This is one prospective cohort,
not a retry/reclassification of the historical seed4211 unresolved intent. No
production build/change, replay, timeout/start-budget/clock policy, expiry seal,
provider, DDS-default or load intervention. M3 open; PR2 draft; M4 untouched.

Exactly these sequential slots, once each, stop on first failure and mark all
remaining slots NOT_EXECUTED. No replacement/repeat/additional seed after results:

| Order | Profile | Seed | Measurement seconds |
|---|---|---:|---:|
|1|SRT N0 control|4211|15|
|2|SRT N5|4211|300|
|3|SRT N5|1701|300|
|4|SRT N5|2903|300|

Start with the historical suspect seed, then the other two base seeds. Existing
pinned linux/amd64 image/provider and b8f5418 diagnostic runtime remain fixed.
Use dynamic neighbors, same telemetry targets200/50Hz, 2s offered command slots,
original5s start budget and8s result drain. No auxiliary clock/source/sample/neighbor/
qdisc observers or artificial faults. Command and provider diagnostics plus stable
tcpdump drain checks match the prior focused instrumented run. Require listener
readiness before applications, complete capture populations, provider/trace footers,
zero trace drops, source hashes and all8 runtime hashes unchanged throughout.
No builds/tests overlap live slots; host tests/syntax precede measurement.

Run tools/m3_admission_diagnostics.py --matrix three-seed with a fresh output path.
Each success must retain matching closed sender/receiver journals, dispatch within
saved receiver deadline, original sender budget, one SDK handoff and exactly one
receiver admission/worker pair bound to original request/session/route/origin and
wire sequence. Duplicate/stale/wrong-context observations do not substitute.
Record every attempted/unresolved command, final live status/history omissions,
effects, offered/skipped slots, telemetry losses/accounting and active context
change observations. Do not turn sensor accounting or command progress into full
N5, delivery, latency, hardware-clock, overhead or superiority qualification.

For a recurrence, preserve original workload verdict separately from stricter
progress verdict. Analyze only closed inputs. Correlate clock rejection13 and
matched COMMAND peer error5 by original request/session/route/sequence/kind; inspect
AgeResult2 expiry versus9 future_sample and clock state/deadline. Record receiver
worker observations and missing ones without claiming nonreceipt/nonexecution.
NOT_FOUND, elapsed budget, receiver journal absence and cleanup UNKNOWN do not
resolve live uncertainty or authorize replay. Distinguish live and post-shutdown
state and context reset. Archive failure even when captures are complete; if no
recurrence, report bounded coverage, not a fix or historical resolution.

Raw PCAP/journals/resources/provider samples remain local with original hashes.
Public selections explicitly enumerate omitted repetitive fields/lines and retain
command/status/capture footers, selected results and original/derived hashes.
Cleanup only owned namespaces. Stop the cohort after any failure, archive and
review before proposing another plan or fix. No N3/DDS/Intrinsic scope expansion.
