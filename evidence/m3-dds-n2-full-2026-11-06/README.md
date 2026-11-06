# Default DDS N2: full-duration seeded execution — 2026-11-06

This step extends the short N2 development probes to the planned 600-second
source workload for each base seed: 1701, 2903 and 4211. The frozen plan is
written before the first child runs. Endpoint pairs are fresh and sequential;
operator-to-robot seed is base+1. N2 retains 60±15 ms normal-distribution delay
and 3% random loss in each direction, 256-packet netem queue and readback checks.
This covers default/system DDS with simultaneous startup, 200-Hz IMU/50-Hz joint
production and absolute rate-change intents targeting 200 Hz every two seconds, one pending
intent at a time. It does not qualify SRT N2 or complete M3 acceptance.

## Measurement and command policy

The installed SDK/ROS/worker/capture binaries are reused without rebuilding.
Sources, eight selected installed binary/SDK hashes and installed demo Python
bytes are frozen before execution and verified around each child. The image,
common-VM/zero-offset proof, explicit immediate/full-snapshot 32,768-KiB PCAP
buffer request and v2 native record layout remain those of the preceding study.
The native observer is enabled in all runs; no on/off resource contrast exists.
The observer, driver polling history and shared emulated host can affect timing.

Command admission, deadlines, 1.5-second liveness/freshness, journal durability,
atomic handler claim, status correlation, same-session expiry sealing and
no-replay rules remain unchanged. A busy pending intent skips cadence slots;
there is no catch-up burst. UNKNOWN pauses new work. Missing/NOT_FOUND, timeout
or budget expiry alone do not prove nonexecution. Success, authoritative expiry,
UNKNOWN, unresolved intent and skipped slots remain separate populations.
A full 600-second sensor window does not imply 300 admitted/executed commands.
Terminal status can arrive during the existing eight-second result drain.

The status history retains first/latest 32 polls with explicit omitted counts.
Closed matching original-owner successful records receive the read-only journal
timeline decomposition. Missing/unknown/recovered records withhold that timing
claim. Journal timestamps precede mutations/commits, not fsync completion or
atomic handler start. Polling cadence is not a result latency bound. Aggregate
command-state snapshots used for progress are not per-frame callback evidence.

Zero PCAP kernel drops, captured/file integrity and native recorder loss/coverage
gates stay strict. PCAP filter-population reconciliation is a separate condition
for realtime windows. Native observations concern socket-tap skbs, not physical
frames or delivery. GSO/VLAN/MTU interpretation and actual source/callback counts
remain explicit. No claim of transport parity, isolated overhead or hardware
performance follows from these observations.

## Reproduction

After the existing M3 setup, fresh runs can be invoked separately:

```sh
python3 tools/run_m3_dds.py --commands --profile N2 --seed 1701 \
  --seconds 600 --skip-build --monotonic-capture
```

Repeat with seeds 2903 and 4211. The archived orchestration script writes the
complete plan and checks source/installed hashes before and after each run.
It stops on a failed child, retains the failure, and does not retry or silently
replace cases. The output directory must be fresh. Raw captures, prefixes,
clocks, sampler files and journals remain local with hashes. Published inspect
information is a selected capability/namespace projection, never full env dumps.

All three 600-second cases completed with execution/capture gates passing:
830 successes/effects, 12 receiver-backed expiries without dispatch, one BUSY
admission rejection and 57 skipped slots; no UNKNOWN/unresolved intents. Seed
1701 age estimates failed on clock steps; seeds 2903/4211 qualified their shared-VM
estimates. Realtime packet windows remain withheld in all three runs. Seed 2903 robot PCAP
also has an unreconciled filter population (170,340 filtered versus 170,338
captured/file, zero kernel drops); native recorder qualification is independent. Thus the
full N2 age gate remains open despite completed duration/seed execution coverage.
See [results](RESULTS.md) and study.json for complete outcomes. No new ROS GTest or
full M2 execution is claimed. SRT/full N1, v2 long N5, deterministic N3 and N4
command-phase barriers, device/offload coverage, controlled resources and semantic/
security alignment remain separate work. Intrinsic/M4 remains untouched.
