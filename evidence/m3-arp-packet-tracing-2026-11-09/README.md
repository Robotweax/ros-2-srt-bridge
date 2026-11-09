# Packet-level ARP queue/drop diagnosis — 2026-11-09

Passive tracing now distinguishes actual source qdisc drops from replies delayed
past a counter window. No tuning, dependency change or product runtime rebuild.
PR2 stays draft; M3 is incomplete and Intrinsic/M4 untouched.

In the new N5/2903 run,18 positive robot reply-counter windows have no source tap
reply inside their wider read envelope. Per-packet lifecycle joins distinguish:

| Branch in those18 windows | Windows | Evidence |
|---|---:|---|
| Qdisc drop |13|Distinct scoped skb lifecycle ends with kernel `SKB_DROP_REASON_QDISC_DROP`|
| Queued, then driver start after window |5|Same ID has ordered root enqueue/dequeue;93.832–113.944ms residence|

The five delayed IDs are4,13,18,21,22. Driver start is1.082–96.874ms after the
respective outer counter-window end. The source AF_PACKET hook is immediately
before driver start; its absence inside that window was **not packet loss**.
These are this cohort's identities, not retrospective identities for the prior
eight ambiguous windows. No individual ARP request/reply nonce or peer-tap ID is
invented; peer counts remain aggregate corroboration.

## Calibration and original failures retained

[Original plan](PLAN.md), [unsigned filter correction plan](PLAN-V2.md),
[loaded plan](PLAN-LOADED.md). Plans precede their respective live runs.

- Kernel7.0.14-linuxkit exposes BTF and all seven probed raw tracepoints despite
  absent tracefs event mounts. BPF/PERFMON suffice; no privileged container,
  tracefs mount, global trace configuration, sysctl or kernel setting changes.
- First no-traffic verifier preparation fails on structurally unreachable
  generated instructions. Corrected no-traffic attachment closes cleanly.
- V1 frozen88ba3f1 calibration N0 remains **FAILED**: native/PCAP see30 replies,
  tracer0. N5 remains **NOT_EXECUTED**, no retry. JMP64 sign-extended high-bit
  32-bit namespace/header immediates while LDXW zero-extended their values.
- V2 uses JMP32 only for those unsigned field comparisons, preserving pointer
  tests at64bits. A real kernel BPF test proves the former comparison rejects
  and the corrected one accepts the same high-bit value. Readiness version2
  identifies the correction. Failed evidence and original source/hashes remain.
- V2 frozen38f0af4 runs once each in fresh owned namespaces. N0:30/30 kernel
  replies reach driver/native/peer. N5, existing512kbit/16-packet profile with a
  bounded synthetic15000-packet UDP stimulus:20 exact qdisc drops,10 driver
  starts/replies at both taps. All60 IDs terminate; zero observer loss/pending.
  Surviving calibration queue intervals are microseconds, not a long-delay test.

Synthetic requests use exact owned MAC/IPs and provoke real kernel replies;
there is no userspace reply generator, neighbor flush, ping, permanent entry or
product setting change. Synthetic load exists only in calibration. Its outcome
cannot substitute for a ROS/SRT qualification run.

## Loaded ROS/SRT run, once per slot

Frozen live source5544747 with eight runtime/two existing observer hashes equal
the prior loaded cohort, plus the exact V2-calibrated tracer binary. Both roles
have passive exact42-byte Ethernet/IPv4 ARP reply/netns/ifindex scope. Existing
PIPE/PASS counters, CONTROL/root/neighbor/provider diagnostics, UDP-PCAP and
native-v2 stay enabled. Normal128Kbit competitor,200/50Hz targets,2s offered
commands,5s command budget,5000ms idle and8s result drain remain unchanged.
No synthetic requests/flood, injected drop or tuning in this loaded cohort.

| Slot | Command outcomes | Skips | Durable progress gate |
|---|---|---:|---|
| N0/2903/15s |8 successes /8 attempts|0|PASS|
| N5/2903/300s |121 successes,1 REJECTED/context_lost /122 attempts|28|**FAIL**|

Original harness exit0/capture gates pass in both; the outer command gate fails
for N5 and exits1. Command34 has one SDK handoff and matching closed sender/
receiver REJECTED/context_lost state6/reason1, zero unresolved/UNKNOWN records,
121 effects. Receiver dispatch was already recorded, so this is neither expiry
nor journal-only nonexecution proof. There are zero verified expiries and no
active transport context/link-loss events. Do not infer its cause from ARP
counts. Earlier UNKNOWN intents98/12 remain unresolved; no replay or retry.

| Scoped reply source, full tracer span | Lifetimes | Driver start | Qdisc drop | Pending |
|---|---:|---:|---:|---:|
| N0 operator |1|1|0|0|
| N0 robot |1|1|0|0|
| N5 operator |12|12|0|0|
| N5 robot |26|10|16|0|

All source/peer native reply populations equal driver-start counts. Loaded N5
records48 operator and72 robot lifecycle events, zero ring/map/read failures,
collisions, unknown frees, consumed-before-driver outcomes or bulk ambiguity.
Every ID has valid boundaries. All16 robot drops have stage sequence queue→
kfree with actual QDISC_DROP reason; no successful enqueue trace is asserted for
those packets. This does not locate the exact inner netem/TBF drop instruction.

