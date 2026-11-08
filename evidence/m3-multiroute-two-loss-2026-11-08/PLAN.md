# Sustained mixed-route two-loss: three conditional single executions

Freeze this source/plan after215 host tests pass. Run in this exact order, once
each; proceed only after every gate of the preceding run passes. Stop at the
first failure, retaining its original verdict. No retries or selector changes:

1. `python3 tools/m3_ros_multiroute.py --output .local/m3-multiroute-two-loss/1701 --capture --losses 2 --seed 1701`
2. `python3 tools/m3_ros_multiroute.py --output .local/m3-multiroute-two-loss/2903 --capture --losses 2 --seed 2903`
3. `python3 tools/m3_ros_multiroute.py --output .local/m3-multiroute-two-loss/4211 --capture --losses 2 --seed 4211`

Three fresh owned Docker fixtures, pinned existing Linux amd64 image and seven
runtime artifacts, phase-preserving C++ IMU200Hz/joints50Hz source for one nominal
ten-second window per run. Source/sample diagnostics enabled, same fixed record
budgets. Prior captured baseline/one-loss runs remain separate. N0 underlying
qdisc base/base+1 readback uses the declared seed; it has zero random impairment,
so these are independent-start repeatability checks, not random-loss seed
coverage or causal performance comparisons. Permanent neighbors remain an explicit
fixture intervention. Separate ROS domains/LOCALHOST, common boot/zero-time-
namespace proof; no COMMAND workload or production/runtime changes.

Before arming, install exactly two rules selecting SENSOR source SDK messages7/8,
row1 positions2/3, using the captured handshake/binding ISN, tuple and socket.
Initial action counters must be0; final counters exactly one packet/drop per rule.
Exclude message-zero parity. Remove/read back only the owned hook after both result
barriers, preserving VM install/remove brackets. Actual complete SDK row5..8 must
exist; selected messages7/8 must span both route IDs. Fail if admission/replacement
changes that actual row, instead of adapting the selector.

All earlier source/hash/admission/SDK/context/accounting and capture gates stay
mandatory: measured fenced rate within1% for each route, skipped slots explicit,
complete zero-loss source/sample traces, exact hashes/stamps/order for every typed
observation, stable empty checkpoints, six balances0 and nonnegative stage terms,
Clock/QoS/session/owner/generations/isolation and accepted publication age<=250ms.
BUSY, upstream DDS and replacements are explicit, not transport successes. No SDK
send errors. Aggregate queue counters do not assign a precise stage to each ID.

Identity and measurement captures remain two distinct closed phases. Identity
requires one binding and agreeing handshake origin at both taps. Opt-in filtered
packet-socket recorder has final BPF before bind, initial kernel count0, native
observers first/last, full source-window coverage, exact SDK/native/full-PCAP
multisets, stable equal file/dispatch/kernel populations, zero drops/truncation/
exhaustion, verified size/hash and unchanged interface features. Expected source
keys exclude only7/8; every complete four-source parity row remains. Do not invent
parity for a partial final row. Realtime PCAP timestamps are not age authority;
native monotonic observations are skb, not physical-wire timestamps.

Required two-loss result: no decoded receiver decision for messages7/8, exactly
those two SDK messages missing from receiver decisions at the drained cutoff,
all other decoded decisions accepted, gap metric exactly2 and no selected typed
observation. Selected row parity must be present at both taps. Its incoming
monotonic timestamp must precede the receiver's stable cutoff, which precedes
classifier removal. Each selected source's SDK begin follows both rule installs;
original source origin precedes parity. Both routes must subsequently show fresh
typed observations before cutoff. Keep selected source counters/hashes/SDK indices
explicit. These are missing identities at a finite drained cutoff, not a generic
irrecoverable-loss counter, internal expiry event, permanent absence claim or
proof of nonexecution. Earlier successful one-loss repair remains independent.

Preserve frozen plan, original results/provenance, seven hashes before/after,
source/sample metadata and typed hashes/metrics, selected capture/lifecycle/fault/
clock/qdisc status, tests and local raw-artifact hashes. Do not archive credentials,
full inspect/environment dumps, raw PCAP/native prefixes, journals or detailed
resource samples. Remove all owned fixtures and passphrases. Python-only extension:
last full SDK70 /ROS41 validations remain unchanged, not rerun. This does not
complete baseline/one-loss repetitions, long-window N3, N4, M3, physical-age,
security/resource parity or Intrinsic/M4.
