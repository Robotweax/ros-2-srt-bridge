# Monotonic observation windows

Final SRT N0 and DDS N0 smokes (15 s), paced DDS N5 (30 s) and default sensor
smoke (15 s) all pass. Command attempts are 8/8, 8/8 and 15/15 confirmed.
Both phases at both endpoints qualify CPU and opt-in monotonic capture. The
default sensor run has no observer or added CAP_BPF. This is short development
evidence, not full M3 duration/seed qualification or controlled performance.

Below: outbound IPv4 UDP skb frame lengths at the AF_PACKET observation point.
Includes every class (including control/discovery and the N5 competitor).
Endpoint totals overlap traffic observations; do not sum them as unique network
bytes. These figures do not measure isolated sensor overhead or physical link
transmission/delivery. Kernel observer work can be charged to endpoint tasks;
CPU comparisons must account for this capture variant.

| Run | Phase | Endpoint | Outbound UDP frames | Outbound frame bytes | Capture qualifies |
| --- | --- | --- | ---: | ---: | --- |
| srt-n0 | source_enabled | operator | 1607 | 141496 | yes |
| srt-n0 | source_enabled | robot | 6179 | 2913305 | yes |
| srt-n0 | fenced_observation | operator | 1624 | 143182 | yes |
| srt-n0 | fenced_observation | robot | 6196 | 2914967 | yes |
| dds-n0 | source_enabled | robot | 4150 | 2021872 | yes |
| dds-n0 | source_enabled | operator | 334 | 159232 | yes |
| dds-n0 | fenced_observation | robot | 4211 | 2052222 | yes |
| dds-n0 | fenced_observation | operator | 382 | 182960 | yes |
| paced-n5 | source_enabled | robot | 3067 | 1750894 | yes |
| paced-n5 | source_enabled | operator | 539 | 262282 | yes |
| paced-n5 | fenced_observation | robot | 3176 | 1833016 | yes |
| paced-n5 | fenced_observation | operator | 587 | 286326 | yes |

Per-class and inbound counts, recorder gates and clock proofs remain in run manifests.
