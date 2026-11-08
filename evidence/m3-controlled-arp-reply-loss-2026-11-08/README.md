# Controlled kernel ARP reply loss and restoration

The scoped V2 clean control and injected reply-loss/restoration cases both pass.
Two kernel-generated peer replies reach the counted software PIPE action and are
counted as DROP, while no matching replies or original UDP identities appear at
the taps during the fault. After removal, a genuine peer reply and all three
original UDP identities appear exactly once, without a source resend. A distinct
fresh control packet also succeeds. Root/default settings remain unchanged.

This causally qualifies the **injected synthetic ARP reply-loss path**: absence
of an outgoing reply at a tap can mean an eligible generated reply was dropped
before observation. It does not prove the unique organic N5 root-drop/neighbor
cause, repair prior command uncertainty, or qualify ROS/SRT/M3. PR2 stays draft;
M3 incomplete, Intrinsic/M4 untouched.

## Accepted V2 cases

| Fresh namespace case | Counted eligible replies | Counted drops | Genuine replies during active interval, source/peer | Original UDP delivered once | Fresh control |
|---|---:|---:|---:|---:|---:|
| clean PIPE→PASS |1|0|1 /1|3|1|
| fault PIPE→DROP, then removal |2|2|0 /0|3 after restoration|1|

Both cases start with ABSENT dynamic peer entries. No ping, neighbor replace,
flush, permanent entry, sysctl, queue, rate, idle or budget tuning is used. The
same N0 roots are created in fresh owned internal namespaces and stay unchanged
through each case, with zero root drop increments. The only fault is an owned
robot egress ARP-reply selector, removed within the original fixed timing gate.

The software-only u32 selector matches the exact seven words of the Ethernet/
IPv4 ARP payload: operation2, both owned IPv4 addresses and both ARP MACs. Native
frames separately validate the owned Ethernet MACs/direction. A counted gact PIPE
precedes PASS or DROP in the same rule: PIPE does not short-circuit the following
verdict. Only ordinary UDP producers/receiver run; no userspace ARP sender, SRT/
ROS peer or N5 competitor is active. The observed eligible replies are kernel
output in the owned responder namespace.

The Linux controller is ready before the producer. After the first-send bracket,
it snapshots the actions/root/neighbors at nominal1.15/1.25s, requires a positive
stable PIPE/verdict population, and removes the selected rule at nominal1.35s.
Actual fault removal starts1.350737001s and completes1.368607751s after the first
send. The common zero-offset VM clock brackets installation/removal; the guaranteed
active interval is180337595997..182166899415ns. No matching outgoing/incoming peer
reply or labeled original UDP observation occurs inside that interval. Two eligible
replies total84bytes at PIPE, DROP packets2/drops2; both action snapshots agree.

The original three sendto calls complete once each while the rule is active.
After removal, the next genuine reply is observed at both endpoints; first original
UDP source-hook observation is2.063324751s after the first send,4.083us after the
operator's peer-reply hook observation. All three original identities then reach
the receiver exactly once. These are local synthetic hook associations, not
physical-wire or general latency bounds. No application or provider retry is used.
The fresh packet uses a different case label (1002), not a resend of the original
case2/sequence0..2 identities.

The operator has20 INCOMPLETE neighbor samples and later4 REACHABLE samples in the
fault case; the robot remains sampled STALE after learning the caller. Snapshot
states do not establish exact transition instants or authenticated ARP acceptance.
Control has no INCOMPLETE samples. All child controllers/receivers exit0 without
forced kill, selected rules are absent afterward, and all owned namespaces and
credentials are removed. Case details: [clean](qualified-v2/clean-pass/result.json),
[fault and recovery](qualified-v2/reply-drop-restore/result.json).

## Capture scope and retained first failure

