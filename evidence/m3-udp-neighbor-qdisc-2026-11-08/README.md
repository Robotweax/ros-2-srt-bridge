# UDP, neighbor and qdisc isolation without tuning

Two different CONTROL stall stages are observed: provider growth before the
software PASS counter, associated with unresolved neighbor samples/ARP; and
selected PASS growth without source AF_PACKET observations, associated with root
queue pressure. Not every quiet interval is a send failure. No tuning is applied.

The new observer cohort passes N0/2903 8/8 and N5/2903 126/126, with0/24 skipped
slots, zero expired/unresolved intents and both command gates PASS. Cohort exit0,
exactly one run per slot. There are no active context/link-loss events. The earlier
session failure does not recur under the added observer work; this is not a fix
or resolution of prior intents98/12. PR2 draft, M3 incomplete, Intrinsic/M4 untouched.

## Stage observations

All primary >=1s adjacent CONTROL source gaps and all active loss windows are
selected prospectively. There are4 gaps in new N5 and zero loss windows; new N0
has neither. Strict provider/wire socket/clock/frame/population/hash guards apply.
The source software PASS selector covers CONTROL UDP peer/port, not authenticated
socket identities. Root counters cover the whole interface and have different
non-atomic read brackets; mirrored child drops are never added.

| Sender, gap | Provider DATA / retransmit increments | Selected PASS delta | Root drop delta / peak qlen | Sampled sender neighbor states | Interpretation |
|---|---:|---:|---:|---|---|
| operator,1.528432875s |91 /75|0|0 /0|PROBE4, INCOMPLETE11|Before selected PASS, with neighbor resolution lead|
| robot,1.332005584s |126 /120|30|1390 /16|PROBE2, INCOMPLETE10, REACHABLE1|After selected PASS contribution; mixed neighbor/queue observations|
| operator,1.001725500s |0 /0|0|0 /0|REACHABLE10|No selected send activity: quiet is not loss proof|
| robot,1.349117001s |24 /24|20|9491 /16|DELAY14|After selected PASS contribution, root queue pressure; no ARP inside gap|

All four windows have stable mapped provider identities and zero selected source
CONTROL hook observations during the gap. TC pairs wholly inside these windows
are7/6/4/5 respectively in the table order. Root deltas and queue peaks cannot
identify which specific CONTROL packets dropped versus waited, nor exclude other
kernel stages after the classifier. Prior independent software-PASS/root-loss
placement controls provide context only within their recorded synthetic fixture;
current installation is software-only, zero PASS drops and root options preserved.
N0 has positive selected PASS increments240 operator /250 robot and full captures.

A posthoc stricter witness avoids comparing mismatched sample spans in the first
operator gap. Between filter-read brackets[85066198080,86446045581]ns, cumulative
reported PASS packets/bytes remain flat. Twelve provider read pairs wholly inside
that interval grow75 DATA,59 retransmissions and20 ACK, with zero selected source
hook observations in the enclosing gap. This localizes the discrepancy before
selected PASS execution, rather than explaining it only with root qdisc drops.
The counter-read contract is cumulative; this is still aggregate observation, not
an exact per-packet kernel trace. [Common-interval evidence](analysis/srt-N5-2903-common-interval.json).

During that gap the operator emits two owned-MAC ARP requests, also sees two
reflected local request copies (not peer replies), and receives one genuine peer
reply. The robot sees the two requests and one outgoing reply. The operator's
peer reply precedes resumed old-flow source observation by53.541us, on the same
qualified kernel-monotonic clock. This and PROBE/INCOMPLETE samples support
neighbor-resolution involvement in the pre-PASS stall; ARP has no request nonce,
packet presence is not authenticated neighbor acceptance, and sampled reads do
not establish exact transition times or a unique kernel branch.

The robot's last1.349s gap has20 selected PASS executions, root drop growth9491,
peak qlen16/backlog3768bytes, sampled DELAY states and no ARP in either tap window.
It demonstrates a distinct post-PASS/root-pressure association; attributing all
gaps to neighbor resolution would be incorrect. The mixed1.332s robot gap retains
both INCOMPLETE samples and PASS/root growth without forcing a single explanation.
The quiet1.002s operator gap has no provider increments and is not a loss case.
Full reads, edge-crossing/before/after neighbor samples, ARP identities and all
classifications: [path analysis](analysis/srt-N5-2903-path.json).

