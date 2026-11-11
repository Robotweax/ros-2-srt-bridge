# Loaded ARP reply eligibility, without tuning

PASS-only ARP reply counters now run on both owned peers beside CONTROL counters.
The loaded cohort passes N0/2903 8/8 and N5/2903 134/134, with0/16 skipped slots,
zero expired/unresolved intents and no active context/link-loss events. Each slot
runs once; exit0. Added observer work means this is not a mitigation, performance
comparison or resolution of prior intents98/12. PR2 draft, M3 incomplete, M4 untouched.

The primary CONTROL-window analysis is cautious: its one1.026943917s robot→operator
gap has ten requester INCOMPLETE samples, but no positive reply-counter increment
in the strictly contained reads. The genuine operator reply appears at the end
and only the next counter read includes it. Zero contained growth cannot establish
no generation during the omitted boundaries. No session failure recurs here.

A separately marked **posthoc all-positive-step** analysis finds eight robot-side
read envelopes with positive PIPE/PASS reply execution increments and no matching
source-tap reply within the wider read envelope. All eight have root queue pressure
in a wider bracketing context. This supports a post-eligibility delay/loss stage
under load, not lack of reply eligibility in those intervals. It does not prove
eight lost packets or the unique historical cause.

## Instrument and prospective measurement

The already qualified exact seven-word ARP selector matches owned operation2,
SHA/SPA/THA/TPA; native frames separately check Ethernet MAC/direction. Every read
validates software-only u32, complete repeated JSON match words and distinct
PIPE→PASS actions, never DROP. Replies are ordinary owned kernel output; no active
ARP probe or userspace ARP producer. Separate preferences/protocols coexist with
CONTROL IP PASS, preserving root options. New200ms polling is bounded37500records
per peer, with read brackets, cumulative action identities/counters, errors and
complete footer/population gates. PIPE/PASS reads are non-atomic and need not equal
at each instant. Any action drop, regression, changed identity, offload, missing
status/error/budget/capture gate invalidates diagnostics.

N0 positively counts operator1/robot2 eligible replies. Both PIPE and PASS lifetime
totals agree there, with zero action drops. Loaded N5 totals are operator11/robot14
reply executions (462/588bytes), also zero action drops. These are action executions,
not authenticated unique ARP packets, source messages or exclusive loss counts.
No counter-minus-tap subtraction is presented as a drop count.

The fixed run retains dynamic neighbors,512kbit TBF/16packet child,128Kbit offered
competitor,200/50Hz sources,2s offered commands,original5s budgets/5000ms idle/8s
result drain. No cache flush/replace/permanent entry, ping, injected loss, priority,
queue, bandwidth, timeout or budget change. No SDK/ROS/native-recorder rebuild;
all8runtime+2observer hashes equal the preceding controlled fixture and remain fixed.

## Primary selected CONTROL gap

All primary>=1s source gaps and all active loss windows are retained; there is one
gap and no loss window in N5, neither in N0. For requester robot, the ARP responder
is operator; the two roles' root counters are kept separate. The gap spans
[322013257855,323040201772]ns on the proven common zero-offset VM clock. Robot
neighbor samples are INCOMPLETE10; operator is REACHABLE10. CONTROL classifies
provider growth without selected PASS growth. This is a pre-PASS association.

Responder contained reply reads cover the outer envelope
[322044534022,322867747647]ns with zero eligible/PASS delta and zero reply hooks.
The peer request/reply is observed near3230401..ns, outside that contained read
envelope. The retained next counter read grows9→10. Neither zero delta nor the
last reply observation can be used to backfill exact generation time or causality.
All before/after/crossing reads and both peers' native ARP records remain in
[primary analysis](analysis/srt-N5-2903-arp.json).

## Posthoc audit of every positive reply step

After primary closure, a new explicit analysis selects **all** adjacent eligibility
OR PASS packet increments whose two reads are wholly inside the source publication
window. This does not change primary selection or command verdicts. It retains
nonatomic one-action-only increments too, rather than assuming both counters update
together. Source/peer hooks are counted over the wider first-read-start→last-read-
end envelope, with inner counts separate. Outside/edge generation is not guessed.

| Reply source | Positive steps | Steps with source reply in outer envelope | Steps with positive PIPE/PASS and no source reply there |
|---|---:|---:|---:|
| operator |10|10|0|
| robot |13|5|8|

Each of the eight robot steps reports+1 eligible/+1 PASS execution,+42bytes,0action
drops. Outer read envelopes are about222–224ms, fully within native coverage. The
reply-source (robot) root context is explicitly wider, about645–647ms: root drop
increments176..6089 and sampled peak qlen16 in every such context. Requester
neighbor samples are DELAY/PROBE. These are whole-interface counters and sampled
gauges, not individual ARP drop attribution. Mirrored child drops are never added.
Some later source replies lie outside step envelopes; eight is a **window count**,
not eight permanently lost packets or unique requests. ARP has no nonce binding
those repeated tuples to particular requests/counter executions.

The evidence places missing/delayed observations after eligible/PASS reply handling
in those envelopes, with root-pressure association. It does not distinguish exact
queue/drop/driver branches or establish an organic failure mechanism uniquely.
[All23steps, widened root contexts and hashes](analysis/n5-posthoc-positive-steps.json).

## Telemetry and integrity

N5 source75034/SDK-accepted72066 by conservation/decoded15913/observer15850;
accept-to-receiver gap56153, receiver rejection63 (unknown-age19/stale0). Six
conservation residuals remain zero, sources~200/50Hz. Sensor availability is still
unqualified. N0 source3783/observer3656 is separately recorded. Closed UDP tuple/
payload-hash multisets match both directions:67864 robot→operator,65672 reverse.
Whole-run root drops1294240 robot /0operator are not per-ARP or window loss counts.
SENSOR lifetime/partial counter scopes remain distinct from application windows.

Plan24062a9 precedes frozen measured source2aae62b724cd34f6340366e52b1352dc29cc7bee,
host322 PASS. After closed source/archive verification,17e4e46 adds reply-source
root correlation and2scope guards (host324), then051df30 adds all-positive-step
posthoc audit and3guards (host327). Those revisions change analysis only. No tests,
builds or heavy analysis overlap live. SDK72/ROS41 are prior validation, not newly
executed suites. No runtime/provider/observer build or tuning; provider source and
archive unchanged. All trace/provider/native/PCAP/neighbor/CONTROL/ARP population
gates pass, rules/owned namespaces/credentials removed.

Raw originals remain local with hashes. Public selections omit repetitive provider
streams/arrays, packet binaries, journals and full sample streams while retaining
summary, phase/window reads, raw rule readbacks and complete statuses. Exact raw
file disposition and selected field/line omissions are in
[public-disposition.json](public-disposition.json) and
[public-selection.json](public-selection.json). Posthoc source lineages and negative
guards are explicit; previous FAILED/UNKNOWN evidence is unchanged.

Next freeze a targeted queued-versus-dropped ARP observation/control with packet-
level identity or calibrated root-drop tracing before mitigation. These aggregate
counters already distinguish eligibility from downstream absence/delay; they do
not justify tuning from arithmetic differences. Historical exact causes, full
N3/N5, default loaded DDS discovery, clock/security/resource/hardware and transport
comparison gates remain open. PR2 stays draft, Intrinsic/M4 unstarted.
