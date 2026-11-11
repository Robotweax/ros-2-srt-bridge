# Bounded sample admission / SDK handoff observer

One separately planned finite observer validation passes. This is not a new N3
baseline cohort, does not replace either prior failed ROS attempt, and does not
establish full N3/M3 acceptance. No ROS one/two-loss case ran. PR #2 remains draft.

`sample_diagnostics` is off by default. When enabled, two independent fixed SPSC
lanes retain ROS callback admission results and transport SENSOR SDK observations.
Each lane has128 slots,256 total, with a75000 attempted-record budget. Overflow
and exhaustion are explicit and fail correlation checks. The ROS lane has exactly
one single-threaded executor producer; the transport lane exactly one owner.
Other public `submit_sample` callers do not emit ROS lane records. The record path
has no allocation, I/O, mutex or retry; the single ROS consumer formats JSON.
The observer adds work and has no performance-equivalence claim.

Admission events retain the original callback ingress timestamp, context, route,
callback sequence, source message header timestamp, serialized body size and exact
submit result, including BUSY. Transport events include the retained origin and
envelope sequence, packet size, local socket/generation, returned SRT message
number and actual `SRTO_ISN` readback. The opt-in path uses `srt_sendmsg2` with the
same initialized TTL/ordering metadata as the pinned `srt_sendmsg` wrapper. The
SRT archive, wire/crypto/clock/deadline/pacing/admission/retry/command policies are
unchanged. SDK acceptance is not delivery authority. ISN readback occurs after
the bracketed send; it is static connection metadata, not an in-bracket counter.

Correlation joins source header timestamps to unique callbacks, then original
ingress/route/owner/session/generations to SDK results. Cross-lane event sequence
is not causal order: the SDK may progress before the ROS thread records its
returned submit result. A successful handoff must not precede the admission-call
begin. Queued inputs without an observed handoff remain explicitly unmatched;
there is no absence/retry inference. Duplicate identities, missing final status,
loss, exhaustion and incomplete metadata fail checks. Candidate wire sequences
use the first source-message cycle (including the binding) of this pinned
one-packet-per-message SENSOR contract and must agree with captures;
they are not inferred from ROS publication count.

Measured code/plan was frozen in `125f86f`. Before measurement,70 SDK tests,
36 ROS reported tests and176 host tests pass. Tests include bounded lanes,
overflow/budget/concurrent FIFO, actual SDK metadata with original ingress and
binding/sample identities on IPv4/IPv6, preservation of BUSY without an SDK join,
missing/duplicate observations and the unchanged strict N3 gate.

Exactly one19-IMU observer run at requested20Hz used the existing explicit
permanent-neighbor fixture and separate closed identity/measurement captures:

| Observation | Result |
| --- | --- |
| Source calls / matching admission / SDK source / receiver publications | 19 / 19 / 19 / 19 |
| BUSY observed | 0 |
| Sender trace records / drops / exhaustion | 39 / 0 / false |
| Receiver trace records / drops / exhaustion | 0 / 0 / false |
| Measurement source / parity packets per endpoint | 19 / 5 |
| Measurement PCAP file/captured/filter per endpoint | 24 / 24 / 24 |
| Publication age upper maximum | 8,701,792 ns |

The39 sender rows are19 admission results plus20 accepted SDK messages including
the pre-sample binding. Source message/header identity candidates match exact
native and PCAP observations. All payload hashes and ordering agree, all six
conservation balances are zero and no stage loss is recorded. Both declared
capture populations complete with zero native reserve/copy or PCAP kernel losses,
standalone final footer equality and stable bounded drain. Interface features
match before/after. Source callbacks remain in the same qualified session with
actual sensor QoS. Age upper bounds are callback-ingress-based under configured
conservative clock assumptions, not physical sensor age or realtime PCAP latency.

No BUSY occurred in this run. Rejected-admission correlation is tested with
controlled parser/storage fixtures, not claimed as a newly reproduced live BUSY
case. The previous missing source ID7 and try-lock BUSY remain failed evidence;
no contending holder/duration or fix is established. No producer or SDK-accepted
sample is replayed, and the original strict19-source `outcomes()` gate is unchanged.

Six selected runtime hashes are stable across measurement; the transport/ROS
binaries were intentionally rebuilt before this run, so they are not asserted
identical to the previous cohort. The pinned SRT dependency archive is unchanged.
Sources match the frozen commit. Build/test logs, prospective plan, original
results, trace/capture logs, hashes, counters and provenance are retained. Raw
captures/journals/resource traces remain in `.local/m3-sample-handoff/`; credentials,
full environment and container inspect outputs are excluded.

Next: separately plan ROS one/two-source loss cases using actual SDK identities,
map each missing/repaired message back to the admitted callback, and preserve any
independent BUSY losses. Deliberate late repair ordering, full200/50Hz multiroute/
seed qualification, N4 command phases and other M3 gates remain open. Intrinsic/M4
is untouched.
