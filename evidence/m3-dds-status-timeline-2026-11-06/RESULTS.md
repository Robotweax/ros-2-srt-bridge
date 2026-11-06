# Short N2 follow-up results

All three frozen runs passed without retries. 84 distinct admitted intents ended
with 82 confirmed successes/effects and two receiver-backed expiries (revision 1,
zero dispatch, invalid result). All six closed journals pass integrity checks and
agree on immutable commands and terminal states. No intent remains unresolved.
No NOT_FOUND or missing status is treated as nonexecution.

| Seed | Attempts | Successes/effects | Expired without dispatch | Unresolved | Skipped command slots | Maximum terminal-observation latency (ms) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1701 | 28 | 27 | 1 | 0 | 2 | 5412.994 |
| 2903 | 30 | 30 | 0 | 0 | 0 | 1448.268 |
| 4211 | 26 | 25 | 1 | 0 | 4 | 8458.562 |

Both expiry runs report one stale COMMAND at the receiver. The driver histories
retain 27 polls for seed 1701 intent 12 and 42 for seed 4211 intent 15, including
local queued observations after the five-second budget and a final authoritative
expiry. Neither history is truncated. Later distinct intents succeed without
advancing generation for the expired intent. These are original-session durable
absence seals, not evidence that context-changing failures can always resolve.

Seed 1701 confirms its expiry after 5.413 s; seed 4211 takes 8.459 s. Prompt effects
and eventual terminal agreement do not imply a terminal-status time guarantee.
The historical 10.871 s success remains a separate observation. No run is dropped
or replaced to improve latency, and no freshness/deadline policy is weakened.

All six PCAPs report zero kernel drops. Native v2 recorders have zero reserve/copy
failures and qualify both measured phases. These are socket-tap observations,
not physical wire or callback delivery. The same common VM/zero-offset clock proof
is recorded at both endpoints. Containers are private, nonprivileged, with NET_ADMIN
and opt-in BPF capabilities, no host networking or published ports.

The plan froze 161 source files, eight selected installed application/worker/
capture/SDK hashes and installed Python script bytes. All three run inventories
match that plan; selected binaries and measured scripts remain unchanged. After
the runs, the offline analyzer/test added a current-owner guard. Its two frozen
versions/hashes are retained, and final analysis reproduces all three timelines
exactly. The 56 compiled production sources remain unchanged from bb44d5f.
83 final host Python tests pass; the demo Python package was installed normally.
No new ROS GTest/full M2 execution is claimed.

Each workload is only 60 s. This step does not satisfy the full 600-second matrix,
physical tap/device coverage, isolated observer resource cost, transport semantic/
security parity or complete M3 acceptance. No SRT/DDS performance advantage is
claimed. Raw PCAPs/native prefixes/SQLite/clock samples stay local with hashes.
