# Late repaired-source ordering at the ROS boundary

The separately planned short-period fixture passes: a source packet absent on the
wire is reconstructed and delivered by the SDK, then explicitly rejected by the
bridge as `SessionError::replay` after newer typed samples have been observed.
Publication order does not regress. The original20Hz attempt remains failed and
is retained. This is finite single-route development evidence, not full N3/M3
acceptance. PR #2 remains draft; Intrinsic/M4 is untouched.

## Receiver diagnostics and preflight

The default-off sample trace now has schema2 point4, `receiver_decision`, in the
existing transport SPSC lane. It retains actual `srt_recvmsg2` message metadata,
original source epoch/session/route/ingress/envelope sequence, local owner/socket/
generations and the actual bridge Session admission result before applying its
action. Source identity is distinct from receiver owner identity. No payload,
callback or I/O is added to the record path; the ROS consumer formats logs.

The opt-in receive path uses the same public API as the pinned `srt_recvmsg`
wrapper, with a metadata output argument. Default admission, replay, clock, TTL,
SDK/command retry, wire, crypto and provider policy are unchanged. Consumers are
rebuilt for the trace layout. Schema1 source traces remain readable; receiver
records require schema2 and a valid original source epoch. Metadata does not
authorize decisions or replace packet/counter completeness checks.

Before the first attempt, all70 SDK tests,36 ROS-reported tests and190 host tests
pass. New native IPv4/IPv6 checks validate returned receiver message number,
original source epoch and admission result. The core Session regression admits a
newer sample, explicitly rejects the older still-current-session sample as replay,
keeps the session active and admits a subsequent fresh sample. The numeric replay
reason12 is asserted. Tests reject missing/duplicate/mismatched receiver events,
accepted or stale substitutes for replay, wrong source epochs, incorrect timing
and absence of newer typed publication evidence.

## Original20Hz attempt: failed precondition retained

Plan/code `01db3b8` ran exactly once:19 samples requested at50ms intervals, with
SDK message5 (first position of row1) dropped. All19 were admitted, but only18
were decoded by the bridge and published. No receiver decision exists for message5;
all18 observed decisions accept their samples. All six conservation balances are
zero, with one gap from SDK acceptance to receiver decode, not a bridge rejection.

The native incoming parity arrives103,247,708ns after the first later source
message6 exposed the gap. The pinned provider's `src/session.cpp` sets
`sensor_repair_deadline_microseconds=20000`, marks the gap on a later source and
expires it through `expire_sensor_receive_gaps`. FEC receives the current receive
floor. The observed timing and missing SDK delivery are consistent with this
mechanism; no internal expiry counter or exact retirement event was captured.
The absence is not relabeled as Session replay or a proven historical cause.

The original FAILED manifest is unchanged. Post-hoc closed-output analysis checks
18 source+5parity records in both native and PCAP populations and retains the
original gap1. No capture reconstruction or successful verdict is substituted.
The failure establishes that this50ms source schedule did not exercise the planned
bridge-level replay boundary.

## Separately planned short-period attempt

Revision `87922c3`, frozen after191 host tests, requests5ms source intervals while
retaining the provider's20ms repair deadline. Exactly one new fixture runs. It must
observe successor6-to-parity natively in strictly under20ms, a newer same-row typed
sample before parity, and an actual selected receiver replay result. The scheduling
and host harness change only; the receiver-trace runtime remains identical to the
70-SDK/36-ROS validated build. No failed-case replacement or further retry occurs.

| Observation | Result |
| --- | --- |
| Source calls / admitted / SDK source handoffs | 19 / 19 / 19 |
| Receiver decoded / rejected / typed published / observer | 19 / 1 / 18 / 18 |
| Selected SDK message / source ID / envelope sequence | 5 / 3 / 4 |
| Selected receiver classification | replay12 |
| Newer source IDs observed before incoming row parity | 4,5 |
| Incoming successor6-to-parity interval | 11,619,584ns |
| Original callback ingress-to-parity elapsed | 18,880,709ns |
| Sender / receiver trace records | 39 / 19, zero drops/exhaustion |
| Measurement source / parity records per endpoint | 18 / 5 |
| PCAP file / dispatch / kernel accepted per endpoint | 23 / 23 / 23 |
| Publication age upper maximum, accepted samples | 10,428,575ns |

One exact classifier drop removes the selected source; all completed-row parity
survives. The SDK nevertheless returns that original message, with matching source
identity and original ingress. The bridge records replay before publishing it.
Every other admitted sample is accepted and observed once with the expected typed
hash and order; later samples continue normally. All six balances are zero, with
only `receiver_rejected=1` nonzero and no SDK-accept-to-receiver gap. No BUSY occurs;
independent BUSY losses remain explicitly supported by the existing accounting.

The ordering check precedes Session age evaluation. The rejected sample therefore
has no evaluated conservative age bound. Its observed callback/native elapsed
intervals are not physical sensor age or proof of a selected-packet age check.
Accepted-publication age histograms, qualified clocks, same session, actual QoS,
zero stale/unknown-age classifications and unchanged features pass independently.
No original timestamp or budget is renewed and no SDK-accepted sample is replayed.

Both separate capture phases use the opt-in filter-before-bind recorder. They
retain initial kernel0, correct protocol/filter lifecycle, stable equal drains,
zero kernel/native losses, intact file hashes and exact native/PCAP identities.
There is no continuous cross-phase coverage or physical-wire assertion.

Requested5ms is not an achieved200Hz rate qualification. The finite first-to-last
source call span is116,171,459ns for18 intervals, about154.94Hz; median interval
6,040,146ns, maximum12,303,750ns. These are post-hoc finite call observations. The
actual row timing, rather than nominal rate, satisfies this test's repair horizon.
Full sustained200/50Hz IMU/joints and multiseed scheduling remain separate gates.

## Provenance and remaining work

Both prospective plans, original failed output, passing revision, post-hoc
analyses, source-cadence observations, build/test logs, trace/capture/status logs,
typed hashes/metrics, inventories and raw hashes are retained. Six selected runtime
hashes are stable across both attempts; the provider sources match the unchanged
pinned commit. Sources are separately hashed for each frozen experiment. Raw
captures, journals and detailed resource/clock traces stay under
`.local/m3-ros-late-repair/` and `.local/m3-ros-late-repair-r2/`; credentials are
removed and full inspect/environment dumps are excluded. No new full M2 acceptance
or comparison with older recorder workloads is claimed.

Next: full200/50Hz multiroute/rate/seed N3 qualification with phase-preserving source
scheduling and explicit admission/handoff accounting, then the remaining N4
admission/dispatch/result-commit barriers. Historical capture/reset/UNKNOWN cases,
DDS discovery/security/age equivalence and other M3 gates remain open.
