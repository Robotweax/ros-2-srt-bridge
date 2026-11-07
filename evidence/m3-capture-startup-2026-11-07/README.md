# Filter-transition accounting and filter-before-bind recorder

The controlled filter-transition class is reproduced, the new opt-in recorder
passes its finite qualification, and one separately planned ROS two-loss case
passes. Original tcpdump failures remain failed and unchanged. Their exact cause
is not established by this class reproduction. Full N3/M3 remain open; PR #2 stays
draft. Default tcpdump captures and old acceptance gates are unchanged.

## Controlled probes

Code/plan `1b1610b`, 184 host tests and syntax checks were frozen before exactly
three fresh owned fixtures, once each, with stop on failure. Each sends two tagged
negative packets to UDP39782 and sixteen positive packets to UDP39781. A real
receiver binds both ports, avoiding ICMP side traffic. Native observers at both
endpoints and the receiver verify all18 identities.

| Fixture | Initial filter and controlled transition | PCAP/callbacks | Cumulative receive count | Kernel drops | Capture population accepted |
| --- | --- | --- | --- | --- | --- |
| carry | Broad filter accepts two negatives, then narrows to positive port | 16 | 18 | 0 | **No: expected negative class** |
| early | Final filter before either finite stream | 16 | 16 | 0 | Yes |
| prebind | Final classic BPF attached before enabling packet reception | 16 | 16 | 0 | Yes |

The carry fixture uses the installed libpcap1.10.4 API with immediate mode. It
starts with zero stats, queues two negatives without dispatch, observes receive
count2, changes filter and still observes2. After sixteen positives, the file and
callbacks contain exactly16 positive IDs but cumulative receives are18. No negative
ID appears in the file. This known lifecycle produces a two-count excess without
kernel buffer drops or missing known positive records. It passes its predeclared
class experiment while failing capture-population equality; it is not an accepted
capture or a subtraction/calibration rule for historical data.

The [pinned upstream libpcap source](https://github.com/the-tcpdump-group/libpcap/blob/libpcap-1.10.4/pcap-linux.c)
explains cumulative kernel statistics and temporary user-space filtering of ring
entries accepted under an earlier filter. Installed behavior is tested directly;
the upstream source is not asserted byte-identical to Ubuntu patches. The library
version string mentions TPACKET_V3 support; it does not identify the active ring
mode of these immediate-mode probes. No exact tcpdump startup schedule or historical
packet identity is inferred from this deliberately controlled transition.

## Opt-in recorder

`tools/m3_packet_capture.py` compiles the final Ethernet filter on a dead libpcap
handle (no capture activation), creates an AF_PACKET/SOCK_RAW socket with protocol0,
attaches the final classic BPF, requires disabled-socket accepted count0, and only
then binds eth0/ETH_P_ALL (protocol3). Recorded VM-monotonic brackets verify this
order. There is no receiving broad-filter period or prefilter-count subtraction.
It uses the unchanged installed library only as a compiler, not a live pcap handle.

The recorder retains kernel SO_TIMESTAMPNS values in standard microsecond PCAP,
not userspace receive timestamps. They remain realtime timestamps with no monotonic
age/window qualification implied. The independent native observer provides the
qualified header observations. This recorder is restricted to the owned Linux64
Ethernet fixture; broad physical-wire/offload/VLAN applicability is not claimed.

Files are exclusive/new, bounded by128MiB and75000 records, with truncation,
ancillary timestamp, budget and kernel-drop failures explicit. Requested socket
receive buffer is32MiB; observed actual buffer is8MiB. No general no-loss or
performance guarantee follows. On cooperative stop it requires two unchanged
records==cumulative kernel snapshots within five seconds, checks again before
close, flushes the file and records its byte length/hash. The host compares the
parsed record count, hash and length with final status, plus independent exact
native/PCAP identities. Quiet snapshot equality is not proof of future silence.

The final recorder status has its own truthful backend/counter names. The wrapper
still uses the original standalone tcpdump footer parser for tcpdump captures.
Tests retain8-captured/10-filtered as failed, reject status/lifecycle mistakes,
file mutation, incomplete drains, truncation, drops and budget exhaustion. No raw
status or population repair is applied to old captures.

## Finite ROS two-loss case

Integration/plan `6ba6562` was frozen with186 host tests after the probes passed.
Exactly one new `--trace-losses --trace-loss-count 2 --capture-backend packet-socket`
fixture ran. The earlier failed tcpdump case is neither retried with the same
backend nor reclassified. This is an explicitly changed recorder candidate with
no resource/performance-equivalence claim. No SDK/bridge/ROS runtime source or
binary changed this turn; six artifact hashes match the prior SDK70/ROS36 validated
trace runtime before/after. No new full SDK/ROS/M2 run is claimed.

| Observation | Result |
| --- | --- |
| Source calls / admitted / SDK source handoffs | 19 / 19 / 19 |
| Independent BUSY admissions | 0 |
| Selected SDK messages / source IDs | 7,8 / 5,6 |
| Classifier drops | Exactly one for each selected identity |
| Typed published / observed payloads | 17 / 17, excluding only IDs5,6 at finite cutoff |
| Measurement source / parity records per endpoint | 17 / 5 |
| Measurement PCAP file / dispatched / kernel accepted | 22 / 22 / 22 |
| Identity PCAP file / dispatched / kernel accepted | 8 / 8 / 8 |
| Sender / receiver trace records | 39 / 0, zero drops/exhaustion |
| Publication age upper maximum | 8,993,897ns |

Actual SDK identities map the selected source samples, without assuming every ROS
publication consumes a source index. Both selected source packets are absent from
both measurement populations; every completed-row parity survives, including
last-source-sequence parity. All other complete typed payload hashes/order agree.
All six conservation balances are zero. The only nonzero loss term is exactly2
between SDK acceptance and receiver decode. No accepted sample is replayed, and
no generic irrecoverable-loss or FEC-supply counter is inferred for `arq:never`.
Missing IDs are observations at the finite cutoff, not infinite nonarrival claims.

Same-session clock/QoS checks and publication age histogram gates pass. These ages
start at bridge callback ingress under configured clock assumptions, not physical
sensor age or realtime-PCAP latency. Both capture phases have initial kernel0,
attach-before-bind, stable/equal drains, intact file hashes, zero kernel/native
losses and exact native/PCAP identities. Native capture is started first and kept
attached until PCAP processes close; timestamp markers and controller ordering
are retained. The phases remain separate, with no continuous cross-phase claim.
Interface features are unchanged.

Original probe and ROS outputs, prospective plans, statuses, bytecode/lifecycle
readbacks, trace/capture logs, typed hashes/metrics, selected inventories and raw
hashes are retained. Raw payload captures, journals and detailed resources stay
under `.local/m3-capture-startup/`. Credentials are removed; full container inspect
and environment dumps are excluded. Upstream source download hash and separate
probe/integration source provenance are recorded. Old failure artifacts are not
modified or reconstructed; the historical counter/root-cause question remains open.

Next: deliberate late-repair ordering/rejection tests, followed by full200/50Hz
multiroute/seed N3 qualification. N4 command phases and all remaining M3 gates stay
open. Intrinsic/M4 is untouched.
