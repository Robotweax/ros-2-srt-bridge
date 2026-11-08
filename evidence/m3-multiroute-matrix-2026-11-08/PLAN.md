# Short baseline/one-loss repetitions and conditional30s pilot

Freeze this source/plan after223 host tests, Python syntax and diff checks pass.
Run exactly once:
`python3 tools/m3_multiroute_cohort.py --output .local/m3-multiroute-matrix/short`

The cohort executes these six fresh owned fixtures in order, nominal10s each:
baseline1701, baseline2903, baseline4211, one-loss1701, one-loss2903,
one-loss4211. Cases use --capture, their explicit base seed and losses0/1. Stop
at the first failure and mark every remaining case NOT EXECUTED; no retry or
selector adaptation. Prior passing/failing cohorts remain independent. Each
case has its own original result/provenance and controlled child-shutdown report.

Only if all six cases pass every gate, execute exactly once:
`python3 tools/m3_ros_multiroute.py --output .local/m3-multiroute-matrix/pilot30 --capture --losses 0 --seed 1701 --seconds 30`
This is a bounded baseline-duration pilot, not30s one/two-loss acceptance or a
long-duration seed matrix. No further live run/retry is specified by this plan.

Same pinned seven runtime binaries, Linux amd64 Docker emulation, instrumented
phase-preserving IMU200Hz/joints50Hz source, source/sample diagnostics enabled;
no SDK/ROS C++/provider/production policy changes or rebuild. Separate ROS domains,
LOCALHOST, common boot/zero-time-namespace proof, explicit permanent neighbors,
N0 qdisc base/base+1 readback. Seeds have no random impairment here; independent-
start repeatability is not random-loss coverage or causal performance comparison.
No COMMAND workload. Original missing receiver footer/unknown shutdown cause and
stopped original two-loss seed cases remain unqualified and unchanged.

All prior cadence/source/hash/session/clock/QoS/age/accounting/capture/lifecycle
gates stay strict. Actual source count/fenced duration must meet200/50Hz within1%,
skipped slots remain explicit, stable checkpoints empty, all six balances0 and
loss terms nonnegative; observed typed stamps/hashes/order must match source.
Local BUSY, DDS and replacements remain explicit and consume no fabricated SDK
indices or individual replacement-stage proof. All accepted-publication upper
ages<=250ms. Complete source/sender/receiver statuses, zero drops/exhaustion and
all three owned children initially live -> controlled SIGINT exit0, no timeout/
kill. Any missing status or abnormal child outcome fails even if counters balance.

Added window gate: actual resume-to-pause duration must be in[nominal,nominal+1]s.
Allow at most(nominal+1)*250 source records and twice that plus binding1 sender
records:10s allowances2750/5501;30s7750/15501. Unchanged hard limits10000 source,
75000 sample/packet recorder records and128MiB PCAP budget. These allowances do
not stand in for measured cadence, complete traces or strict recorder populations.
No budget enlargement, truncation or undocumented multi-window stitching.
Source wait/host barrier adapt to declared duration; production deadlines do not.

For all baseline/one-loss/pilot cases require SDK-to-receiver gap0 and no receiver
rejection, in addition to six balances. Strict native/full-PCAP source/parity keys
must reconcile exact SDK-assigned messages/ISN, binding offset and partial final
row handling at both endpoints. Separate closed identity and measurement phases;
identity8/8 populations, final BPF before bind/initialkernel0, native observers
first/last and full source-window coverage, stable equal file/dispatch/kernel
counts, verified length/hash, no drops/truncation/exhaustion, unchanged features.
Realtime PCAP timestamps are not age authority; native monotonic times are skb
observations, not physical-wire times. No continuous capture across phase gaps.

One-loss selector is fixed before arming: SDK message8, row1 position3, exact
SENSOR flow/socket/ISN, parity excluded. Require both routes in actual row5..8,
initialcounter0/final exactly1drop, selected source absent at both taps while
parity is present, explicit accepted Session decision and exact typed repair before
classifier removal. Fail if actual admission changes that row population rather
than moving the selector. Target SDK bracket follows installation; incoming
parity <= decision end <= typed observation < hook removal.

Preserve cohort progress and original per-case verdicts, provenance, selected
metadata/hash/clock/qdisc/capture/fault/child-shutdown/lifecycle logs and tests.
Raw PCAP/native prefixes, journals and detailed resource/endpoint samples remain
local with hashes; no credentials or inspect/environment dumps archived. Seven
runtime hashes before/after and cleanup of all owned fixtures/passphrases required.
Previous SDK70/ROS41 remain the last full validations, not new executions. Host223
is current. Passing all runs would not complete full N3 durations/comparison,
30s faults, N4/M3, physical-age/security/resource/hardware or Intrinsic/M4 acceptance.
PR2 remains draft; any failure remains authoritative and stops this plan.
