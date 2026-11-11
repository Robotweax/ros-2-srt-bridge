# SRT N5 full-duration seeded execution — 2026-11-06

**Outcome: failed qualification.** Seed 1701 passed; seed 2903 failed PCAP
kernel-drop gates (2672/2637) and retained one unresolved driver intent / sender
journal UNKNOWN. Seed 4211 was not executed. See [results](RESULTS.md), the frozen
plan and independent native reanalysis. No gate relaxation or replacement run.

This frozen cohort requests 300-second SRT workloads for base seeds 1701, 2903
and 4211, sequentially in fresh owned endpoint pairs. It extends the earlier
short SRT N5 probes; the preceding explicit paced-DDS N5 cohort remains separate evidence.
N5 requests shared 512-kbit/s root TBF per direction, 4,096-byte burst,
32,768-byte limit and a 16-packet child netem queue. A live robot-to-operator UDP
competitor targets 128,000 bits/s with 1,024-byte blocks. No stochastic loss or
jitter is configured; seeds label repetitions, not random impairment samples.
TC arguments and readbacks are retained. The pinned JSON reports normalized
TBF latency rather than an explicit byte-limit field; the limit request is
preserved in the successful command arguments.
No host qdisc, published ports or privileged
container is introduced. The existing SRT crypto/profile configuration remains.

The existing application/SDK/worker/capture binaries and demo Python bytes are
reused, hashed and frozen alongside source inventories. The SRT Python runner adds competitor-process liveness and whole-run offered-load
gates already present in DDS. The separate negative test stops its competitor
after measurement starts and expects failure. This is not a completed N5 case or
replacement run; its deliberately interrupted capture windows remain unqualified.
Compiled bridge/SDK/wire/IPC and command/publication policy remain unchanged.
There is no rebuild. Native capture v2 is enabled throughout, with immediate
full-snapshot PCAP and the existing 32,768-KiB buffer request. Captures retain sixteen rotating 16-MB files (256,000,000 nominal bytes).
There is no observer
on/off resource contrast and no controlled hardware-performance claim.

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
python3 tools/run_m3.py --profile N5 --seed 1701 --seconds 300 \
  --skip-build --monotonic-capture
```

Repeat with seeds 2903 and 4211. The archived orchestration script freezes the
whole plan before starting and checks source/installed hashes around each child.
It stops on failure and retains the failed case, without retries or replacement.
Raw PCAPs, native prefixes, journals, clocks and sampler files remain local with
hashes. Only selected inspect capability/namespace fields are published.

See RESULTS.md and study.json for actual outcomes and any uncompleted cases.
Neither
requested duration nor a passing execution verdict closes all M3 gates. Remaining age/clock gates,
remaining age/security/semantic alignment, long v2 N5, deterministic N3, N4 phase
barriers, other devices/offloads and controlled resources remain separate work.
All 83 host tests pass after the runner change; no new ROS GTest/full M2 execution is
claimed. Intrinsic/M4 is unchanged; PR #2 remains draft.

The paced-DDS cohort was completed, replayed and archived before the SRT-only
runner change. These are separate frozen source configurations. The DDS XML
pacing candidate is not applied to SRT; default DDS N5 discovery remains open.
Offered load/process liveness do not prove matched-window competitor delivery.
No isolated transport/resource advantage follows from separate emulated runs.
