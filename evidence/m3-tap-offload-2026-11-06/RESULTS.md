# Results

74 host Python tests pass. The version-2 native program builds with warnings as
errors and passes the 40-datagram/80-observation monotonic clock/length selftest.
A forced 4-KiB overflow reports 2,000 invocations, 23 stored records and 1,977 failed
reservations, expected exit 2; loss is not hidden.

## Controlled tap cases

Counts below exclude the extra successful restoration-control datagram. The
same open observers must see that control in every case. Native/PCAP known probe
identities and lengths agree exactly in the final run; every recorder is loss-free.

| Case | Datagram intents | Sender tap | Receiver tap | Application receipts | Observed position/representation |
| --- | ---: | ---: | ---: | ---: | --- |
| baseline | 16 | 16 | 16 | 16 | plain UDP observation population matches delivery |
| egress-drop | 16 | 0 | 0 | 0 | egress tap after tested qdisc drop |
| egress-delay | 16 | 16 | 16 | 16 | egress tap includes tested 200ms queue delay |
| ingress-drop | 16 | 16 | 16 | 0 | ingress tap before tested ingress drop |
| gso-noqueue | 8 | 1 | 1 | 8 | UDP segmentation representation characterized |
| gso-netem | 8 | 1 | 1 | 8 | UDP segmentation representation characterized |
| shaped-only | 16 | 16 | 16 | 16 | plain UDP observation population matches delivery |

The 200-ms delay case's actual sender deltas are retained per datagram; the final
range is 200.02–206.94 ms. Aggregate root drop increments exceed the targeted flow count; the excess is
not attributed by protocol. Targeted UDP counters establish the 16 test packets independently. Both GSO cases carry
one 9,642-byte skb with eight segments at each endpoint, while the socket delivers
eight 1,200-byte datagrams. Their skb accounting qualifies, while frame
interpretation is false. This remains a virtual-device observation, not a
physical-link test. The shaped-only fixture excludes competition/application peers.

## Live regressions

Final SRT N0 and default DDS N0 smokes confirm 8/8 commands each. Paced DDS N5
30 seconds confirms 15/15. Both phases at both endpoints qualify monotonic skb
accounting and the no-indicated-GSO/VLAN/over-MTU interpretation. All recorder
reservation/copy errors are zero. The default sensor smoke passes without the
optional observer/BPF capability. All four use immediate PCAP mode and reconcile
the captured/filter/file counters in this run; this is not a universal counter
identity. Read-only feature snapshots match before/after at opted-in endpoints.

Final live runs: `srt-n0`, `dds-n0`, `paced-n5`, `default-sensor`.
Seven controlled cases share one frozen 159-file inventory; four live inventories
also match all 159 files. Installed scripts and the 56 compiled production source
files plus command/simulator binaries are unchanged. The observer native binary
changes only the lab artifact/metadata, not SDK wire/IPC or execution semantics.
No new ROS GTest/full M2 execution is claimed.

## Historical compatibility and unresolved scope

Four historical classic captures reproduce all numeric/classification fields;
only the incorrect generic pre-qdisc scope text changes in reanalysis. Four v1
endpoint/phase windows reproduce their old numeric/classification fields, with
missing offload metadata explicitly unknown and interpretation unqualified.
Original artifacts are not rewritten. `counter-examples.json` distinguishes the
buffered missing-control case from cases where all known observations match but
filter counters differ. Counter equality is not treated as a universal proof.

Older v1/buffered observer resource studies do not establish v2/immediate cost.
Physical-link/offload paths beyond this veth fixture, controlled resource costs,
remaining profile/duration matrix and N3/N4 special gates remain open. No
SRT/DDS advantage or complete M3 acceptance is claimed.
