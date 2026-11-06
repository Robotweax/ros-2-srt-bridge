# Results and limits

All 11 preregistered workloads passed without retries: eight 45-second N0 runs
and three five-minute paced N5 repetitions. Every cgroup phase at both endpoints
qualified. All opt-in monotonic phases qualified, with zero recorder failures.
The existing narrower endpoint CPU qualification is retained separately in each
manifest. Source inventories and projected cgroup reanalysis match exactly.
All 22 closed journals pass quick_check and agree on 634 successful revision-3
command records per side, including result generations and payload hashes.
These are additional functional/resource observations, not complete M3 acceptance.

## Observer on/off observations

Differences below use on-inner minus off-outer and on-outer minus off-inner core
percent observations. They are neither strict physical CPU bounds nor confidence
intervals. Signs vary, especially for SRT; this shared VM does not yield an
isolated observer CPU overhead estimate. Charged-memory maxima are higher in the
on runs, but include cache/kernel allocation and cannot identify a standalone
physical observer footprint. Each paired run confirms 23 commands/effects, while
sensor production/delivery populations differ and remain in the table below.
The first SRT off run produces 198.182 Hz IMU versus approximately 200 Hz in the
other SRT runs. No run is discarded or replaced to reduce variation.

| Group | On / off pair | Endpoint | Observed CPU difference (core percentage points) | Sampled charged-memory max difference (MiB) |
| --- | --- | --- | ---: | ---: |
| srt | srt-N0-2-on / srt-N0-1-off | robot | -9.05–-7.87 | +22.52 |
| srt | srt-N0-2-on / srt-N0-1-off | operator | -5.93–-5.12 | +22.67 |
| srt | srt-N0-3-on / srt-N0-4-off | robot | +6.75–+7.61 | +22.67 |
| srt | srt-N0-3-on / srt-N0-4-off | operator | +5.14–+5.66 | +23.15 |
| dds | dds-N0-1-on / dds-N0-2-off | robot | +0.99–+1.56 | +19.25 |
| dds | dds-N0-1-on / dds-N0-2-off | operator | +0.50–+0.91 | +20.55 |
| dds | dds-N0-4-on / dds-N0-3-off | robot | +0.03–+0.68 | +21.82 |
| dds | dds-N0-4-on / dds-N0-3-off | operator | -1.97–-1.49 | +19.93 |

## Longer paced N5 coverage

Each fresh endpoint pair retains simultaneous startup, shared 512-kbit/s shaping,
16-packet netem queue, live offered 128-kbit/s competitor and the explicit paced
sensor profile. Different N5 seeds label repetitions; no stochastic loss/jitter
is configured. All 450 commands confirm with 450 effects. The reduced callback
population includes intentional middleware pacing/replacement and other stages,
not isolated WAN loss. These passes do not fix default DDS N5 cold discovery.

| Seed | Commands confirmed | Effects | Samples produced | Callbacks received | Recorder records robot/operator | Recorder failures |
| --- | ---: | ---: | ---: | ---: | --- | ---: |
| 1701 | 150 | 150 | 75032 | 19079 | 38758/38565 | 0 |
| 2903 | 150 | 150 | 75018 | 19236 | 38612/38416 | 0 |
| 4211 | 150 | 150 | 75031 | 19286 | 38530/38336 | 0 |

## Workload populations

Rates list IMU/joints in Hz. Counts use each run's existing source-fenced sensor
accounting. Successful effects and callback populations are distinct quantities.

| Run | Command attempts | Effects | Produced | Received callbacks | Actual source Hz |
| --- | ---: | ---: | ---: | ---: | --- |
| srt-N0-1-off | 23 | 23 | 11179 | 10647 | 198.182/49.662 |
| srt-N0-2-on | 23 | 23 | 11286 | 10884 | 199.979/50.017 |
| srt-N0-3-on | 23 | 23 | 11274 | 10842 | 199.981/50.001 |
| srt-N0-4-off | 23 | 23 | 11281 | 10923 | 199.980/50.017 |
| dds-N0-1-on | 23 | 23 | 11270 | 11269 | 199.964/50.019 |
| dds-N0-2-off | 23 | 23 | 11275 | 11273 | 199.921/50.008 |
| dds-N0-3-off | 23 | 23 | 11276 | 11273 | 199.993/50.020 |
| dds-N0-4-on | 23 | 23 | 11266 | 11266 | 199.981/50.017 |
| dds-paced-N5-1701 | 150 | 150 | 75032 | 19079 | 199.997/50.002 |
| dds-paced-N5-2903 | 150 | 150 | 75018 | 19236 | 200.000/50.002 |
| dds-paced-N5-4211 | 150 | 150 | 75031 | 19286 | 199.998/50.003 |

## Container source-enabled resources

CPU uses observed inner/outer deltas. Memory is maximum sampled cgroup charge,
not RSS/PSS/hard peak. The group includes capture/test/competitor processes;
work accounted elsewhere in the VM/host is excluded. Different transport
semantics/crypto/packing make this table unsuitable for an SRT/DDS advantage
claim. Local zero throttling counters do not prove uncontended VM scheduling.

| Run | Endpoint | Observed cgroup CPU (core %) | Sampled charged memory (MiB) |
| --- | --- | ---: | ---: |
| srt-N0-1-off | robot | 54.84–55.71 | 207.67 |
| srt-N0-1-off | operator | 40.67–40.98 | 146.90 |
| srt-N0-2-on | robot | 46.66–46.98 | 230.20 |
| srt-N0-2-on | operator | 35.06–35.55 | 169.57 |
| srt-N0-3-on | robot | 49.93–50.50 | 229.61 |
| srt-N0-3-on | operator | 38.55–38.69 | 170.73 |
| srt-N0-4-off | robot | 42.89–43.19 | 206.94 |
| srt-N0-4-off | operator | 33.04–33.41 | 147.58 |
| dds-N0-1-on | robot | 22.29–22.54 | 186.32 |
| dds-N0-1-on | operator | 24.56–24.80 | 153.11 |
| dds-N0-2-off | robot | 20.98–21.30 | 167.07 |
| dds-N0-2-off | operator | 23.89–24.06 | 132.56 |
| dds-N0-3-off | robot | 22.29–22.60 | 165.19 |
| dds-N0-3-off | operator | 25.76–25.96 | 131.92 |
| dds-N0-4-on | robot | 22.64–22.96 | 187.01 |
| dds-N0-4-on | operator | 23.99–24.28 | 151.85 |
| dds-paced-N5-1701 | robot | 113.49–113.69 | 198.17 |
| dds-paced-N5-1701 | operator | 8.12–8.14 | 168.98 |
| dds-paced-N5-2903 | robot | 113.39–113.61 | 200.35 |
| dds-paced-N5-2903 | operator | 8.17–8.19 | 169.62 |
| dds-paced-N5-4211 | robot | 113.78–113.99 | 199.26 |
| dds-paced-N5-4211 | operator | 8.29–8.31 | 168.42 |
