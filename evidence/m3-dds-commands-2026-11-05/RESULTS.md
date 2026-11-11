# DDS command acceptance results

The N0 common-VM development scenario exercised actual rate changes with
concurrent typed simulator telemetry. It is not the fixed-200-Hz full M3 workload.

| Intent | Rate / generation | Observed journal outcome | Device effects |
| --- | --- | --- | --- |
| 1 | 100 Hz, 0 → 1 | SUCCEEDED; duplicate returns same result; conflicting payload reports conflict | 1 |
| 2 | 75 Hz, 1 → 2 | UNKNOWN / effect_uncertain after unobserved delayed handler reply; duplicate does not resend | 1 |
| 3 | 50 Hz, 2 → 3 | UNKNOWN / context_lost after receiver SIGKILL following effect and sender SIGKILL before reconciliation | 1 |
| 4 | 200 Hz, 3 → 4 | SUCCEEDED after explicit test-device reconciliation and resetting the fault delay | 1 |

Four unique intents, four effects, two confirmed success results and two deliberately
UNKNOWN outcomes. UNKNOWN entries have no valid result. Neither uncertain intent
was replayed. The sender emitted three COMMANDs before SIGKILL, then one QUERY
and zero old COMMANDs after reopen; its only subsequent COMMAND was new intent 4.
Live duplicate intent 1 and conflicting reuse of ID 1 emitted no extra COMMAND.

Both closed journals pass SQLite `quick_check` and contain exactly IDs 1–4, all at
revision 3, with identical payload hashes, state/reason and result fields. The
sender and receiver agree on SUCCEEDED(1), UNKNOWN(2), UNKNOWN(3), SUCCEEDED(4).
The journal inspector reads files only after container cleanup and does not
substitute for DDS status observations in the driver.

Seven session tests verify mutual acknowledgment/namespace qualification,
replay/wrong-target/wrong-process/future-time rejection, nonce rotation on lease
expiry, retired-peer rejection/capacity bounds, invalid replacement failure and
refusal of wrong-session heartbeats to extend a lease. Eighteen ROS GTests passed
(21 with wrappers); nineteen Python tests passed. The original SRT M2 regression
also passed. All final source inventory hashes match.

DDS captures have 5,107 robot and 5,081 operator frames, complete and without
unaccounted frames or tcpdump kernel drops. Counts differ across endpoints because
local/multicast observations are not a matched sensor/command wire window. One
sender callback admission drop after restart remains visible in diagnostics.
No isolated-WAN loss, lossless application admission, latency superiority or full
M3 acceptance is inferred from these results.
