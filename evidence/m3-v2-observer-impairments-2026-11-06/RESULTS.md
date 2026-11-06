# Results and limits

All twelve changed-configuration workloads passed without retries: eight 45-second N0 runs and four 60-second N1/N2 probes. The earlier smaller-buffer study failed and remains separate. The short impairment probes do not satisfy the full 600-second, three-seed matrix.

Every cgroup phase replays exactly from the archived projections. Opt-in native recorders report zero reserve/copy failures. PCAP kernel drops are zero. Raw captures, packet prefixes, clocks and journals remain local with hashes. No physical delivery, isolated CPU cost or full M3 acceptance is established.

All 299 admitted commands confirmed SUCCEEDED, with 299 effects and no unresolved intents. The 24 closed journals pass integrity checks and agree on revision-3 results. DDS N2 skipped five scheduling slots while awaiting command status: 25 attempts, all confirmed. Its maximum invocation-to-terminal-observation latency was 10,870.99 ms (includes status polling/reconciliation, not receiver start or execution latency); the other impairment runs each confirmed 30 with no skipped slots. No retries or weakened deadlines were introduced.

## Observer on/off observations

The observed CPU differences retain variation and negative values; inner/outer observations are neither physical bounds nor confidence intervals. Charged-memory maxima include cache/kernel allocations. Both modes use immediate PCAP with the larger buffer; historical smaller-buffer or v1 results cannot substitute. Source/callback populations differ.

| Group | On / off pair | Endpoint | Observed CPU difference (core percentage points) | Sampled charged-memory max difference (MiB) |
| --- | --- | --- | ---: | ---: |
| srt | srt-N0-2-on / srt-N0-1-off | robot | +0.99–+1.94 | +23.93 |
| srt | srt-N0-2-on / srt-N0-1-off | operator | +1.04–+1.85 | +24.19 |
| srt | srt-N0-3-on / srt-N0-4-off | robot | -0.48–+0.49 | +23.13 |
| srt | srt-N0-3-on / srt-N0-4-off | operator | -1.09–-0.32 | +23.04 |
| dds | dds-N0-1-on / dds-N0-2-off | robot | -2.29–-1.75 | +22.75 |
| dds | dds-N0-1-on / dds-N0-2-off | operator | -3.99–-3.45 | +23.21 |
| dds | dds-N0-4-on / dds-N0-3-off | robot | +0.07–+0.60 | +20.56 |
| dds | dds-N0-4-on / dds-N0-3-off | operator | -0.29–+0.31 | +21.88 |

## Workload populations

Rates list IMU/joints in Hz. Command attempts, receiver effects, terminal states and unresolved observations remain distinct; see study.json and journal-audits.json for status detail. Callback deficits are not isolated network loss.

| Run | Command attempts | Effects | Produced | Received callbacks | Actual source Hz |
| --- | ---: | ---: | ---: | ---: | --- |
| srt-N0-1-off | 23 | 23 | 11283 | 10879 | 199.998/50.010 |
| srt-N0-2-on | 23 | 23 | 11289 | 10936 | 199.990/50.003 |
| srt-N0-3-on | 23 | 23 | 11293 | 10943 | 199.996/50.010 |
| srt-N0-4-off | 23 | 23 | 11288 | 10901 | 199.990/50.009 |
| dds-N0-1-on | 23 | 23 | 11273 | 11270 | 199.886/49.983 |
| dds-N0-2-off | 23 | 23 | 11271 | 11268 | 199.981/50.017 |
| dds-N0-3-off | 23 | 23 | 11278 | 11276 | 199.988/50.008 |
| dds-N0-4-on | 23 | 23 | 11277 | 11275 | 199.958/50.006 |
| srt-N1-probe | 30 | 30 | 15026 | 11127 | 199.988/50.014 |
| dds-N1-probe | 30 | 30 | 15031 | 11296 | 199.977/50.011 |
| srt-N2-probe | 30 | 30 | 15023 | 6410 | 199.983/50.004 |
| dds-N2-probe | 25 | 25 | 15023 | 6898 | 199.937/50.013 |

## Container source-enabled resources

CPU includes all work charged to the container, excludes work elsewhere, and is affected by shared emulated VM scheduling. Memory is sampled cgroup charge, not RSS/PSS or a hard peak. These results do not establish a transport advantage.

| Run | Endpoint | Observed cgroup CPU (core %) | Sampled charged memory (MiB) |
| --- | --- | ---: | ---: |
| srt-N0-1-off | robot | 42.54–42.88 | 206.94 |
| srt-N0-1-off | operator | 31.89–32.26 | 146.98 |
| srt-N0-2-on | robot | 43.87–44.48 | 230.87 |
| srt-N0-2-on | operator | 33.30–33.74 | 171.17 |
| srt-N0-3-on | robot | 40.47–40.95 | 229.94 |
| srt-N0-3-on | operator | 31.12–31.51 | 171.22 |
| srt-N0-4-off | robot | 40.47–40.95 | 206.81 |
| srt-N0-4-off | operator | 31.83–32.20 | 148.18 |
| dds-N0-1-on | robot | 23.42–23.66 | 187.00 |
| dds-N0-1-on | operator | 26.81–27.04 | 153.68 |
| dds-N0-2-off | robot | 25.41–25.71 | 164.25 |
| dds-N0-2-off | operator | 30.49–30.80 | 130.48 |
| dds-N0-3-off | robot | 23.40–23.68 | 167.03 |
| dds-N0-3-off | operator | 27.79–28.11 | 131.91 |
| dds-N0-4-on | robot | 23.75–24.00 | 187.59 |
| dds-N0-4-on | operator | 27.82–28.09 | 153.79 |
| srt-N1-probe | robot | 43.33–43.50 | 235.43 |
| srt-N1-probe | operator | 29.17–29.37 | 175.22 |
| dds-N1-probe | robot | 22.65–22.88 | 188.86 |
| dds-N1-probe | operator | 24.72–24.94 | 155.66 |
| srt-N2-probe | robot | 45.60–45.87 | 236.22 |
| srt-N2-probe | operator | 24.79–24.94 | 175.29 |
| dds-N2-probe | robot | 28.32–28.52 | 190.26 |
| dds-N2-probe | operator | 22.56–22.72 | 155.44 |
