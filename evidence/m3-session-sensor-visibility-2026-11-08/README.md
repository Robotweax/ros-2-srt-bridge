# Seed2903 session failure and SENSOR provider visibility

The instrumented failure **recurs**, with11/12 successful commands,138 skipped
slots and unresolved intent12. Both strict all-success and success-or-qualified-
durable-expiry gates FAIL; cohort exit1. N0/2903 passes8/8, zero skips/unresolved.
Zero live verified expiries. Original prior2903 intent98 remains unresolved; no
retry, replay, retrospective expiry or mitigation. PR2 draft, M3 incomplete,
Intrinsic/M4 untouched.

## CONTROL failure localization

Read-only analysis of the original2903 run confirms that after intent98's SDK
handoff and before robot CONTROL loss, fully-contained sender samples grow by413
DATA/406 retransmissions, while robot received DATA grows by0. The original lacks
kernel-monotonic captures; this cannot uniquely locate its packet gap. Original
hash-guarded evidence: [original-2903-analysis.json](analysis/original-2903-analysis.json).

The new cohort adds passive native-v2 capture and an independent SENSOR provider
stream, changing observation workload. It is a separate reproduction of the
failure class, not proof of the original run's exact cause. New intent12 has one
SDK handoff, no receiver record or original COMMAND admission/defer/expiry event,
and remains senderstate8/reason2/revision0. Its original5s budget is unchanged.

| Matched old CONTROL flow, operator→robot | Observation |
|---|---|
| Last robot hook observation |362832902456ns VM monotonic|
| Robot CONTROL loss |367837546083ns|
| Quiet to loss |5004643627ns =5.004643627s|
| Actual peer idle timeout readback |5000ms|
| Fully-contained same-identity provider read pairs |47|
| Sender DATA / retransmission increments during quiet |309 /292|
| Sender ACK / NAK increments during quiet |42 /1|
| Old-flow observations during quiet, source / peer |0 /0|
| Full adjacent source gap bracketing the event |5.263612877s|

The same local owner/session, generation, sender fd and receiver wire socket ID
are mapped by strict baseline/reverse-flow guards. Native capture covers the
analysis interval with complete populations, zero reserve/copy losses, v2 frame
metadata and common zero-offset VM time namespaces. The pinned provider increments
DATA-sent after full successful UDP send completion; kernel acceptance is not
physical egress/delivery. Thus this new event is localized between sender send
completion and the observed source hook, with a silence duration consistent with
peer-idle detection. It is not evidence of a bridge clock-admission rejection.

Operator records link loss15.736125ms after robot loss, with a matched incoming
old-flow shutdown observation84.958us before its loss event. The existing analyzer
withholds that second provider mapping because session association has already
changed; do not label it an independently proved idle interval. All4 qualifying
>=1s adjacent source gaps and both loss windows remain in
[CONTROL analysis](analysis/srt-N5-2903-control.json), including withheld mapping.

The sender before-close snapshot is available while state6/BROKEN. Availability
is not connected health. A subsequent no-socket read ends at367960249625ns; four
DATA and two ACK old-flow datagrams appear later at source and peer hooks, first
at368096489375ns. Before-close end is not exact close-return timing, and this does
not distinguish provider close-drain, UDP/kernel queuing, neighbor resolution or
qdisc scheduling. It does demonstrate delayed old-flow observations rather than
new SDK COMMAND handoffs. There is no encrypted command-to-packet mapping and no
execution/negative-outcome authority from these packets.
[Late-egress detail and original command event](analysis/late-egress.json).

All closed UDP tuple/payload-hash multisets match both ways:84403 robot→operator
and73973 operator→robot records. Root drop deltas are2216798 robot /164 operator;
child drops mirror root and are never summed. Whole-run counters cannot allocate
drops to this flow/window or alone explain all309 successful UDP submissions.
The next causal target is the sender's local UDP/neighbor/qdisc path, not a longer
command budget or a larger idle timeout. A named kernel/provider cause is still
unproved.

## Added SENSOR visibility

Separate default-off `--sensor-provider-diagnostics` uses the unchanged pinned
srt_bstats API and a separate bounded SPSC stream:128 rows,75000-record limit,
100ms nominal cadence, explicit footer/loss/exhaustion/schema/channel gates and
before-close snapshots. It carries SENSOR owner/session/generation/fd/read brackets,
state/availability, cumulative DATA/unique/loss/drop/undecrypt/FEC counters and
buffer/flow/flight gauges. Existing CONTROL CLI/stream remains compatible.
See [field semantics and unavailable dimensions](PROVIDER-SURFACE.md).

