# Paced DDS sensor profile results

The default remains system. Every N5 row uses simultaneous startup, the unchanged
512-kbit/s endpoint qdiscs, 16-packet netem queue and 128,000-bit/s offered UDP
competitor. The paced profile explicitly changes sensor publication/egress policy.
All rows are development evidence, not a controlled SRT/DDS performance comparison.

| Run | Source s | Produced / callbacks | Accepted / stale / clock-rejected | Commands success / intents | Effects | Age checks |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| n5-paced-full | 300.105 | 75,025/19,128 | 19,128/0/0 | 150/150 | 150 | True |
| n0-system | 15.112 | 3,778/3,765 | 3,765/0/0 | 8/8 | 8 | True |
| n0-paced | 15.107 | 3,777/961 | 961/0/0 | 8/8 | 8 | True |
| sensor-paced | 15.085 | 3,772/971 | 971/0/0 | not exercised | — | True |
| n5-paced-1701 | 15.103 | 3,776/972 | 972/0/0 | 8/8 | 8 | True |
| n5-paced-2903 | 15.095 | 3,773/954 | 954/0/0 | 8/8 | 8 | True |
| n5-paced-4211 | 15.110 | 3,778/964 | 964/0/0 | 8/8 | 8 | True |

System and UDP-1200 N5 both fail readiness before a measurement window; their
failed manifests and competitor checks remain preserved. No command/sensor population
or latency is invented for those absent windows. The first paced smoke is retained
as development: it predates stricter competitor reporting and is not a final row.

The full N5 paced run confirms 150/150 distinct commands with 150 effects, no inbox
drops, lease expirations or seals. Both peers end ready. Source rates are actual
199.993 Hz IMU / 50.002 Hz joints. Produced populations 60,019 / 15,006 yield
11,752 / 7,376 callbacks; every received callback passes its local shared-VM age
estimate gate. Missing before callback includes deliberate middleware pacing/
replacement, kernel/network and reader-history loss; it is not isolated WAN loss.
The low callback fraction is a material tradeoff, not a lossless transport claim.
Both closed journals pass quick_check and agree on 150 SUCCEEDED/revision-3 entries
and matching result generations 1–150. Source/command fences and drain remain intact.

All three paced N5 smoke seeds confirm 8/8 with eight effects. Whole-run competitor
rates are near 128 kbit/s, with host liveness polls throughout scenario execution.
This is offered-load/liveness evidence, not matched-window delivered throughput.
Source/receiver counts stay separate from packet capture counts. Whole-run captures
include discovery, services/diagnostics and competitor; no matched-window overhead
or CPU comparison is claimed. Runs overlap fixtures in an emulated amd64 VM.

The native probe verifies participant controller budget, both named sensor writer
modes/controller/history/reliability/durability/memory policy/data sharing and the
default command writer. A negative XML-opt-in check fails publisher creation.
The build/preflight recipe passes. 35 host Python tests pass. Paced-profile N0
duplicate/conflict/lost-reply/SIGKILL/QUERY/no-replay/five-second-shutdown acceptance
passes, including unchanged leases during the blocked handler. Combined N0 system,
combined N0 paced and sensor-only paced regressions pass. Production compiled
sources and bridge binary are unchanged since 02d40e6; its 32 ROS GTests/full M2
results remain historical rather than claimed as rerun in this config/tool step.

All ten final source inventories match, installed Python bytes match and native
probe binary/source hashes are retained. Raw PCAPs/journals stay local with hashes.
M3 remains open: default N5 discovery, cross-session uncertainty, complete durations/
seeds, command-phase barriers, DDS emission-stage accounting, age/security and
matched CPU/wire/SRT pacing/reconciliation cost equivalence are not qualified.
