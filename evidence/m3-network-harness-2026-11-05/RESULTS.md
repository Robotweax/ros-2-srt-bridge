# M3 development results

SRT only. N0 is a full five-minute window; all other rows are 15-second smoke
windows at base seed 1701 (operator direction 1702). This is not M3 acceptance.
The histogram population is the last diagnostic snapshot, including startup;
observer totals and observation tails are recorded separately in each manifest.

| Run | Window s | Observed IMU / joints | Confirmed commands / attempts | IMU upper-age p99 / max ms | Unknown-age / stale admission drops | Robot outbound parity/source frame-byte ratio |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| N0-full | 300.01 | 27569 / 13709 | 150/150 | 15 / 17.62 | 0 / 0 | 0.601 |
| N1-smoke | 15.01 | 1343 / 705 | 8/8 | 64 / 71.80 | 0 / 0 | 0.595 |
| N2-smoke | 15.02 | 841 / 515 | 8/8 | 133 / 146.20 | 0 / 0 | 0.606 |
| N4-smoke | 15.00 | 1202 / 595 | 7/7 | 14 / 14.90 | 0 / 0 | 0.599 |
| N5-smoke | 15.02 | 707 / 484 | 8/8 | 136 / 156.64 | 0 / 0 | 0.329 |

Different profiles/durations and short transients make these rows unsuitable as
a statistical performance comparison. Upper-age distributions include delivered
samples only; missing, rejected and unresolved populations remain explicit in
the manifests. One-way N4 and commit-phase barriers remain unqualified.

The full N0 run produced 150 confirmed results and exactly 150 device effects.
It observed IMU marker span 54,311 with 26,742 missing within that span, and joint
span 14,626 with 917 missing. These exclude unknown leading/trailing losses.
Captured SRT DATA counts agree between endpoint egress/ingress, and the sink
reports no session rejection/replacement/stale drops. The large gaps therefore
require attribution before the WAN boundary (for example local DDS ingress or
latest-only sender/pump cadence); the precise stage is not proven by this run.
The configured 200 Hz timer is a target, not an achieved-rate guarantee here.
No source-rate or full M3 performance acceptance is claimed.

The 256-packet N5 prototype in `attempts/` had 81 unknown-age and 590 stale
admission drops and one unresolved command. The 16-packet child-queue rerun
confirmed eight commands. The child packet cap is authoritative after replacing
the TBF default child; the root's configured byte limit alone does not cap a
replacement netem child. Both records remain available; the prototype is not the
current N5 configuration. Competing traffic uses iperf3 `-b 128K` (131,072 bit/s
target); recorded sender summaries are approximately 132 kbit/s. The iperf server
is deliberately stopped at cleanup and its client reports server termination.

CPU and summed RSS are in the manifests and raw per-process observations. These
are Linux amd64 user processes emulated on an aarch64 Docker Desktop VM, with
20 VM CPUs and about 8.3 GB VM RAM. CPU excludes the observer/capture; summed RSS
can double-count shared pages and process-start/exit CPU tails are not captured.
No hardware or DDS efficiency conclusion follows.
