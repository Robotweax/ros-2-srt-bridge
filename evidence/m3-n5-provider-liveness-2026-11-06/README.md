# N5 provider/egress liveness diagnostic — 2026-11-06 UTC

One prospective 300-second N5 execution (seed 1701, no injected fault) completed
with **126 confirmed successes/effects, 24 skipped slots and zero unresolved
intents**. No active CONTROL loss/close occurred. This does not reproduce or fix
the historical N5 reset, replace failed cohorts or complete N5/M3 acceptance.

The new observation is a **4.237-second CONTROL egress gap while selected
provider send counters continued increasing**. A post-hoc ARP check finds five
operator ARP requests and an ARP reply about 20 microseconds before CONTROL
resumes. This suggests neighbor-resolution involvement in this run; neighbor
state and kernel drop stages were not sampled. It is a hypothesis for the next
controlled diagnostic, not a demonstrated historical initiating cause.

## Prospective analysis

The [plan](diagnostic-plan.json) and analyzer were frozen in commit `e29412c`.
120 host tests and syntax checks passed; the analyzer reproduced the retained
known-filter receiver-loss signature before execution. Source hashes and eight
runtime hashes match before/after. SDK/ROS/provider binaries, timeouts and N5
settings are unchanged; no new full SDK/ROS/M2 test execution is claimed.

All adjacent nonzero-destination CONTROL egress gaps >=1 second whose packet
endpoints lie in the active source window are retained. No gap was selected
because its counters increased. Mapping requires a recent nonzero common
session plus reciprocal tuple/socket observations and the pinned provider
archive; unavailable or ambiguous cases are withheld. Counter deltas use only
adjacent available same-identity reads with both read brackets inside the gap.
Native capture counts/hashes/coverage and common VM clock are checked. The source
window is censored at its boundaries; routing IDs are not authenticated identity.

| Sender | Gap seconds | DATA-sent delta | Retransmissions included in DATA | ACK-sent | NAK-sent |
| --- | ---: | ---: | ---: | ---: | ---: |
| operator | 1.000311417 | 0 | 0 | 0 | 0 |
| operator | 4.237048752 | 364 | 350 | 68 | 1 |
| robot | 1.099705168 | 15 | 14 | 0 | 0 |
| robot | 1.054902209 | 35 | 28 | 15 | 0 |

Every interval has zero source outgoing CONTROL observations across **all**
CONTROL flows, not just the selected old routing ID. Each peer has one old-flow
observation 19–24 microseconds after the leading source edge; these edge overlaps
are retained, not mistaken for an entirely empty peer window or authenticated
packet pairing. The largest gap has 39 internal provider read pairs. Selected
counters exclude keepalive/handshake/ACKACK; flat counters do not prove UDP
absence. Retransmissions must not be added to DATA-sent a second time.

These observations narrow this run's three positive-counter gaps to a difference
between provider send accounting and the egress tap. They do not uniquely choose
socket handling, neighbor resolution, qdisc or another pre-tap mechanism. Whole-
run root qdisc drop deltas (operator 184, robot 618355) are not per-flow/event
loss counts; child counters overlap and are not summed.

## Exploratory ARP follow-up

`tools/m3_arp_gap_observations.py` was added **after measurement** to decode ARP
in all four already-selected gaps. Header shape and representation are checked;
native hashes match the primary analysis. Non-outgoing duplicate requests remain
in the artifact and are not counted as extra peer probes/replies. Four additional
parser tests bring the host total to **124 passing tests**. This analysis was not
a preregistered outcome or a reason to alter a verdict/threshold.

In the 4.237-s operator gap, five outgoing ARP requests target the robot. The
robot's outgoing ARP reply is observed 30.542 microseconds before source CONTROL
resumption; the operator sees that reply 19.792 microseconds before resumption.
SENSOR/other traffic is also retained in the interface crosscheck. A second
robot gap has an ARP reply 76.375 microseconds before resumption. Neighbor-table
transitions, queued/dropped datagrams and exact causal ordering inside the kernel
remain unobserved. This association motivates neighbor-state sampling and a
prospectively planned fixture contrast; it does not prove a provider defect or
establish that the historical incident had the same cause.

## Outcomes and completeness

Closed immutable journals have 126 sender and 126 receiver records, with matching
successful command/context/result fields. Every command has one observed SDK
handoff; each receiver dispatch timestamp precedes its conservative receiver
start deadline. Receiver and sender deadlines are not assumed equal. Terminal
observation latency includes asynchronous result polling and does not measure
handler start or physical delivery. Old UNKNOWNs remain unchanged.

Provider logs **2993/24/3054** and command traces **397/5/5** are complete, with
zero drops/exhaustion. Maximum observed provider read span is 0.623041 ms and
sample-start gap 113.664291 ms; these are observations, not bounds.

PCAP records/filter counts agree at **121477 per endpoint**, kernel drops zero.
Native counts **121569 operator / 121567 robot** have zero reservation/copy loss;
intervals/populations differ. Realtime PCAP windows remain withheld by clock
qualification. Competitor whole-run offered load is about 128023 bits/s with
1235 alive checks; no per-window delivered-load inference is made.

Source/published/observer populations are **75024/23032/23030**, with all
conservation balances zero. The large sensor deficit remains part of the result;
command success is not lossless sensor delivery or a performance advantage.

[Findings](findings.json), [primary analysis](provider-flow-analysis.json),
[all-flow/edge crosscheck](gap-crosscheck.json), [ARP observations](arp-gap-observations.json),
[largest-gap interface observations](largest-gap-interface-crosscheck.json) and
[journal audit](journal-audit.json) preserve their scopes. `run/run.json`, results
and selected logs are unmodified original copies. Raw packet payloads/prefixes,
journals, clocks and resources stay local with SHA-256 identities. No secrets or
inspect/environment dumps are included.

Next: add bounded read-only neighbor-state observations and prospectively test
neighbor-resolution involvement in the owned N5 fixture. Any altered neighbor
configuration is a separate diagnostic candidate, not a replacement baseline.
Historical cause/UNKNOWNs, full N5/M3, N3/N4/default DDS N5, age/clock/security and
resource parity remain open. PR #2 stays draft; Intrinsic/M4 is untouched.
