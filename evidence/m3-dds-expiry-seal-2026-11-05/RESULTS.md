# DDS expiry-seal results

All primary runs use protocol v2. N0 is five minutes; N2 probes are 60 seconds
per seed, and N4/N5 are 15-second development smokes. Count/audit success does
not mean every command succeeded. Expiry is reported separately.

| Run | Success / intents | Expired | Unresolved | Effects | Application COMMANDs | Seal requests | New receiver tombstones | Existing-record replies |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| n0-full | 150/150 | 0 | 0 | 150 | 150 | 0 | 0 | 0 |
| n4-smoke | 4/5 | 0 | 1 | 4 | 5 | 0 | 0 | 0 |
| n5-control-first | 2/2 | 0 | 0 | 2 | 2 | 31 | 0 | 31 |
| n2-1701 | 24/24 | 0 | 0 | 24 | 24 | 1 | 0 | 1 |
| n2-2903 | 28/29 | 1 | 0 | 28 | 29 | 2 | 1 | 1 |
| n2-4211 | 24/25 | 1 | 0 | 24 | 25 | 16 | 1 | 15 |

All three N2 probes end with zero unresolved intents. Seed 1701's seal returns
an already committed success unchanged. Seeds 2903 and 4211 each commit exactly
one EXPIRED/revision-1 tombstone, with no handler dispatch for that ID. In seed
4211, ID 20 expires; new scheduled ID 21 then succeeds using expected generation
19 and result generation 20. There are 25 application COMMANDs for 25 distinct
intents, 24 starts/effects, and no resend of the expired intent.

N0 runs for 300 seconds at actual 199.984/50.001 Hz, confirms 150/150 commands
with 150 effects and no seals, and passes its shared-VM age checks. It produces
75,024 samples and receives 75,002 (20 IMU and two joint gaps before callback).
This is not isolated WAN loss or cross-host age qualification. Both closed
journals pass quick_check and agree on all 150 terminal results.
N4 retains one unresolved intent after session rotation; no seal is sent across
that context change. Both peers regain readiness. N5 control-first retains two
successes/two effects despite 31 seals reading existing records, with no false
expiry. It skips six slots. Default simultaneous N5 fails before any measurement
window; its failed manifest is preserved, with no invented outcome population.

See journal-inspection.json for durable expiry IDs/hashes, exact saved deadline
and admission times, zero dispatch timestamps, revision 1, invalid result and
matching sender/receiver records. Counters are snapshots and can lag or include
requests later censored by the result window. A seal returning an existing record
does not mean it created a tombstone. COMMAND counts are application publications;
Reliable DDS can still retransmit packets on the wire.

Source/binary hashes and installed Python bytes match. Eight new actual-journal
GTests pass, for 32 actual ROS GTests (36 with wrappers), plus 33 host Python tests.
Full DDS fault acceptance and a full M2 rebuild pass. The recorded first C++ build
has only later runner-metadata/host-test differences, with every compiled input
unchanged; final run inventories match completely. SDK archives/source and SRT
remain unchanged. Raw PCAPs/journals stay local; their hashes/sizes are retained.

These are development results in an emulated amd64 VM, with overlapping fixtures.
No controlled CPU/hardware or SRT/DDS performance advantage is claimed. Security,
age origins/bounds, matched CPU/wire windows and full impaired duration/seed gates
remain open. The new DDS expiry protocol has no qualified SRT semantic/cost parity.
N4 is a mid-window outage rather than a command-phase barrier; context changes
remain QUERY-only. N5 simultaneous startup remains a separate discovery limit.
