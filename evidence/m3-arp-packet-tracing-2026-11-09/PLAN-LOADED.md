# Loaded packet-level ARP cohort after qualified calibration

V1 failed zero matching (unsigned comparison bug), N5 not executed; retain it.
V2 frozen38f0af4 passes N0 all30 through driver, N5 kernel QDISC_DROP20/driver10.
All30 lifetimes percase, zero unresolved/loss/collision/pending, source and11
binaries fixed. Native/ARP-PCAP count30/10 replies respectively on both peers.
Survivors traverse enqueue/dequeue in microseconds: this does not calibrate long
ARP queue delay. Kernel BTF validates prototypes/layout/reasons. No tuning.

Integrate the calibrated passive tracer as default-off --arp-packet-trace,
requiring loaded ARP/requisite diagnostics, N0/N5 dynamic/no faults, <=480s.
Only added capability PERFMON on owned containers. New tracer built before live;
8 runtime/2existing observer binaries stay pinned. Both roles scope exact owned
ARP reply header/netns/ifindex, six hooks, <=600s/4096 outstanding IDs/1M events/
4MiB ring. Stop load, drain, detach tracer before closing native capture; retain
partial failures, no global tracefs or kernel tuning. No injected ARP/flood in
this loaded cohort; its previous512kbit/16 queue/128Kbit competitor/200/50Hz/
2s commands/5s budgets/5000ms idle/8s drain/default dynamic neighbors unchanged.

After tests/preflight/source freeze, exactly one N0/2903/15s then one
N5/2903/300s, stop first integrity/durable-completion failure, no retries.
Strict all-success also reported; added observer overhead prevents mitigation
claims. Preserve all prior failed/unknown intents and no replay/retroexpiry.

After closure/source verification, classify EVERY scoped source lifecycle using
actual kfree reason or driver-start, complete stage ordering, qdisc handle and
residence; retain bypass, bulk/copy/pending/otherfree ambiguity explicitly. Positive
N0 creation and exact driver-start/native source+peer reply population required.
Compare all adjacent positive reply counter steps wholly within source publication
and all >=1s CONTROL gaps/active loss windows. Report per-cookie created/terminal
membership and carry-in/out relative to each window; do not infer packet loss
from counter differences, absent taps or whole-interface root drops. Repeated
ARP headers have no nonce; native peer counts are aggregate, not per-ID matching.
Long queued ARP only if one ID has ordered enqueue/dequeue and matching handle;
explicit drop only for BTF QDISC_DROP, actual other reasons retained. No historic
causality claim, physical delivery guarantee or traffic prioritization change.

All raw hashed, public omissions explicit, owned namespaces/rules/credentials
removed. No tests/builds/heavy analysis while live. SDK72/ROS41 remain prior;
PR2 draft, M3 incomplete, Intrinsic/M4 untouched. Further tuning not authorized
by these measurements.
