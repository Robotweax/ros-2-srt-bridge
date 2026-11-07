# CONTROL classifier/root-qdisc stage diagnostic — 7 November 2026

A dedicated software CONTROL tc PASS counter is now qualified relative to the
tested root-loss fixture and the existing AF_PACKET tap. The live N5 run did
**not** reproduce a >=1-second old-flow gap. It also **failed robot PCAP filter-
population reconciliation**, so no full capture/N5 acceptance is claimed.

## Original failure and fresh qualification revision

The first [plan](diagnostic-plan.json), source `708af1b`, stopped at its synthetic
probe. Its baseline, negative-port and root-loss phases completed, but netem→TBF
replacement failed because tc cannot reuse the same root handle for a different
qdisc kind. The original FAILED result/error and partial artifacts are retained
in `failed-probe/`; its planned ROS/N5 executions were not run.

The fixture helper now explicitly deletes only the owned operator root when
changing netem/TBF kind, with its packet generator idle. The classifier remains
installed. This changes the synthetic helper, not default NetworkLab shaping.
A focused regression checks both kind transitions and same-kind preservation;
cooperative receiver shutdown on errors also retains future receiver records.

A separately committed [revision](diagnostic-plan-r2.json), source `f2010a1`, ran
one fresh synthetic probe with exact known populations:

| Phase | UDP sends | Selected PASS increment | Source tap | Peer tap / receiver |
| --- | ---: | ---: | ---: | ---: |
| N0 baseline, source10080 | 16 | 16 | 16 | 16 / 16 |
| N0 SENSOR-port negative control, source10081 | 4 | 0 | 4 | 4 / 4 |
| Root 100% loss, source10080 | 16 | 16 | 0 | 0 / 0 |
| N5 shaped, source10080 | 16 | 16 | 16 | 16 / 16 |
| N0 restored, source10080 | 1 | 1 | 1 | 1 / 1 |

Native/PCAP probe identities and populations match, captures are complete,
features are unchanged, and filter removal is verified. This places the software
PASS action before the tested root loss and the taps after that loss in this
owned fixture. It does not establish physical-frame delivery or behavior on
other drivers/offloads. These are synthetic tagged UDP sends, not SRT-authenticated
commands. See `qualified-probe/result.json`.

## Observer and live run

The opt-in `--control-qdisc-diagnostics` installs a dedicated software u32/gact
PASS rule (preference49150), selecting UDP CONTROL port10080 and the exact owned
peer /32. Existing classifier hooks are refused; root kind/handle/options are
checked unchanged. The rule executes a PASS verdict and adds work; it is not
the passive AF_PACKET observer. Default invocations install nothing.

Polling targets 200 ms, caps at 37500 records and retains sequence/read brackets,
explicit errors/final status, pass counters and separately bracketed root-only
counters/gauges. Root counters cover the whole interface; child counters overlap
and are not summed. The port/peer selector is an aggregate, not an authenticated
SRT socket or per-datagram identity. Classifier removal and empty readback are
verified after collection.

One 15-s permanent-neighbor ROS N0 smoke passed with **eight successes/effects**,
complete diagnostics and reconciled PCAP. One 300-s N5/seed1701 permanent-neighbor
candidate then recorded **129 successes/effects, 21 skipped slots, zero unresolved
intents and no active CONTROL loss/close**. No fully observed old-flow egress gap
>=1 s recurred. The original result is retained as a no-reproduction diagnostic,
not a historical reset fix, residual-gap localization or replacement cohort.

Measured source is `f2010a1` for smoke and `83e9dd5` for N5. Frozen source hashes
and eight runtime hashes match before/after. SRT/SDK/ROS binaries, timeouts,
protocol policy and default dynamic-neighbor fixture are unchanged. Permanent
neighbors and the classifier remain explicit diagnostic interventions.

## Post-hoc aggregate stage crosscheck

The unchanged gap threshold produced no incident interval. A separately labeled
post-measurement aggregate analysis compares two counter snapshots wholly inside
native capture coverage against the wider whole-capture selected outgoing UDP
population:

| Role | Selected PASS execution delta | Wider native selected outgoing observations |
| --- | ---: | ---: |
| operator | 6991 | 6991 |
| robot | 14771 | 5122 |

This records a population difference between classifier executions and tap
observations, consistent with removal/withholding after the tested classifier.
It is **not** an exact per-packet loss count: boundaries, in-flight behavior and
possible execution/requeue semantics differ. The final sampled robot root has
92564 whole-interface drops and zero backlog/qlen; these values cannot be assigned
to individual CONTROL packets. No unique queue/drop cause or explanation of the
previous 1.315-s gap follows. The failed PCAP gate is not rescued. The aggregate
extension and its boundary test were added after measurement; provenance keeps
that distinct from the frozen measured source.

## Capture gate, outcomes and limits

N5 operator PCAP has **110671 file/captured/filter packets**, with zero kernel
drops. Robot PCAP has **110671 file/captured packets versus 110673 received by
filter**, also zero kernel drops. Its file integrity is valid but population
reconciliation is **false**. The original development manifest says `passed`
while `pcap_population_reconciled=false`; that is not capture qualification.
No missing records are reconstructed, no cause is assigned, and no retry replaces
this result. Realtime PCAP windows remain withheld by clock qualification too.

Independent native captures retain **110690 records per endpoint**, zero reserve/
copy failures, qualified clock/count/hash coverage. TC logs retain **1595 records
per endpoint**; provider logs **2995/24/3057**, command traces **405/5/5** are complete
without loss/exhaustion. Permanent state/MAC remains verified. Maximum observed
TC read span is 63.643833 ms in N5 and 68.819250 ms across smoke/N5; sample-start
gaps reach 210.192542 ms. These are observations, not bounds or negligible cost.

Closed immutable journals agree on all 129 confirmed results/context fields,
with one SDK handoff each and dispatch before conservative receiver start
deadlines. Source/published/observer sensor populations are **75034/27873/27873**,
all conservation balances zero; large deficits remain. No lossless-delivery,
physical-realtime, security-parity or resource/performance claim is made.

Host tests: **144 before original probe, 145 after transition fix, 148 before N5,
149 after the exploratory aggregate boundary test**; syntax checks pass. No fresh
full SDK/ROS/M2 execution is claimed for these tools-only changes.

[Findings](findings.json), [source provenance](source-provenance.json), original
probe/smoke/N5 manifests/logs, state/counter samples, provider/neighbor/ARP/gap
analyses and journal audits retain their own scopes. Raw packet payloads/prefixes,
journals, clocks and resources remain local with SHA-256 identities. No secrets
or inspect/environment dumps are published. Earlier failures/UNKNOWNs unchanged.

Next: investigate the two-record filter/file shutdown discrepancy with a bounded
capture-drain test and exercise the qualified stage observer under a deterministic
queue/loss interval. Do not repeat spontaneous N5 runs until one looks favorable.
Default fixture, historical exact cause and full N5/M3/other gates remain open.
PR #2 stays draft; Intrinsic/M4 is untouched.
