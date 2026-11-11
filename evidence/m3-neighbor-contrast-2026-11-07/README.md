# Sampled neighbor state and L2 contrast — 7 November 2026

The ordered N5 pair supports neighbor resolution as a contributor to the
observed dynamic-fixture gaps, but **permanent neighbors do not remove all
CONTROL gaps**. The historical failed capture also contains an ARP reply just
before CONTROL resumes. This strengthens a hypothesis, not a unique kernel
failure attribution, historical fix or M3 acceptance.

## Prospective executions

The [plan](diagnostic-plan.json) was committed before preflight. The N0 permanent-
neighbor smoke ran once for 15 s, then dynamic N5 and permanent-neighbor N5 each
ran once for 300 s, seed 1701, in that order. No failed run was retried or replaced.
Both N5 cases use identical observer methods, image, SDK/ROS binaries, shaping,
competitor settings and source commit `035100b`; preflight used `41e6f60`.
Eight runtime hashes match before/after and all measured source hashes match
those frozen commits. Both N5 cases report the same VM boot ID. Order and
nondeterministic scheduling remain confounds; this is one descriptive pair.

The default remains dynamic. Permanent mode explicitly installs actual owned
peer MACs only in disposable containers and verifies state/MAC through every
sample and final readback. Host networking and SRT settings are unchanged.
Both observers use read-only peer-scoped `ip neigh show`, with returned eth0,
identity and header validation; no active neighbor probe is requested.

| Execution | Successes/effects | Unresolved | Skipped slots | Qualifying source gaps |
| --- | ---: | ---: | ---: | ---: |
| N0 preflight, permanent | 8 | 0 | 0 | 0 |
| N5 dynamic | 130 | 0 | 20 | 3 |
| N5 permanent candidate | 132 | 0 | 18 | 2 |

All original development manifests are `passed`; no active CONTROL loss/close
occurred. These verdicts do not mean full N5 qualification. Closed immutable
journals match all confirmed results, with one SDK handoff per successful intent
and receiver dispatch timestamps before conservative receiver start deadlines.
Sender and receiver deadlines are not assumed equal. Old UNKNOWNs remain intact.

## All preselected gaps and state observations

The unchanged primary analyzer retains every fully observed adjacent old CONTROL
source-flow gap >=1 s in the source window. Counters use adjacent available
same-identity reads wholly inside the interval. Neighbor rows wholly inside each
gap are separated from edge-crossing reads and bracketing context. These are
sample counts, not exact transition times or continuous state durations.

| Mode / sender | Gap seconds | DATA-sent delta (retransmissions already included) | Sender samples wholly inside gap |
| --- | ---: | ---: | --- |
| dynamic / operator | 3.232864418 | 224 (207 retransmissions) | PROBE 1, INCOMPLETE 31 |
| dynamic / robot | 1.141203625 | 45 (40 retransmissions) | PROBE 1, INCOMPLETE 10 |
| dynamic / robot | 1.058229125 | 77 (69 retransmissions) | INCOMPLETE 10 |
| permanent / operator | 1.000092084 | 0 | PERMANENT 10 |
| permanent / robot | 1.314880584 | 17 (16 retransmissions) | PERMANENT 13 |

All three dynamic gaps have increasing selected send counters and INCOMPLETE
samples at the sender. The permanent operator interval has flat selected
counters, which do not prove UDP absence. Its robot interval still has increasing
DATA counters without an old-flow egress observation despite verified PERMANENT
state/MAC. Thus neighbor resolution cannot explain every observed gap. Selected
counters omit keepalive/handshake/ACKACK, and routing IDs do not establish
authenticated receipt or physical delivery. Kernel queues/drop stages were not
observed; neither qdisc nor socket handling is uniquely assigned a cause.

Permanent state/MAC is verified across all **3167 operator / 3170 robot** samples
and final readbacks, not just the gap samples. Dynamic logs retain **3180/3180**
rows. Source-window dynamic INCOMPLETE counts are **33 operator / 20 robot**;
startup state counts are retained separately. Observer read spans reach
**44.683084 ms**, sample-start gaps **111.184208 ms** across the N5 pair. Polling
adds subprocess/netlink work and misses states between reads; no zero-overhead
or observer-free equivalence is claimed.

## Retrospective historical ARP association

An explicitly post-hoc check of the old failed independent-trace run
`.local/m3/20261106T181823876229Z` uses the same raw hashes as its previously
qualified flow archive. Its old operator-flow source gap is **5.127369086 s**,
contains **six outgoing ARP requests**, and the operator observes an ARP reply
**5.250 microseconds before source CONTROL resumes**. That reply is
**119.106083 ms after the recorded robot session-change marker**.

This is consistent with neighbor-resolution involvement in that incident. No
historical neighbor-table samples or provider counters exist, and the exact
kernel branch/queue/drop chain remains unobserved. No historical verdict,
UNKNOWN, result, expiry, replay policy or nonexecution conclusion is changed.
See [selection/provenance](historical-gap-selection.json) and
[ARP observations](historical-gap-arp.json). Non-outgoing duplicate requests
remain in the artifact and are not counted as extra outgoing requests/replies.

## Completeness, testing and limits

Every case has complete neighbor/provider/command/native diagnostics, zero
provider/trace drops or budget exhaustion and zero native reservation/copy
failures. PCAP populations reconcile with zero kernel drops:

| Mode | PCAP records per endpoint | Native operator / robot | Source / published / observed sensors |
| --- | ---: | ---: | --- |
| preflight | 8121 | 8122 / 8125 | 3773 / 3665 / 3664 |
| dynamic N5 | 125814 | 125902 / 125900 | 75023 / 19805 / 19805 |
| permanent N5 | 108233 | 108254 / 108257 | 75036 / 27570 / 27565 |

Capture populations differ and are not equated. All conservation balances are
zero, but sensor deficits remain large. Realtime PCAP windows remain withheld by
clock qualification. This pair does not establish transport superiority,
physical realtime/delivery, security parity or isolated resource cost.

Host tests: **134 before preflight, 136 before the N5 slots, 138 finally**.
Syntax checks pass. After measurement, output reuse was hardened so an existing
sample/status/ready artifact is refused without mutation; explicit budget-
exhaustion regression coverage was added. This error-path-only change was not
live reexecuted and does not alter the measured successful sampling path.
[Source provenance](source-provenance.json) distinguishes measured commits from
that subsequent fix. No fresh SDK/ROS/M2 rerun is claimed for these tools-only
changes; the eight runtime binaries remain unchanged from their earlier tests.

[Comparison](comparison.json) links all original case manifests, state samples,
MAC/readbacks, selected logs, provider/flow/ARP/neighbor analyses, journal audits,
raw hashes and tests. Neighbor rows are bounded metadata; raw packet payloads,
prefixes, journals, clocks and resource samples remain local. No credentials or
inspect/environment dumps are published.

Next: distinguish the residual permanent-neighbor gap from sampled neighbor
resolution and localize the pre-tap queue/drop stage before changing any default
fixture. A permanent-neighbor result remains a diagnostic candidate, not a new
baseline or historical reset fix. Full N5/M3, N3/N4/default DDS N5 and clock/age/
security/resource gates remain open. PR #2 stays draft; Intrinsic/M4 untouched.
