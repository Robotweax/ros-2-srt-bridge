# DDS terminal-status timeline — 2026-11-06

This step investigates the 10.87-second invocation-to-terminal-observation wait
in the preceding v2/large-buffer N2 development probe. It adds bounded driver
status-poll history and a read-only closed-journal timeline tool. Production
C++/SDK/wire/IPC, control QoS, freshness, TTL/lease, atomic handler-start rules,
expiry sealing and no-replay policy are unchanged. Intrinsic/M4 remains untouched.

## Historical command 15

The saved journals and driver row place these timestamps in a proven common
Linux VM/zero-offset time namespace. Deltas are observations, not latency bounds:

| Stage | Observed delta (ms) |
| --- | ---: |
| Driver invocation to coordinator origin | 0.443333 |
| Origin to sender admission timestamp | 1.134000 |
| Sender to receiver admission timestamp | 70.332334 |
| Receiver admission to dispatch timestamp | 6.920666 |
| Dispatch to receiver finish timestamp | 4.637250 |
| Receiver finish to sender result-observation timestamp | 10655.113547 |
| Sender observation to driver terminal observation | 132.406500 |

The receiver finish timestamp is 83.47 ms after invocation; the dominant wait
follows it. Journal timestamps are sampled **before state mutation/SQLite commit**,
not fsync completion or atomic handler claim. Dispatch-to-finish is not isolated
handler execution. Sender observation includes journal/middleware/scheduling and
reconciliation. The closed receiver/sender records agree on SUCCEEDED/revision 3,
payload hash and result generation. This decomposition does not relax deadlines.

A supplemental offline CDR fingerprint probe uses the generated ROS decoder on
unfragmented RTPS UDP payloads, checks decoded identities/hashes/contexts against
closed journals and retains serialization roundtrip differing offsets. It is
not a general RTPS parser or reassembler and does not claim complete middleware
population coverage. All 516 decoded observations uniquely match a native record
by full frame length and 128-byte prefix. Timestamps below come from those native
records; PCAP realtime is not converted to monotonic. Full packets/prefixes stay
local. A tap observation does not prove middleware delivery or callback acceptance.

| Robot STATUS control sequence | Command | Header sent time relative to command-15 invocation (ms) | First operator tap observation (ms) |
| --- | ---: | ---: | ---: |
| 55 | 14 | -459.252 | 10735.753 |
| 58, SUCCEEDED/revision 3 | 15 | 85.828 | 157.518 |
| 62, SUCCEEDED/revision 3 | 15 | 759.585 | 10735.753 |
| 100, SUCCEEDED/revision 3 | 15 | 8651.041 | 10735.753 |
| 110, SUCCEEDED/revision 3 | 15 | 10741.123 | 10779.612 |

Successful command-15 STATUS frames reach the tap early, while a preceding
control sequence first appears much later. Sender diagnostics count 51 stale
control rejections, zero inbox drops, zero lease expirations and no control
publish call over freshness. Reliable ordered middleware delivery/retransmission
blocking followed by freshness rejection is consistent with these observations;
this is an inference, not per-frame callback proof or a uniquely attributed
network/middleware root cause. The historical trace lacks callback timestamps.
No claim is made that every missing initial observation was a particular netem
drop. KeepLast/Reliable semantics and the 1.5-second freshness check remain intact.

## Instrumentation and limits

Each future DDS workload intent retains the first 32 and most recent 32 local
GetCommandStatus responses. `status_observations_omitted` explicitly counts the
gap after 64 polls; complete histories remain complete when at most 64 polls
occur. Snapshots retain found/state/reason/local_error/revision/query_queued,
observation time and budget-elapsed flag. They are driver service observations,
not remote callback traces. Missing/NOT_FOUND/timeouts do not manufacture a
terminal result or prove nonexecution. History collection changes the test
observer workload; no causal resource comparison uses these runs.

`tools/m3_dds_result_timeline.py` reads only completed combined DDS runs and
checkpointed journals, opens SQLite immutable/read-only, verifies identity/schema,
command hashes and unchanged files, and requires matching common-VM/zero-offset
clock proof. Matching original-owner successes receive a timeline; missing,
unknown or changed-owner observations retain explicit uncertainty. Inconsistent
contexts/timestamps reject. The helper never transmits, seals or retries intents.

```sh
python3 tools/m3_dds_result_timeline.py .local/m3-dds-combined/RUN \
  --out .local/fresh-timeline.json
```

The output path must be fresh. Never use live or uncheckpointed databases.
The evidence includes the historical analysis, supplemental decoder source and
sanitized observations, then a frozen three-seed N2 follow-up with poll history.
Each new run is 60 seconds, default system DDS, native capture on, same 32,768-KiB
PCAP request, fresh owned containers, no retries or policy relaxation. These are
short development repetitions, not the full 600-second/three-seed acceptance.

All three new runs passed: 82 successes/effects and two expiries without dispatch,
zero unresolved intents, zero PCAP kernel drops and native recorder losses.
83 final host Python tests pass. The current-owner guard was added to the offline
analyzer/test after the live runs; their frozen versions are retained and final
reanalysis reproduces all three timelines exactly.

See [results](RESULTS.md). No new ROS GTest/full M2 execution is claimed. Earlier
failed smaller-buffer evidence remains separate and unchanged. M3 and PR #2
remain in progress/draft.
