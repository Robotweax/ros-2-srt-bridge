# DDS readiness results

Count/audit success is distinct from command completion and age qualification.
All primary runs use seed 1701 and the system DDS transport. N2 is 60 seconds;
N1/N4/N5 and sensor-only checks are 15-second development smokes.

| Run | Status | Confirmed / attempted | Non-admitted | Unresolved | Effects | Produced / received | Age checks |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| n0-full | passed | 150/150 | 0 | 0 | 150 | 75,025/75,022 | True |
| n1-smoke | passed | 8/8 | 0 | 0 | 8 | 3,774/2,868 | True |
| n2-60s | passed | 17/18 | 0 | 1 | 17 | 15,025/6,952 | True |
| n4-smoke | passed | 4/5 | 0 | 1 | 4 | 3,782/3,216 | True |
| n5-control-first | passed | 2/2 | 0 | 0 | 2 | 3,777/1,763 | True |
| n5-simultaneous | failed; no window | — | — | — | — | — | — |

The five-minute N0 runs at actual 199.976 Hz IMU / 50.002 Hz joints, with
150/150 confirmed commands and 150 effects. Three IMU samples are missing before
callbacks; joints have no gap. Both endpoint inbox-drop and lease-expiration
counts are zero. Local shared-VM age checks pass; this is not cross-host age
qualification. Both journals have 150 SUCCEEDED/revision-3 entries, rate 200 and
matching result generations 1–150.

N1 confirms 8/8. N2 confirms 17/18, with one unresolved intent, 17 effects and
12 blocked slots; both peers end ready with zero lease expirations. N4 confirms
4/5 with one unresolved intent and four effects; both peers end ready after one
lease expiration each. This demonstrates rediscovery, not replay of old intent.
N5 control-first confirms 2/2 with two effects but skips six pending slots.
Its startup ordering is explicit; simultaneous N5 still fails before a window.
The final sender receives 140 HELLOs but has zero outgoing control/HELLO matches,
with one incoming publisher on each channel: partial/asymmetric DDS discovery,
rather than an established mutual session. Earlier N5 attempts had zero delivered
HELLOs. No claim is made that packetization or liveness solved discovery.

See each manifest for skipped pending slots, startup diagnostics, lease expirations,
source rates, command censoring and both endpoint captures. All final runs match
the frozen source inventory. The first of three consecutive fault runs records
the full build; later runs reuse its hashed binary. ROS tests: 23 actual GTests
(26 including wrappers). Host Python: 30 passed. M2 was fully rebuilt and passed.

All captures are whole-run UDP Ethernet observations, including discovery, local
diagnostics/services and the N5 competitor. They do not provide matched-window
sensor overhead. Source-enabled windows are fenced; received callbacks rejected by
the age gate are distinct from samples missing before callbacks. The shared-VM
header-age estimate is not SRT conservative age qualification. Runs overlapped
development fixtures in an emulated amd64 VM; no controlled CPU/hardware claim.

Final N0 closed journals pass read-only quick_check and agree on every inspected
ID, payload hash, state/reason, revision, rate, generation and result. Raw PCAPs
and SQLite files stay local; hashes and sizes are recorded. Earlier evidence is
immutable; development manifests preserve failures and variable completion.

M3 remains incomplete: no cryptographic DDS peer authentication/encryption, no
cross-host clock qualification, no matched CPU/wire comparison, no full seed/duration
matrix, no deterministic N3 DATA/FEC selector or N4 command-phase barriers.
