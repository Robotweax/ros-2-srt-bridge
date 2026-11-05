# Sensor-cadence results

All rows are SRT N0 (no injected delay/loss) on the recorded emulated Linux amd64
image. Marker spans cover first-to-last observed source payload, not unobserved
leading/trailing loss. Histograms stop at the last diagnostic snapshot.

| Run | Window seconds | IMU source marker span | Missing within span | Observed IMU | IMU age-upper p99 / max ms |
| --- | ---: | ---: | ---: | ---: | ---: |
| Before 30 s | 30.00 | 5,463 | 2,650 (48.51%) | 2,813 | 12 / 14.33 |
| After 30 s | 30.02 | 5,413 | 82 (1.51%) | 5,331 | 12 / 13.01 |
| Before 5 min | 300.01 | 54,311 | 26,742 (49.24%) | 27,569 | 15 / 17.62 |
| After 5 min | 300.01 | 53,534 | 741 (1.38%) | 52,793 | 12 / 13.90 |

The 30-second attribution run observed 5,461 IMU/1,481 joint ingress callbacks,
2 BUSY submissions, no obsolete submissions, and 2,633 sender mailbox
replacements. With the faster sender the 30-second run had 5,416/1,479 ingress,
11 BUSY submissions and zero mailbox replacements. The native isolated regression
independently went from 48/100 delivered (old wait) to 89/99 IPv4 and 89/100 IPv6
(new wait), above its 80% gate. Scheduling variation and strict route pacing still
permit latest-only drops; the test is not a hard real-time guarantee.

The five-minute rerun confirmed 150 commands and exactly 150 device effects,
without unresolved/non-admitted commands. Joint gaps fell from 917/14,626 (6.27%)
to 29/14,576 (0.20%). Sender final diagnostics had 48 BUSY submissions and four
mailbox replacements. Sink admission rejected/replaced/stale/unknown-age counts
were zero. Snapshot tails differ and do not form an exact conservation equation.

The original five-minute run measured source CPU 17.35% and sink CPU 7.75% of
one VM core; the rerun measured 22.39% and 10.87%. More samples were forwarded,
and active sender wakeups increased. These observations include workload changes,
emulation and process-observation limits, so they are not a controlled hardware
CPU benchmark. Source/sink maximum summed RSS was about 185 MB / 87 MB in the
rerun. Raw metrics and their scopes are retained in each manifest.

The N5 smoke with the faster sender preserved freshness and accounting, but six
of seven queued commands were confirmed before the cutoff while the device had
seven effects. The seventh result is explicitly unresolved/censored; it is not
reported as a failure without effect or a confirmed success. Higher offered traffic
changes congestion. Full N5 qualification, final drain/window accounting and the
DDS comparison remain open.

Residual N0 gaps (~1.4% IMU) are not fully attributed yet; possible stages include
strict route pacing and latest-only outbound queues. The simulator's 200 Hz is a
configured target and actual source cadence remains below that under this setup.
No full-rate, lossless, M3 acceptance or SRT/DDS superiority claim follows.
