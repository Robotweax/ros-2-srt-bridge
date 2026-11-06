# CONTROL provider diagnostics — 2026-11-06

Optional CONTROL statistics now retain bounded SDK observations before the
separately qualified egress hook. This completes instrumentation, not M3/N5
qualification or diagnosis of the old CONTROL silence. Protocol policy,
timeouts and pinned provider remain unchanged. Default is disabled.

The prospective [plan](diagnostic-plan.json) specifies exactly one 90-second N5
execution after tests and one N0 smoke. Both executions use source commit
`0ace537` (SDK/ROS code from `eedf5d3`); all source hashes match, installed scenario
and header match source, and eight runtime hashes match before/after. The
provider source check matches pin `52be7c86ee1f303cbb0c8718c364217e4dd97a36`.

| Check | Result |
| --- | --- |
| Host Python | 105 passed |
| Full native/SDK CTest | 69 passed |
| Rebuilt ROS packages | All three; 36 reported tests passed |
| Controlled one-way CONTROL silence IPv4/IPv6 | 5005/5003 ms to provider loss; actual idle readback 5000 ms; 788/781 checks |
| N0 15-second smoke | 8 successful commands/effects, 0 unresolved or skipped |
| N5 seed 1701, 90-second diagnostic | 39 successful commands/effects, 6 skipped slots, 0 unresolved |

N0 provider records by operator/first robot/replacement robot: **271/23/226**.
N5: **974/24/959**. All final statuses have zero drops and no budget exhaustion.
N5 command traces retain **135/5/5** records without loss. Unavailable setup
samples are explicit. Connected samples read back 5000 ms. N5 maximum observed
sample-start gap is 113.283167 ms and maximum SDK read span 0.673250 ms, across
all incarnations. These observations are not scheduling/latency bounds.

No active-window CONTROL link loss or close recurred in either execution.
Consequently no incident window exists here for provider-versus-egress cause
attribution. This is instrumentation validation only; the failed historical N5
cohorts and UNKNOWNs are not replaced or reclassified. No extra retry was run.

N5 PCAP records/filter counts agree at 39550 per endpoint, kernel drops zero.
Native records are 39598 operator / 39603 robot with zero reservation/copy
failures. Their capture intervals/populations differ; do not equate totals.
Realtime PCAP measurement windows remain withheld by clock qualification.
N5 source/published/observer populations are **22534/7173/7173**; the large
sensor deficit stays visible. A successful command/diagnostic gate is not a
lossless sensor or performance claim. All accounting balances are zero.

[Findings](findings.json) retain unavailable counts, sampling spans, command
outcomes, active event selection, capture status and sensor conservation.
`smoke/run.json` and `n5/run.json` are unmodified original manifests, with the
original result documents, diagnostic logs, selected final states and qdisc
readbacks. PCAP payloads, native prefixes, journals, clocks and resources stay
local; SHA-256 manifests retain their identity. No credentials, inspect or
environment dumps are included.

The sampler uses `srt_bstats(..., 0)` on CONTROL only, with actual read brackets,
owner/generation/socket identity and a separate 128-record SPSC queue capped at
75000 lifetime records. Overflow/exhaustion fails runner completeness. SDK
mutex/bookkeeping work can perturb scheduling. DATA/ACK/NAK counters omit
keepalive, handshake and ACKACK; provider send accounting does not prove peer
delivery. Counter deltas preserve both read brackets, never cross unavailable
samples or socket identity changes, and flag potential 32-bit saturation.
Gauges are not counters; zero RTT need not mean a latency estimate.

Next: use these frozen observations in a prospectively bounded experiment that
separates provider scheduling/socket sending from post-qdisc CONTROL traffic.
Historical initiating cause, full N5/M3, N3/N4, default DDS N5, age/clock/security
and resource parity remain open. PR #2 stays draft. Intrinsic/M4 is untouched.
