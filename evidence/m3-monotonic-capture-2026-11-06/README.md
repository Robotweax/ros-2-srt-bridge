# Experimental kernel-monotonic packet accounting — 2026-11-06

Both M3 runners now support explicit `--monotonic-capture`. A separate passive
AF_PACKET socket filter records kernel monotonic timestamps, skb frame lengths,
interface/direction and 128-byte packet prefixes. It uses the existing workload
source-enabled and fenced-observation intervals, without converting realtime.
This adds an observation path; realtime PCAP accounting and its independent
clock/integrity gates are preserved. M3 and controlled SRT/DDS comparison remain
incomplete. Production C++/SDK/SRT/wire/IPC and Intrinsic/M4 are unchanged.

## Implementation and qualification

- Standalone C++ tool builds with the pinned image's g++ and libbpf. It emits
  verifier-checked BPF instructions directly, without clang, BTF dependencies,
  package installation or image changes. The helper is
  [documented as kernel monotonic time](https://man7.org/linux/man-pages/man7/bpf-helpers.7.html).
  No clock correction or realtime drift-model relaxation is involved.
- A BPF socket filter is attached only to its own AF_PACKET socket on the owned
  endpoint's eth0. Return 0 suppresses that observer socket's receive queue;
  application traffic continues normally. No tc/XDP hook, route/qdisc change,
  host namespace, privileged container or published port is added. CAP_BPF is
  added only when opted in; existing endpoint NET_RAW/NET_ADMIN remain. Default
  runs retain their original capabilities and no monotonic observer.
- Kernel-monotonic and workload epochs require zero time-namespace offsets.
  The native tool rejects nonzero/missing offsets; existing common boot/time-
  namespace proofs remain required by both runners. The ready marker is emitted
  only after attachment. Both phase boundaries must be covered by ready/stop.
- The [BPF ring buffer](https://docs.kernel.org/bpf/ringbuf.html) is bounded at
  16 MiB by default. Output is capped below 128 MiB. Atomic seen/submitted/
  reservation-failure/copy-failure counters cover every observer invocation.
  Socket close detaches the hook; remaining records drain before stable counters
  and file-record count are checked. Any exhaustion, copy/poll/write error,
  missing footer, counter mismatch or incomplete coverage rejects the capture.
  The socket close/drain design follows the
  [AF_PACKET release path](https://github.com/torvalds/linux/blob/v6.17/net/packet/af_packet.c).
- Binary artifact format v1 has a 16-byte little-endian header and fixed 152-byte
  records. Prefix tails are initialized, lengths/interface/type fields checked,
  and truncated/unknown formats rejected. This is a lab artifact format, not a
  bridge wire/IPC change. Prefixes cover maximum IPv4 header + UDP + SRT header.
  Payload byte totals come from validated UDP lengths, not invented payload
  copies. SRT DATA/FEC/control and RTPS classification retains the pinned parser.
- IPv4 UDP fragments are DDS-only and keep unknown UDP payload totals. Non-UDP
  frames are counted as ignored. Known IPv6 TCP/ICMP/no-next terminal protocols
  can be ignored after bounded extension parsing; IPv6 UDP, fragments, unknown
  or out-of-prefix chains reject qualification. IPv4 UDP remains the supported
  measured population; unknown traffic is not silently discarded.
- `monotonic_captures` is separate from realtime `window_captures`. Every phase
  uses [start,end) in kernel monotonic time; records need not arrive sorted across
  CPUs. The timestamp denotes execution of the kernel observer, not first-bit
  arrival, hardware transmission, physical delivery or a sensor population.
  Frame lengths are skb observations, not a qualified physical-link/offload
  accounting. Endpoint/direction totals overlap and must not be summed as unique
  traffic. RTPS includes controls/discovery; N5 totals include the competitor.
- Capture processes remain outside endpoint CPU. Kernel observer work may be
  charged to endpoint tasks; this observer changes host load. This variant is
  explicit in manifests and must be controlled in any performance comparison.

## Validation

58 host Python tests pass. New tests compare prefix-derived byte/class totals
with whole PCAP parsing and cover half-open/unsorted timestamps, counter/clock/
coverage/interface failures, corrupt binaries/lengths/direction, IPv4 fragments,
and IPv6 UDP/extension rejection versus known non-UDP traffic.

The isolated loopback check sends 40 known datagrams across five sizes. All 80
outgoing/incoming observations have correct lengths and kernel timestamps within
the userspace monotonic send/receive brackets; no recorder loss occurs. Synthetic
observation metadata and brackets are retained for audit. This validates the
clock relation in this environment, not physical wire timing.

A forced 4-KiB ring overflow with paused userspace records 2,000 invocations,
25 submissions and 1,975 failed reservations. Native exit 2 and analyzer rejection
are expected and verified. Running without CAP_BPF fails before a ready marker.
The probe containers drop all capabilities except BPF/NET_RAW as applicable.

Final current-source runs: SRT N0 and DDS N0 smokes (15 s), paced DDS N5 (30 s),
and default sensor smoke (15 s) pass. Commands confirm 8/8, 8/8 and 15/15.
Both phases at both opted-in endpoints qualify monotonic capture and CPU. Every
opted-in recorder has zero reservation/copy failures. The default run confirms
absence of CAP_BPF and observer results. See [counts and limits](RESULTS.md).
Four source inventories match all 153 files, installed scripts match, and 56
production source files plus command/simulator binaries are unchanged. No new
ROS GTest/full M2 execution is claimed. Native build/provenance and per-run
capability/clock proofs are retained.

Initial IPv6 parser failures and successful longer development runs before the
CPU-scope wording correction are retained separately, excluded from final
current-source results. Raw PCAPs, packet prefixes and journals stay local with
hashes/sizes. Whole-run PCAP and monotonic totals are recorded for corroboration;
their lifetime edges differ, so equality is not a completeness or loss proof.

## Reproduction

Normal M3 build paths compile the observer when opted in:

```sh
python3 tools/run_m3.py --profile N0 --smoke --monotonic-capture
python3 tools/run_m3_dds.py --commands --profile N5 --dds-profile paced-sensors --smoke --monotonic-capture
```

For the isolated check after building the native binary, use a fresh output dir:

```sh
docker run --rm --pull=never --platform linux/amd64 --network none \
  --cap-drop ALL --cap-add BPF --cap-add NET_RAW \
  -v "$PWD:/workspace" -w /workspace ros2-srt-m3:20261105 \
  python3 tools/check_m3_monotonic_capture.py \
  --native build/m3-monotonic-capture/monotonic_capture --out .local/mono-check
```

Native CLI: `monotonic_capture INTERFACE OUTPUT READY_JSON [RING_BYTES]`.
Ring size is a power of two, 4 KiB through 16 MiB; runner defaults remain fixed.
Outputs must not exist. Build and standalone checks are isolated from measured
peers and do not warm their discovery.

Next: longer durations/seeds, observer overhead and observation-stage/offload
qualification, then controlled comparisons with aligned pacing/reconciliation,
age and crypto semantics. This step is not complete M3 acceptance or a transport
performance advantage.
