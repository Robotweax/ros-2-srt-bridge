# Prospective SRT admission diagnostics

Freeze this plan and the diagnostic source before any live slot. This is a new
instrumented cohort, not a retry or replacement of the preceding4211 failure.
No production behavior fix, replay, expiry-seal, lease, start-budget, SDK/provider,
clock-policy or DDS-default change. M3 remains open; PR2 draft; M4 untouched.

Execution order exactly once, stop after first failure with later slots skipped:

1. SRT N0 seed4211,15s, positive diagnostic/command control.
2. SRT N5 seed4211,300s, same workload/seed/duration as the unresolved historical
   slot, now instrumented. No additional seeds or attempts after seeing results.

Image remains the pinned linux/amd64 digest; same dynamic-neighbor default,
200/50Hz sensor targets, 2s offered command slots, one SDK handoff per fresh
command, original5s start budget and8s result drain. Skip builds in live runs;
all builds/tests must finish before the cohort, none overlap its live windows.
Retain complete trace/provider footers, both ready tcpdump listeners before app
start, capture file/filter/footer/kernel population gates and stable drain.
Record all eight runtime hashes after the diagnostic rebuild and require them
unchanged across live slots; verify provider pin and original source hashes.

New opt-in bounded observations preserve existing producer lanes/default-off
behavior: transport COMMAND/QUERY admission decision with original kind, identity,
sequence, origin, evaluation time, clock state/deadline and returned age error;
receiver admission/query worker completion with JournalError; sender correlated
peer error with original COMMAND/QUERY kind and request sequence. No sample trace
or new observer intervention. Footers must show zero drops; confirm each success
has receiver admission and worker observations in addition to matching closed
journals and unique SDK handoff. Raw inputs stay local with hashes; public
selections must explicitly record omitted repetitive samples.

Native tests before live must exercise real success, missing-query worker result,
capacity rejection, COMMAND versus QUERY peer errors, and a controlled
receiver-only clock-expiry gap. This synthetic clock test validates observation
boundaries; it is not the historical N5 cause. Preserve interrupted build history
and final source/build/test provenance separately.

Prospective interpretation: correlate receiver clock rejection and sender error
only on identical session/route/request/original sequence/kind, distinguishing
ClockError expiry/unqualified/future-sample where observable. Record unresolved
intent, last live status, closed journals, all handoffs, effects, skipped slots
and active context-change observations. A recurrence can locate an observed
boundary; it cannot invent a durable negative outcome or authorize replay. A
nonrecurrence does not resolve the earlier failure. Any capture/trace/worker or
progress failure remains FAILED; no retry. No full N5 or transport-superiority
claim even if both slots pass. Analyze the closed cohort before proposing fixes.
