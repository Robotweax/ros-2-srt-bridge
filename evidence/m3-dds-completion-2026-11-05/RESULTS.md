# DDS command completion diagnostics

All rows are development runs. N2 uses 60-second windows, N0 30 seconds,
N4 15 seconds. Defaults and all freshness, lease, deadline and no-replay gates
remain unchanged. N5 simultaneous startup is retained separately even on failure.

| Run | Confirmed / attempts | Unresolved | Effects | Stale commands | Matched NOT_FOUND replies | Max sender publish ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| n0-30s | 15/15 | 0 | 15 | 0 | 0 | 0.139 |
| n4-smoke | 4/5 | 1 | 4 | 0 | 59 | 0.602 |
| n2-1701 | 2/3 | 1 | 2 | 1 | 247 | 0.343 |
| n2-2903 | 28/28 | 0 | 28 | 0 | 0 | 0.254 |
| n2-4211 | 11/12 | 1 | 11 | 1 | 171 | 0.337 |

The stale commands arrive at the application callback at ages 2,212.649 ms
(seed 1701) and 2,474.505 ms (4211), before their five-second start deadlines.
They fail the unchanged 1.5-second packet freshness gate. Their IDs match the
unresolved rows, their receiver journals have no entry, and their sender entries
remain LOCAL_QUEUED. The final rows retain NOT_FOUND observations. Both peers
end ready in all three N2 probes. The sender publish-call maxima stay below 1 ms;
that does not identify whether delay was in repair, queueing, transport or executor.
N4 ends ready at both peers, with session rejections during the outage and an
unresolved intent; it has no stale-COMMAND counter increment. N5 again fails
before measurement, with no matched endpoints or delivered HELLOs at either side.

See command-diagnosis.json for each stale command ID, exact application ingress
age, final readiness, last local status observation and read-only journal lookup.
control_checks counts only session validation after kind/route/ID checks; index
zero means that check passed, not durable admission or handler start. Counters
are cumulative snapshots, not an exact pipeline conservation ledger. Publish
duration measures the Reliable publish call only; it does not isolate network,
executor, middleware history or queue delay.

24 actual ROS GTests (27 including wrappers), 32 host Python tests and the full
DDS fault acceptance pass. The new deterministic test checks each rejection
reason, exact stale boundary, live HELLOs during stale control and no cursor
advance on rejection. The status tests prove that NOT_FOUND and elapsed local
observation budget do not create terminal state, result or nonexecution evidence.

All seven final source inventories and binary hashes match. Installed Python
files match byte-for-byte. SDK/core, wire v1, worker IPC v3 and SRT are unchanged.
Raw captures/journals remain local; hashes and sizes are preserved. The prior
N2 capture analysis is separate from the new runtime counters. Full M2 and
five-minute N0 evidence remain at commit 940b4cb; these diagnostics do not rerun
or supersede those historical results.

No complete M3 acceptance, cross-host clock/security equivalence, matched CPU/wire
comparison or performance superiority is claimed. N2 seeds here are short probes,
not the full 600-second qualification matrix. N4 is a mid-window outage, not a
precise admission/dispatch/result-commit barrier. N5 discovery remains open.
