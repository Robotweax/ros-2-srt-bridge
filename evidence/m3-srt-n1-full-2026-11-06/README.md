# SRT N1 full-duration seeded execution — 2026-11-06

This frozen cohort requests 600-second SRT workloads for base seeds 1701, 2903
and 4211, sequentially in fresh owned endpoint pairs. It extends the earlier
short SRT N1 probes; the preceding full SRT/DDS N2 cohorts remain separate evidence.
Netem requests 20±5 ms normal-distribution delay and 1% random loss in each
direction, a 256-packet queue and direction seeds base/base+1. Arguments and
kernel readbacks are archived. No host qdisc, published ports or privileged
container is introduced. The existing SRT crypto/profile configuration remains.

The existing application/SDK/worker/capture binaries and demo Python bytes are
reused, hashed and frozen alongside source inventories. Only capture tooling,
metadata and its comparison guard change; compiled runtime sources, command
policy and installed binaries are unchanged. There is no rebuild. Native capture
v2 is enabled throughout, with immediate
full-snapshot PCAP and the existing 32,768-KiB buffer request. The new rotating-file
retention setting is sixteen 16-MB files (256,000,000 nominal bytes per endpoint).
There is no observer
on/off resource contrast and no controlled hardware-performance claim.


## Retention preflight and bounded change

The preceding SRT N2 endpoints wrote 125,447,816..125,572,581 bytes against the
old nominal 128,000,000-byte rotating-file capacity. N1 has lower configured loss,
so the remaining headroom is insufficient as a planning margin. Before freezing
this cohort, normal SRT and DDS runners switch from eight to sixteen 16-MB files.
The manifest now records file size/count and nominal retention bytes; study
comparisons reject missing/mixed retention configurations. Kernel buffer,
immediate dispatch, full snapshots, offloads and integrity gates are unchanged.
This is bounded file retention, not a guarantee for arbitrary traffic/duration;
tcpdump thresholds use decimal millions and can exceed a threshold by one record.
No hidden retry or failed N1 case motivated the change; it is a recorded preflight.
Historical results and their smaller/unspecified rotation metadata are unchanged.

A separate controlled UDP probe uses 1-MB thresholds to cross the capacity within
a bounded volume. Two files retain 1,206 of 2,001 known datagrams per endpoint;
tcpdump still reports 2,001 captured and zero kernel drops. The strict existing
captured/file gate rejects this overwritten artifact. Four files retain all 2,001
with exact native identity/length equality and zero drops; application receipts
are complete in both cases. A final recovery control is present in both. This
isolates file overwrite from kernel recorder loss. It is not a full-volume proof
that 256 MB is sufficient for every run. Raw captures/prefixes remain local.

## Interpretation

IMU/joints retain 200/50-Hz production and commands request absolute 200-Hz rate
changes every two seconds, with one pending intent. Busy/uncertain work skips
cadence slots rather than bursting or replaying commands. UNKNOWN pauses new
intents. Success, expiry/rejection, UNKNOWN, nonadmission and unresolved results
remain separate. An elapsed source window does not guarantee 300 executions.
Existing deadline/lease, journal durability, atomic handler-start and no-replay
rules are unchanged; no tuning is applied to obtain favorable outcomes.

The SRT source-fenced/drained checkpoint accounting preserves six conservation
balances and every local loss/replacement/rejection population. The SRT
accept-to-receiver gap is not automatically WAN loss or a measured FEC benefit.
Age upper distributions refer to the existing bridge-ingress origin, not sensor
sampling-to-delivery age. They are not equivalent to the DDS Header timestamp
age estimates. Publication-age gates, clock-qualified admission and unknown-age
rejection remain unchanged. Diagnostic previous-state-hold durations include
startup/tails/gaps and are not exact measured-window availability bounds.

Zero PCAP kernel drops and captured/file integrity remain strict. Filter-received
population reconciliation is separate; unreconciled populations withhold realtime
packet windows. Clock qualification is also required for those windows. Native
kernel-monotonic coverage/loss and GSO/VLAN/MTU interpretation remain independent.
Socket-tap observations do not establish physical frames, delivery or checksum/
FCS/wire overhead. No cross-transport advantage is inferred from separate cohorts.

Closed journals are audited read-only for integrity, immutable command agreement
and terminal agreement where authoritative. Missing/UNKNOWN/divergent records are
retained, never recast as nonexecution. The DDS-specific timestamp decomposition
is not applied to SRT's clock-mapped journal contexts. Generation chains are
checked against device state only where outcomes permit that conclusion.

## Reproduction

After the existing M3 build/setup, invoke fresh runs separately:

```sh
python3 tools/run_m3.py --profile N1 --seed 1701 --seconds 600 \
  --skip-build --monotonic-capture
```

Repeat with seeds 2903 and 4211. The archived orchestration script freezes the
whole plan before starting and checks source/installed hashes around each child.
It stops on failure and retains the failed case, without retries or replacement.
Raw PCAPs, native prefixes, journals, clocks and sampler files remain local with
hashes. Only selected inspect capability/namespace fields are published.

All three 600-second cases passed: 900 confirmed successes/effects, no expiry,
UNKNOWN, unresolved, nonadmission or skipped slots. Six journals agree; three
source-fenced summaries and twelve cgroup windows replay exactly. The maximum
measured publication-age upper bucket is 119 ms (bridge-ingress origin), within
the unchanged 250-ms gate. PCAP kernel drops/native recorder losses are zero;
realtime packet windows remain withheld.
See [results](RESULTS.md) and study.json for complete populations and limits.
Neither requested duration nor a passing execution verdict closes all M3 gates. Full DDS N1,
remaining age/security/semantic alignment, long v2 N5, deterministic N3, N4 phase
barriers, other devices/offloads and controlled resources remain separate work.
All 83 host tests pass, including rejection of mixed retention configurations.
No new ROS GTest/full M2 execution is claimed. Intrinsic/M4 is unchanged; PR #2 remains draft.
