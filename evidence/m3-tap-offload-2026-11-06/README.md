# Tap position, offload metadata and capture integrity — 2026-11-06

This step characterizes the owned Linuxkit/veth fixture and corrects measurement
scope. It adds capture artifact v2 with GSO/VLAN metadata and a read-only feature
probe. SDK/bridge wire, IPC, production C++ and Intrinsic/M4 remain unchanged.
M3 remains in progress; no physical-link or transport advantage is claimed.

## Controlled evidence

`tools/m3_tap_probe.py` creates fresh internal endpoint pairs, sends known synthetic
UDP populations, and compares sender/receiver monotonic observations, immediate
PCAP records, application receipts and tc counters. Each same open observer must
also see a known datagram after restoration. Offload settings are queried, never
changed. No ROS/SRT peers or competing load run in these fixtures.

- Plain UDP: all 16 datagrams appear at both taps and the receiving application.
- Egress 100% netem loss: 16 known UDP datagrams pass a targeted u32/gact egress
  counter before the root queue; none appears at either packet tap or application.
  The aggregate root drop increment exceeds the targeted flow count; that excess
  is retained separately without protocol attribution. The
  restored control succeeds. This places this egress tap after that tested drop.
- Egress 200-ms netem delay: all 16 sender-tap timestamps include the queue delay
  (classification threshold 150 ms, separating an immediate tap from the requested
  delay). Actual per-datagram deltas are saved. This is not a precision delay bound.
- Ingress targeted drop: all 16 are visible at both taps, the ingress drop action
  counts 16, and the application receives none. Restoration succeeds. The receive
  tap precedes this tested ingress action; a tap observation is not delivery.
- UDP_SEGMENT: one 9,642-byte skb observation at each endpoint represents eight
  1,200-byte application datagrams, with `gso_segs=8` and `gso_size=1200`.
  Both noqueue and netem cases retain this representation. Observation accounting
  is valid, while individual-frame interpretation is explicitly unqualified.
- A 512-kbit/s TBF/netem shaping-only case matches all 16 observations/receipts.
  It has no competitor or application peers and is not full N5 acceptance.

The [Linux transmit tap](https://github.com/torvalds/linux/blob/v6.17/net/core/dev.c)
and [socket-filter context access](https://github.com/torvalds/linux/blob/v6.17/net/core/filter.c)
support these mechanisms. Runtime experiments, not those upstream references
alone, establish the recorded fixture observations. Other kernels, devices,
encapsulation or bypass paths require their own qualification.

**Correction:** the older generic `egress is pre-qdisc` label was wrong for this
fixture. Current classic-PCAP scope is neutral about stage/offloads and points
to explicit environment qualification. Historical artifacts remain immutable;
apply this correction when interpreting their byte totals. Counts of written
records/classes are unchanged by this text correction. Egress captures cannot
supply pre-qdisc offered traffic or capture packets dropped by that root queue.

## Metadata and eligibility

The native observer emits a version-2 artifact with 168-byte records, retaining
128-byte prefixes and adding GSO segment count/size and accelerated VLAN metadata.
It records the MTU and retains the same bounded ring/file/counter/coverage gates.
The reader still supports historical 152-byte v1 records; missing offload data
is unknown, never evidence that offloads were absent. New runner invocations
require v2. The native program remains attached only to its own packet socket;
the controlled fixture's temporary tc actions are separate from the observer.

`frame_interpretation` qualifies only absence of indicated segmentation/VLAN/
over-MTU skbs in the measured IPv4 UDP population. It does not qualify physical
frames, checksums, padding, FCS, preamble or delivery. The legacy class key
`ethernet_bytes` contains observed skb lengths; `byte_unit` makes that explicit.
Inline VLAN frames reject the unsupported parser path instead of hiding UDP.
The GSO counterexample remains observation-qualified but interpretation-unqualified.

`tools/netdev_features/main.cpp` reads MTU and the named ethtool available/requested/
active/fixed feature bitmaps without SET operations or extra capabilities. Opt-in
runners save before/after snapshots, require them to agree and check the native
MTU against the snapshot. Active features alone do not establish actual use;
per-observation metadata supplies the segmentation check. Snapshot equality is
not a proof against arbitrary intermediate external reconfiguration.

## PCAP accounting correction

A sparse buffered capture wrote 16 records while the native observer and known
probe population included 17: the final control was still absent at shutdown.
Runners now use explicit immediate PCAP mode, stop the owned UDP competitor first,
allow in-flight traffic to settle, then close observers. File records must match
tcpdump's captured count, with zero reported kernel drops and complete parsing.

Further experiments show filter counters can differ even when every known probe
observation matches the native capture. For example, a GSO case writes two known
observations while reporting three received by the filter. The [libpcap statistics contract](https://www.tcpdump.org/manpages/pcap_stats.3pcap.html)
explicitly allows platform/filter/read differences. The exact cause/unit
of every discrepancy here is not established; filter/file equality is not a universal
proof of capture completeness. The helper retains the filter count and reports
population reconciliation separately from written-file integrity. An unreconciled
population withholds realtime PCAP window totals. It does not invalidate the
native observer's independent invocation/reservation/copy accounting or a fully
matched controlled probe population. No equality rule is silently relaxed to
claim complete physical captures.

This mode change affects observer cost: the earlier on/off study applies to the
v1 observer and buffered PCAP mode, not the new v2/immediate combination. Its CPU
variation and memory observations remain historical; no new overhead estimate
is inferred here.

## Validation and reproduction

See [results](RESULTS.md), native build/source hashes, captured observations and
counter logs. Raw frame prefixes/PCAPs stay local with hashes; synthetic send/
receive records and sanitized observer metadata are retained. Development parser,
classifier and counter-gate iterations remain separate. No new ROS GTest/full M2
execution is claimed.

After the existing pinned M3 setup, normal `--monotonic-capture` builds both
standalone tools. Development `--skip-build` requires their current binaries.

```sh
python3 tools/m3_tap_probe.py run --out .local/tap-offload/new-run
python3 tools/run_m3.py --profile N0 --smoke --monotonic-capture
python3 tools/run_m3_dds.py --commands --profile N5 --dds-profile paced-sensors --smoke --monotonic-capture
```

Choose fresh directories. The fixture uses NET_ADMIN/BPF only in owned containers,
never host interfaces; it removes its namespaces and network even on failures.
Default M3 runs use immediate PCAP mode but add no BPF observer/capability.

Remaining: other device/offload paths, v2/immediate observer cost, controlled
hardware/resource conditions, remaining profile/duration matrix and N3/N4 gates,
plus SRT/DDS pacing/reconciliation/age/crypto alignment before a cost comparison.
