# N5 command progress and DDS cold-start diagnostics

The five slots frozen in [PLAN.md](PLAN.md) and source `57f415b` ran once each,
sequentially in fresh owned namespaces. Four pass their bounded workload/proof
gates; default DDS simultaneous startup remains **FAILED before measurement**.
No retry, default transport change or historical verdict replacement occurred.
This is development evidence, not full N5/M3 acceptance or a transport comparison.

| Slot | Workload seconds | Confirmed / attempted | Effects | Unresolved | Skipped slots |
| --- | ---: | ---: | ---: | ---: | ---: |
| SRT N0 preflight |15|8/8|8|0|0|
| SRT N5, dynamic neighbors |60|23/23|23|0|7|
| DDS system, simultaneous |No qualified window|—|—|—|—|
| DDS system, control-first |15|2/2|2|0|6|
| DDS paced-sensors, simultaneous |15|8/8|8|0|0|

“Pass” here includes conservation/journal proof and retained unsuccessful workload
slots, not a command in every two-second slot or a delivery/latency guarantee.
The failed DDS slot issued no workload intents. Its failure is not a zero-latency,
zero-loss or successful command result. Independent later candidate slots were
explicitly planned to execute even if the default failed.

## SRT prospective progress

N5 retains the default dynamic neighbor fixture,512kbit/s per egress direction,
16-packet child queue and128000bit/s competing offered UDP load. Runtime iperf
readback confirms128019.844bits/s across the competitor lifetime, not matched-
window delivered load. The baseline's old131072bit/s description was corrected
to the already configured/runtime-verified128000bit/s; workload settings did not
change. Seed1701 is unchanged. Command/provider diagnostics and bounded capture
drain checking add observer work; no observer-free performance claim is made.

Each successful intent has matching closed sender/receiver journal identity,
original origin/hash/session/result generation, exact sender ingress+5s and
receiver dispatch before its earlier/equal conservative deadline. Sender traces
contain one SDK COMMAND handoff per intent, with no accepted-command replay.
Complete lifecycle/footer populations cover all three recorded bridge incarnations:
N0 counts42/5/5; N5 counts87/5/5. The robot's initial bridge replacement is setup,
not an active-window crash. All provider log completeness gates also pass.

The N5 active source window contains no recorded session-change/invalidation/
session-action/link-loss events. This does not prove continuous packet progress,
reproduce or fix the historical spontaneous reset, or change any old UNKNOWN.
The original start budget constrains execution eligibility, not when a final
status must be observed. Maximum terminal observation is3421.882377ms, median
1511.716501ms. Maximum adjacent intent-submission gap is4023.803085ms; seven
slots are skipped while prior work remains pending. One terminal result is
observed in the original bounded post-cutoff drain.

Actual source rates are199.983578/50.000054Hz over60.099935s. Sensor populations
are15024 produced,5543 published/observed,9481 missing, with all six balances0.
Loss terms are upstream DDS1, admission27, ingress flush77, outbound replacement
490, outbound flush2, SDK-to-receiver gap8762 and receiver rejection122. These
remain explicit deficits, not independently attributed WAN losses. Publication
age upper histogram maxima are153ms IMU/170ms joints, not physical sensor age.
N0 produces3784/observes3661, with123 locally accounted losses and six balances0.

## DDS sampled discovery and startup contrast

The new bounded development timeline records local command diagnostics, typed
callback counts and wait phases. Within unchanged phase/readiness it writes at
most once per second; phase/readiness/failure transitions can add records. Its
2048-record limit fails closed on exhaustion, reuse, missing footer, population
mismatch or regressed timestamp. Samples can miss intervening transitions and
neither endpoint matches nor HELLO callbacks prove authenticated packet delivery.

Default system/simultaneous startup times out at the unchanged45s sender readiness
gate. Both46-record histories have complete footers:

- Sender: no complete CONTROL/HELLO endpoint match observed; last counts are0
  publishers/subscribers for both channels. Local HELLOs sent436, received0.
- Receiver: complete endpoint matches observed (1 publisher/subscriber on each
  channel), local HELLOs sent438, received0.
- Both have journal_ready, handler_ready and qos_verified true, ready/peer_ready
  false, and no failed coordinator or lease expiration in the final sample.

This local asymmetry precedes mutual session qualification. It supports targeting
DDS discovery/delivery rather than modifying application command replay or lease
semantics. It does not identify the exact RTPS sample, kernel queue/drop stage,
unique failure cause or prove that every past failure followed this path. No
packet-level RTPS decoder or causal intervention was part of this measurement.

