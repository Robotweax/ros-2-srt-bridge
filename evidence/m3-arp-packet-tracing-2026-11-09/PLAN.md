# Packet lifecycle ARP tracing, no tuning

PR2 remains draft, M3 incomplete, Intrinsic/M4 untouched. No provider/runtime/
existing-observer rebuild or edits. No timeout, budget, rate, queue, neighbor,
retry, sysctl, offload or default changes. Preserve historical failures and all
negative preparations. Only fresh owned internal Docker networks and containers.

Preparation: inspect running kernel BTF and attach bounded no-op raw tracepoints
with BPF/PERFMON, network none. No tracefs mount, global trace configuration or
privileged container. Retain exact capability/source/compiler/kernel evidence.
Build a separate passive raw-tracepoint observer. Validate running BTF layouts
and argument types rather than infer ABI from a similarly versioned source tree.
Scope net_dev_queue creation to exact owned namespace/interface and all42bytes of
owned Ethernet/IPv4 ARP reply. Keep skb addresses solely as private bounded BPF
map keys; emit monotonic local IDs, never kernel addresses. Track qdisc enqueue,
dequeue (including bulk ambiguity), driver start, kfree reason and consume. End
tracking at driver start: later peer/bridge frees are outside source TX scope.
No claim physical transmission from driver start. Classifier drops before queue
are outside this observer. Clones/copies, map collisions, unexpected termination,
missing stages, loss/overflow, pending IDs and unavailable hooks remain explicit.

Freeze tested source plus8 runtime/2existing observer hashes/new binary hash
before live. No tests/builds/heavy analysis during capture. Once each, sequential:
N0 clean calibration then unchanged existing N5/2903 synthetic calibration. ARP
requests only between exact owned addresses/MACs provoke real kernel replies;
no userspace reply injection. Five requests without synthetic load, then twenty
at100ms spacing with bounded high-rate UDP load (fixture only), then five after
load/drain. N0 has no synthetic flood. The load is a measurement stimulus, not a
product setting. The standard N0/N5 definitions remain unchanged. Fresh dynamic
neighbors; no flush/ping/permanent entries. Readiness precedes stimulus; native
AF_PACKET+PCAP cross-check driver-start population, exact payload/routing scope,
zero observer/capture loss and unchanged root configs. Stop on integrity failure;
no repeat to obtain desired queue/drop counts. No production SRT/ROS outcome
claim from synthetic traffic. Explicit queue/drop evidence must use a single
lifecycle ID, not sampled counter subtraction. A kfree reason other than a
qualified qdisc drop is reported as its actual reason. Queue residence requires
valid enqueue/dequeue ordering; missing enqueue or batched dequeue stays censored.

Publish raw manifests, exact omissions, cleanup and source/hash checks. A loaded
SRT/ROS cohort requires a separate prospective plan after this calibration;
no tuning follows these results. SDK72/ROS41 are prior validation only.
