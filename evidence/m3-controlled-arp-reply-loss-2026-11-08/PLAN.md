# Controlled kernel ARP reply loss, without tuning

PR2 draft; M3 incomplete; prior failed/UNKNOWN intents remain unchanged; Intrinsic/
M4 untouched. No dependency/enclosing-repository edit, SDK/ROS/native observer build,
production tuning, permanent neighbors, cache flush, sysctl, idle/budget/rate/queue/
profile-default change. This is synthetic UDP/kernel ARP qualification, not N5/
SRT/ROS reproduction or proof of a unique historical cause.

Use existing pinned image and8runtime+2observer hashes unchanged. First prepare a
zero-traffic owned-namespace schema/install/readback/removal check of a software-
only flower ARP reply selector. Record any preparation correction separately;
no host-interface tc, no active probe. Read-only tc help is preparation only.

Then freeze source/host guards before two slots once, sequentially, fresh owned
internal namespaces each: clean reply counter/PASS control, then reply DROP and
restoration. Both use identical N0 roots, dynamic initially ABSENT peer neighbor
entries, native-v2 ETH_P_ALL and immediate tcpdump 'arp or (ip and udp)' with
startup/drain/population gates,100ms read-only neighbor samples and exact labeled
UDP identities. No ARP warmup/ping/neighbor replace/flush. The only injected fault
is an owned robot egress rule matching operationREPLY, owned peer IPv4 and ARP/
Ethernet MAC identities. It uses a counted gact PIPE action followed by counted
PASS (clean) or DROP (fault): PIPE cannot terminate or bypass the later verdict.
Root options/identity remain identical before/after; no root impairment changes.

Send3 distinct1200-byte synthetic UDP payloads once from operator port10080 to
robot39781; do not resend on missing delivery. Keep independent receiver active.
A local robot controller is ready before the source and reads shared send brackets
on the proven common zero-offset VM clock. At first-send+1.15s and+1.25s read the
reply actions/root/neighbors; at+1.35s remove only the selected rule and verify its
absence. Require a positive stable counter population before removal, PIPE0drops,
verdict counts equal PIPE, PASS0drops or DROPcount=drops. Record true command/read
brackets; guaranteed active interval is install-end→remove-begin. Controls need
not run at exact nominal times; reject if restoration is later than2s after first
send or active interval does not cover1.25s after source. No traffic during final
rule-installation/ready barriers besides later explicitly started producer.

Fault must show kernel-generated reply eligibility at PIPE and actual DROP counts,
zero matching outgoing/incoming ARP replies and zero labeled UDP source/peer/app
observations during guaranteed fault interval. Native counts include reflected
local copies explicitly, never as peer replies. After rule removal, genuine reply
observed at both taps, initially queued original UDP identities delivered exactly
once without source resubmission, plus a separately labeled fresh control datagram.
Clean must show counted matching replies at both taps and all original deliveries
before observer removal. Do not equate attempted send/absence with nonexecution.
This causally tests the injected reply-loss path, not organic N5 drop reasons.

Stop on first readiness, timer, counter, population, hash, identity, cleanup or
selected behavioral failure; mark later slots NOT_EXECUTED, no case retry or extra
seed. Keep all failures. Before/after root/feature settings read-only, source/
observer/runtime fixed through cohort. No tests/builds/heavy analysis during live;
closed analysis after both cases, all PCAP/native counters/identities and raw hashes
verified. Preserve controller/receiver child status, complete bounded neighbor
streams and teardown. Remove owned rule/containers/network/credential only.

Archive selected metadata and exact raw/derived/local-only disposition. Host parser,
selector/action-chain, packet/reflection and phase/population/timing negative guards
before live; prior SDK72/ROS41 remain prior validation. No tuning follows merely
from this fixture; any N5 ARP pre-qdisc observation/mitigation needs a separate plan.


Preparation amendment before any traffic: the zero-traffic flower install is
unsupported (TC classifier not found), retained as failed preparation with cleanup.
Use the already-supported software u32 classifier instead: exact seven-word ARP
Ethernet/IPv4 payload matches operation2, SHA/SPA/THA/TPA at fixed network-header
offsets; native captures separately validate actual Ethernet source/destination
MACs. Preserve the same PIPE→PASS/DROP chain and all prospective phase gates.
A second zero-traffic u32 schema/readback/removal check is separate preparation;
no live case or source packet was repeated by this compatibility correction.

Second preparation installs u32 successfully but strict selector validation rejects
iproute2 JSON because it serializes repeated 'match' object keys; ordinary JSON
loading retains only the last word. Preserve all seven match words with a guarded
object-pairs parser, retaining the raw failed readback and cleanup. Final separate
zero-traffic preparation verifies the normalized exact selector and removal before
freezing live source. No traffic/case retry is hidden by this parser correction.

Per-case integrity/behavioral gates run only after every child/capture for that
case has stopped, before advancing to the next case; consolidated provenance is
archived after the cohort. No closed analysis overlaps another live case. Final
zero-traffic u32 preparation passes exact seven-word selector/PIPE→DROP readback
and removal. Host316 passes before live; all runtime/observer binaries unchanged.
