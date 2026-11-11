# M3 source-fenced window and stage accounting

This follow-up qualifies the sensor measurement population before the DDS
comparison. M3 remains in progress; these are emulated Linux amd64 development
runs, not hardware performance or superiority evidence. See [results](RESULTS.md).

The new read-only `/bridge/get_metrics` snapshot exposes bounded sensor-stage
counters, pending slots, histograms and a process owner epoch. The simulator's
`/robot/set_publishing` service shares the sensor callback group, so its pause
response fences publication. The harness pauses and drains warmup, establishes a
fresh SRT session with zero source SAMPLE counters, records stable empty-pipeline
checkpoints, then resumes the device. This excludes warmup SAMPLE/FEC history.
At cutoff it pauses again, drains command results for at most eight seconds,
and checks stable empty-pipeline snapshots with unchanged owner epochs. Sensor
counter deltas must satisfy all six conservation equations and the window
histogram populations must match publications. The SRT-acceptance-to-decoded-
receiver gap includes provider, TTL, kernel, network and FEC behavior; it is not
a measurement of physical WAN loss.

The sender polls before a bounded sleep to a submillisecond pacing deadline,
retaining strict rate and queue limits. The simulator preserves schedule phase,
skips missed slots without bursts, and does not reset phase for repeated same-
rate commands. Native queue/transport tests and four simulator schedule tests
cover these changes. SDK wire v1 and private worker IPC v3 remain unchanged.

Final runs and copied evidence:

| Directory | Local run | Result |
| --- | --- | --- |
| n0-full | .local/m3/20261105T153616391199Z | 300-second N0; 150 confirmed commands |
| n5-smoke | .local/m3/20261105T154456488682Z | Short congestion smoke; two confirmed, one unresolved |
| n4-smoke | .local/m3/20261105T154538668977Z | Short outage smoke; seven confirmed |
| sdk-regression | .local/m1/20261105T145359704756Z | 15 Debug, 15 ASan/UBSan, 67 native, 10 native ASan/UBSan; relocated consumer passed |
| m2-regression | .local/m2/20261105T154053788107Z | Original M2 scenario and ROS tests passed |

`source-verification.json` records matching source hashes for these final runs.
ROS has seven codec and four schedule GTests (13 reported including two colcon
wrappers). Eleven Python harness/accounting tests passed. `development/` retains
the earlier cadence comparisons and runs before fresh-session isolation. Their
original manifests are historical, not current-source validation. It also records
an M2 preflight image-pin assertion failure: three subsequent inspections matched
the pin and the unchanged runner passed on retry; the original mismatch was not
logged and its cause is unknown. No image assertion was relaxed.

Text manifests/logs are copied here. Raw PCAPs/resource JSONL remain ignored
locally, with hashes and sizes in `raw-artifacts.json`; credentials and journals
are excluded. Counter-accounting success does not mean all commands completed
or that full M3 acceptance passed. DDS baseline, N3 selector, N4 command-phase
barriers, full seed/duration matrix and matched-window CPU/wire accounting remain.