V1 source38a6f0a executes clean control once, then stops FAILED on full selected
ARP/native-PCAP identity equality. Its reply-loss slot stays NOT_EXECUTED. The
extra observed PCAP packet is gratuitous ARP with equal sender/target IPv4,
not the cross-peer exchange. Recorders have different startup spans; no unique
reason for the one-recorder presence is inferred or repaired using realtime PCAP.
Its actual counters, known UDP deliveries and complete individual populations do
not rescue that original broader identity gate. [Failed V1 manifest](failed-v1/execution.json).

[PLAN-V2.md](PLAN-V2.md) prospectively freezes a new narrower comparison before new
live cases: ARP operation1/2 between the owned peer IPs and all labeled UDP. Every
native/file/filter/kernel population gate stays strict. Other gratuitous/unknown
ARP records are preserved in per-recorder background identity tables and equality
flags, never silently deleted or used as peer replies. V2 uses new fresh namespaces
and does not reclassify V1 or fill its unexecuted slot. Both new slots run once;
there is no repeat until a favorable result under unchanged criteria.

V2 PCAP captured/file/filter counts reconcile10/10/10 operator and9/9/9 robot for
clean,14/14/14 and11/11/11 for fault, all zero kernel drops. Native v2 seen/submitted/
file counts also reconcile, zero reserve/copy loss, qualified clock/interface/frame
coverage. Owned-peer ARP/UDP identity multisets match between PCAP/native; background
identity tables also happen to match in V2 but are not the accepted peer-scope gate.
Reflected local broadcasts remain separate from genuine peer replies. Original
payload hashes match full PCAP payloads and receiver bytes. No PCAP realtime timing
authority or physical-frame delivery qualification is claimed.

## Preparation, validation and provenance

Plan20d8a38 precedes preparation/implementation. A zero-traffic flower install is
unsupported by the kernel, retained FAILED. A separate zero-traffic u32 install
works but its first strict readback fails because iproute2 emits repeated JSON
'match' keys and ordinary loading keeps only the last word. The corrected guarded
object-pairs parser retains all seven words and rejects unexpected duplicate keys.
Final separate zero-traffic exact-selector/action-chain/removal preparation passes.
No probe was sent in those three preparation namespaces; all are removed.
[Preparation outcomes](preparation/summary.json), raw readbacks and commands remain
separate from traffic measurements. No module installation or kernel tuning.

Host316 passes before V1; host317 before V2. Negative guards cover opcode/selector
completeness, PIPE versus terminal PASS, offload/aliased actions, duplicate JSON
keys, counter mismatch, active-window leakage, wrong reflected reply, duplicate or
changed UDP, removal deadline, truncation and peer/background scope. No SDK/ROS/
native-recorder rebuild: prior SDK72/ROS41 are prior validation. All8 runtime and2
observer hashes stay equal to the previous cohort and fixed across both revisions;
provider source/archive unchanged. No tests/builds/heavy analysis overlap live.
Frozen accepted source770632ac9c9fe4b16572bf4c7bb022cad9f2ccba; V1 source and failure
are retained before the scope revision.

All raw artifacts across preparation, failed V1 and accepted V2 remain local with
hashes. JSON/counter/read-bracket/neighbor streams and selected logs are public;
packet binaries/other raw logs stay local. [Public disposition](public-disposition.json)
identifies each verbatim/derived/local-only file; network metadata selections keep
explicit fields with raw/derived hashes. No credentials or full inspect/environment
dumps are published. A read-only console summary used a wrong footer key once;
the corrected display did not change any measurement or repeat a live case.

Next use this qualified ARP pre-tap counter in a separately frozen loaded N5
observation to distinguish reply eligibility from queuing/drop under actual load.
The controlled DROP is before the tested root/tap; root-pressure attribution in
organic N5 remains unproved. Preserve dynamic defaults and original command budgets/
idle timeouts. No tuning or retrospective resolution follows; all other fullM3,
loaded DDS discovery, cross-host clock/security/resource/hardware and superiority
gates remain open.