| New N5 source window | Count |
|---|---:|
| Source produced / SDK accepted by conservation |75036 /70889|
| Receiver decoded SAMPLE / observer |8265 /7704|
| Accept-to-receiver gap |62624|
| Receiver rejected / unknown-age / stale |559 /530 /0|
| Other publication rejection |2|

Source remains~200/50Hz and all six conservation residuals are zero. No sensor,
full N5 or M3 acceptance follows. N0 source3774/observer3652 has zero accept-to-
receiver gap/rejection; its remaining local losses stay explicit.

The new logical session after CONTROL reconnection exposes a sharper provider
acceptance distinction for SENSOR destination socket54013376:

| Whole closed connection/tap population | Count |
|---|---:|
| Distinct source DATA sequences/messages at operator tap |20471|
| Source DATA retransmission bit set |0|
| Provider lifetime received DATA / filter extra |20832 /361|
| Provider lifetime unique received, including accepted FEC supply |5421|
| Provider FEC supply candidates / filter loss |30 /0|
| Provider aggregate receiver drop / undecrypt |8272 /0|
| Corresponding robot provider unique sent / sender drop |63551 /50210|

For the preceding active SENSOR connection, unique received is2846. These two
active receiver lifetimes total8267 unique accepts, close to8265 source-window
SAMPLE decodes, with bind/control and boundary populations kept distinct. The
20471-versus5421 distinction, with distinct source sequences and no retransmission
flag, narrows investigation toward provider receive acceptance/window handling,
not only bridge freshness rejection or repeated source packets. Pinned source
sets unique acceptance from in-order/out-of-order insertion and accepted FEC
supply. It does not export which individual older-window/beyond-window/occupied-
slot/retirement decision occurred. Counts are not a decrypted per-sequence SAMPLE
association or a unique SDK defect proof.

Lifetime totals above are separate from fully-contained adjacent-read increments;
[visibility analysis](analysis/srt-N5-2903-sensor.json) retains both, all connection
identities/session labels, actual brackets, unavailable records, saturation flags
and smoothed gauge ranges. No interpolation across unavailable reads, resets or
source-window boundaries. Aggregate drop/unique/filter/undecrypt counters overlap;
never sum/subtract them as exclusive path losses. Zero undecrypt/filter-loss does
not establish zero packet, window or retirement loss.

Whole-capture SENSOR DROP_REQUEST36854 and large root drops retain feedback/
retirement pressure as a lead. Exact applied retirement, receive insertion reason,
provider application-delivery and terminal-break reason remain unavailable through
the pinned API. Dependency source is read-only and unchanged; source contracts and
hashes are in [provider-source.json](analysis/provider-source.json).

## Validation and provenance

Plan830e427 precedes implementation2810996. Its first full SDK run passes70/72
but the two new native fixtures incorrectly equate available statistics with a
connected state. The failed output is retained; no install/ROS/live followed that
failure. Fixture correction and analysis sourcea20f1ce passes full SDK72/72 and
ROS41/41; host296 passes. Final driver/source03ffa03 is frozen before live, with
Python-only driver additions after the binary build. IPv4/IPv6 native guards prove
independent CONTROL/SENSOR channels, positive unique DATA counts and close samples;
parser guards cover unavailable/reset/gap/saturation/schema/channel/population.

Three runtime artifacts change for the observation surface: bridge_node,
endpoint.a and transport.a. All8 installed hashes and two native-observer hashes
are fixed across/after live; provider archive/source unchanged. No behavior tuning,
DDS profile/default, wire/journal/clock/budget/replay change. No builds/tests/heavy
analysis overlap live. Owned namespaces and credential files removed. All original
raw files rehashed after closed analyses; public selected logs omit both repetitive
provider streams, keeping their footers; selected JSON omits record/delta arrays.
Exact omissions/raw and derived hashes: [public-selection.json](public-selection.json).
Original captures/journals/provider/resource traces stay local, hash-listed.

Closed analyses use frozen tools; the late-egress evidence script is explicitly
posthoc. One ad hoc import SyntaxError is recorded as a failed preparation with no
measurement output; corrected script/output are retained, no live repetition.
Original failed cohort verdicts/uncertainties remain unchanged.

Next separately freeze the existing bounded neighbor and CONTROL qdisc observers
with monotonic capture and ARP/neighbor eligibility evidence, preserving dynamic
neighbors and original budgets. Distinguish UDP enqueue/neighbor resolution from
root/child scheduling before any mitigation. Separately propose upstream reason-
specific SENSOR insertion/retirement counters through a reviewed supported API;
never patch the dependency checkout in place. Full N3/N5, loaded default ROS DDS
discovery, cross-host clock/security/resource/hardware and superiority gates stay
open.