The independent control-first slot verifies zero source publications before
command qualification, then starts the same source under N5. It confirms2 commands
but skips6. Sender final lease-expirations2, receiver0; each peer has one not-ready
sample inside the source window. One command result is observed16087.948466ms
after submission, inside the original <=8s post-cutoff drain and with a receiver
start before its original5s deadline. This is delayed observation/reconciliation,
not permission to start expired work. Readiness at the end does not erase that
history. Its last new intent is about12.997s before cutoff. Startup ordering alone
is insufficient for continuous progress in this run.

The independent existing paced-sensors candidate starts simultaneously and confirms
8/8 intents, skips0, has0 lease expirations and all16 in-window readiness samples
per peer true. Maximum terminal observation is229.215041ms. This is not an isolated
pacing causal experiment: the candidate also uses its existing UDP/SHM1200-byte
configuration, asynchronous sensor writers and sensor-only shared1600bytes/50ms
controller. The system default remains unchanged; Reliable/Volatile/KeepLast64
CONTROL and BestEffort/Volatile/KeepLast1 HELLO QoS remain unchanged.

The source rates and sensor service remain visible:

| DDS candidate | Actual IMU / joints Hz | Produced | Callbacks accepted | Missing before callback |
| --- | --- | ---: | ---: | ---: |
| System/control-first |199.949608 /50.037108|3772|1718|2054|
| Paced/simultaneous |200.006660 /50.001665|3785|967|2818|

Both have zero observed invalid/stale/clock-rejected callbacks. Their DDS age
checks use shared-VM realtime estimates, distinct from conservative SRT intervals;
missing source samples and reduced sensor service are not hidden by command
success. Workload durations, startup ordering, observers, framing and security
costs are not controlled equivalence for a comparative performance conclusion.

## Failure detection and capture integrity

DDS scenarios now check peer/parent abort and report every owned command node and
simulator through the existing tested shutdown helper: pre-signal status, SIGINT
bracket, exit code, forced kill and errors. The parent allows12s for scenario
cleanup before namespace removal; startup/readiness deadlines are unchanged.
All three DDS slots have all three child reports clean/exit0, including the failed
startup. That failed slot's two scenario processes exit1 as expected; both exit
before namespace teardown. Clean cleanup never changes its FAILED verdict.

All five runs' per-endpoint PCAP file/captured/filter populations reconcile with
zero kernel drops. Counts are operator/robot respectively8194/8194,22482/22482,
7114/7086,9838/9856 and4221/4231. Per-endpoint population integrity does not equate
those populations or pair DDS discovery datagrams between interfaces. Realtime
PCAP window timing remains withheld by clock qualification; packet counts are not
age authority, independent physical-wire delivery or a causal kernel trace.

## Validation, provenance and next work

245 host tests pass before and after the runs. New negative tests distinguish
missing diagnostics/matches/HELLO/readiness, reject exhausted/truncated/reused
histories and regressed clocks, require durable identity/deadline/effect proof,
retain UNKNOWN despite NOT_FOUND/elapsed time, and reject late-result phase
misclassification. Syntax/diff checks pass. The analyzer was also checked read-only
against a retained22-success SRT fixture before the frozen live set.

Eight production runtime hashes match before/after and an independent post-run
inventory. Every run source manifest matches frozen57f415b. Changes are Python
fixture/observer/lifecycle/analysis only; no SDK/ROS C++/worker/provider binaries
were rebuilt. Prior full SDK70/ROS41 remain the latest full validations, not new
acceptance runs. The existing paced-profile preflight verifies its actual settings.
All owned containers/networks and SRT credentials were removed.

[execution.json](execution.json) retains every original slot/verdict, closed-journal
proof metadata and startup/shutdown summaries. Selected original manifests/logs,
qdisc/readbacks, source fences, command states, timeline and capture footer metadata
are preserved. [post-hoc-observations.json](post-hoc-observations.json) explicitly
labels later descriptive window/readiness/tail analysis; no original run or gate
was rewritten. [local-artifact-hashes.json](local-artifact-hashes.json) retains raw
file identities. Raw PCAPs/journals, detailed clock/resource samples and full
inspect/environment dumps stay local; credentials are excluded entirely.

Next: prospectively localize the default DDS asymmetric discovery signature with
independently qualified packet evidence and a known-loss/control contrast, then
define longer SRT N5 progress coverage. Keep the paced candidate separate. Do not
select repeated spontaneous runs until a favorable result appears. Historical
causes/UNKNOWNs, full N5/M3, clock/security/resource parity, cross-host/physical-age
and hardware acceptance remain open. PR2 stays draft; Intrinsic/M4 is untouched.