All10 surviving robot replies have enqueue/dequeue with the same root handle;
seven reside69.406–113.944ms, three under1us. Operator max residence8.791us.
Every lifecycle is retained, including those outside publication. Within source
publication there are32 positive adjacent counter steps (operator11/robot21).
All11 operator windows have a source reply. Robot3 windows have a source reply;
the other18 split into13 explicit drops and5 late driver starts as above. The
full-span16 drops and the13 drops in selected windows are different scopes.

All four prospective >=1s CONTROL gaps are retained (1.000279s operator,
1.065958/1.268879/1.052333s robot). None contains creation of a scoped qdisc-dropped
ARP reply; only one contains an operator reply that reaches driver. Thus the
new evidence distinguishes reply loss/delay under load, but does not explain
every CONTROL gap or uniquely establish the cause of historical session failures.

N5 sensor production75031/observed22522, SDK-accept-to-receiver gap47016,
receiver rejection1446, six conservation residuals0; source~200/50Hz. Telemetry
remains unqualified. No superiority or mitigation claim follows added observers.

## Observer contract and use

`tools/arp_packet_trace/main.cpp` loads hand-assembled passive raw-tracepoint
programs; no clang installation or provider rebuild. Running BTF validates exact
field sizes/offsets and all argument types. Its SHA256 is
`6a697382f00e813d017829810e06350e3e4dd811542fd933f1d763cd84527faf`.
BTF also supplies the actual drop-reason enum. Reference Linux tracepoint
interfaces: [net](https://github.com/torvalds/linux/blob/v7.0/include/trace/events/net.h),
[qdisc](https://github.com/torvalds/linux/blob/v7.0/include/trace/events/qdisc.h),
[skb](https://github.com/torvalds/linux/blob/v7.0/include/trace/events/skb.h).
These reference headers are not a claimed source identity for the running kernel;
runtime BTF and calibrated observations are the compatibility evidence.

Six measured hooks: net_dev_queue, qdisc_enqueue, qdisc_dequeue,
net_dev_start_xmit, kfree_skb, consume_skb. Raw skb addresses exist only as private
BPF-map keys; output contains monotonically assigned local IDs. Tracking ends
at driver start so later peer/bridge frees cannot become source TX drops.
Classifier drops before net_dev_queue, untracked clones/copies and physical-wire
delivery are outside scope. Population mismatch, ambiguous stages, other frees,
loss, collision or pending IDs fail the loaded diagnostic rather than fabricate
complete tracing. Missing enqueue cannot establish residence.

Bounds:4096 outstanding IDs,4MiB ring,1million events,600s hard stop. Normal stop
closes all six links, drains the ring, verifies stable counters/populations, then
closes native capture. Existing runner behavior is unchanged unless the new
`--arp-packet-trace` option is explicitly used. It requires the existing loaded
ARP observer and all of its diagnostics, N0/N5 dynamic/no faults, <=480s. It
adds PERFMON only to owned endpoints. Missing hooks/BTF/capabilities fail explicitly.
The separate binary must be built before capture:

```sh
g++ -std=c++20 -O2 -Wall -Wextra -Wpedantic -Werror \
  tools/arp_packet_trace/main.cpp -lbpf \
  -o build/arp-packet-trace/arp_packet_trace
python3 tools/m3_loaded_arp_diagnostics.py --packet-trace --out .local/NEW-UNIQUE-COHORT
```

Use the pinned image and create the build directory first. The second command
starts a fresh cohort, not reanalysis; do not rerun existing evidence to replace
a failed result. `m3_arp_packet_windows.py` performs closed analysis with original
hashes, individual creation/termination membership and explicit carry-in/out.
Its code was added after closure, before joins; the selection was prospective
in PLAN-LOADED.md. Two new boundary tests preserve queued carry-out and terminal-
versus-creation scope.

## Provenance and remaining work

- Host336 before V1,337 before V2,339 before loaded,341 after closed window
  guards. SDK72/ROS41 remain prior validation; only the new tracer was compiled.
- Source verified immediately at each closure, then original changed Git blobs
  checked for post-closure changes. Existing ten binary hashes fixed throughout;
  tracer V1→V2 changes only for the documented bug correction and stays fixed
  through V2 and loaded. Provider commit/archive unchanged.
- [497 original raw hashes](local-artifact-hashes.json),
  [every public selection/omission](public-disposition.json),
  [source verification](source-verification.json), [cleanup](cleanup.json).
  Five owned internal networks/containers and all credentials removed. No tests,
  builds or heavy analysis overlap live. Full PCAP/native/provider/journal/sample
  streams remain local by hash; selected logs explicitly list omitted lines/fields.
- [Full packet joins](analysis/srt-N5-2903-packets.json),
  [all primary windows](analysis/srt-N5-2903-arp.json),
  [all positive counter steps](analysis/srt-N5-2903-steps.json),
  [all cohort statuses including failure](summary.json).

Next investigate command34's worker/start-fence context rejection with existing
journal/clock-grant evidence, and use exact packet lifetimes to evaluate any
separately planned mitigation. No tuning is made or implied here. Full N3/N5,
default loaded DDS discovery, cross-host clock/security/resource/hardware and
comparison gates remain open. PR2 draft, M3 incomplete, Intrinsic/M4 untouched.