## Earlier failed cohort: ARP reanalysis only

The prior visibility cohort's raw native recorder already used ETH_P_ALL; no
recorder change or replacement capture was needed. Hash-guarded ARP reanalysis
covers its4 gaps and2 loss windows. During its5.0046s operator→robot quiet-to-loss
window, there are five outgoing operator requests, five reflected local copies,
five requests at robot and no peer reply inside the window. The enclosing5.2636s
source gap contains six requests and one later reply. That reply is followed by
old-flow egress5.416us later. This is consistent with the new pre-PASS evidence,
but the prior cohort had no sampled neighbor/PASS/root history; do not backfill
those states or claim the exact historical cause is proved.
[Original hash-guarded ARP associations](prior-visibility-arp.json).

## Telemetry and limits

New N5 source75033/SDK-accepted71310 by conservation/decoded9708/observer8640;
accept-to-receiver gap61602, receiver rejected1067 (unknown-age1042/stale0),
publication rejected1. All six conservation residuals are zero; sources~200/50Hz.
Sensor availability remains unqualified. N0 source3778/observer3658 has zero
accept-to-receiver gap. Closed UDP tuple/payload-hash multisets match both ways:
74749 robot→operator and66131 operator→robot records. Whole-run root drops are
1885392 robot /186 operator, not individual flow/window losses. Independent
SENSOR provider lifetime/partial-read reports remain separate from application
windows and do not expose exact insertion/retirement reasons.
[Telemetry](analysis/srt-N5-2903-telemetry.json), [SENSOR counters](analysis/srt-N5-2903-sensor.json).

No profile, producer rate, competitor, original5s command budget,5000ms peer idle,
queue, wire, journal, clock, replay or neighbor-default setting changes. Dynamic
neighbors remain dynamic: no replace/flush/permanent entry or active probe. The
existing neighbor poller adds100ms netlink reads; the CONTROL PASS/root observer
adds200ms queries and PASS execution. These perturb host work and may affect
recurrence, so126/126 cannot be treated as a mitigation or performance comparison.
A longer idle timeout or budget would obscure the stage evidence, not isolate it.

## Validation and provenance

Plan68d7297 precedes implementation/live sourceb9aaf03415389e98ffcf1d13d80f2e93a26ffae5.
Host301 passes before live. One first fixture test fails on macOS /var versus
resolved /private/var alias before reaching the intended hash-mismatch gate;
output retained, fixture root corrected, no live run at that point. All8 runtime
and2 native observer hashes equal the preceding visibility cohort and stay fixed
across/post-live. Provider source/archive unchanged; no SDK/ROS/observer rebuild.
SDK72/ROS41 are prior validation, not newly executed suites this turn.

After closure and frozen source/archive verification, posthoc common-interval
helper4c1e113 adds5 boundary/identity/unavailable/regression guards; host306 PASS.
Its source and measurement provenance are separate; no runtime change or rerun.
No builds/tests/heavy analysis overlap live. Native/PCAP/provider/neighbor/TC
populations pass, zero trace loss; observer rule removed and owned namespaces/
credentials cleaned. Raw originals retained locally with hashes; public selections
omit both repetitive provider streams, full sample streams, binaries and journals.
[Public disposition](public-disposition.json) lists every raw file as verbatim,
derived selection or local-only omission; [selection details](public-selection.json)
record exact transformed fields/counts and raw/derived hashes. Validation logs and
posthoc scripts are retained. Original failure/UNKNOWN verdicts remain unchanged.

Next isolate ARP reply generation versus queuing/drop using a separately qualified
ARP pre-qdisc observation and controlled reply-loss fixture, alongside a separate
known CONTROL root-loss control. Preserve dynamic defaults and original budgets;
no mitigation yet. Exact per-packet kernel-drop reason and the unique original
session-failure cause remain open. Full N3/N5, loaded default ROS/DDS discovery,
cross-host clock/security/resource/hardware and superiority gates remain open.
