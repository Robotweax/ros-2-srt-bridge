# Intent3 probe-renewal diagnosis from retained evidence

The evidence supports delayed reliable, ordered CONTROL delivery as a mechanism
for the expired probe lease. It does **not** show a6.8s owner-thread stop or
6.8s silence on the CONTROL UDP flow. Exact probe attempts, echoed timestamps
and rejected-reply decisions were not retained, so a specific probe failure chain
cannot be proved retrospectively.

This is a read-only audit of `.local/m3/20261109T135531879199Z`; no new run,
runtime change, tuning, forced expiry, command replay or application journal
recovery. Historical118 stays UNKNOWN/reconcile_required. Source and all303 raw
cohort files match their manifests before/after;471 other prior artifacts are
also rechecked. The pinned provider is clean,
and the calibrated sender/older runtime inventories remain unchanged.

## Clock and scheduling context

The retained old/new probe anchors are62373601819/69240717739ns, separated by
**6867115920ns (6.867115920s)**. The first deferred check at68855687781ns sees
probe age6482085962ns (6.482085962s); that age is distinct from the anchor
separation. Recovery is recorded385.096458ms later. As in the cohort evidence,
new intent3 keeps its original5s command budget and closes succeeded with one
SDK handoff. These two clock snapshots are not an exhaustive probe admission log.

Unchanged source contracts explain why UDP activity need not renew the clock:

- The owner *attempts* `begin_probe` when its one-second timer is due, then sets
  the next timer even when the call reports probe_busy. This is not a promise of
  one emitted or accepted probe per second. There is at most one pending probe.
- `Session::tick` and `begin_probe` clear a pending probe at age>=2s. A TimeReply
  renews the mapper only when its echoed t1 matches the current pending probe and
  its age is **strictly below2s**. Old/unmatched replies return probe_not_pending.
- Management probes/replies share the bounded CONTROL FIFO with COMMAND/QUERY/
  STATUS/ERROR. `send(0)` can leave the front queued on rate limiting or SDK
  backpressure. CONTROL receive also checks application space before consuming
  any frame. The retained trace does not record these probe-specific branches.
- The pinned CONTROL provider forces wire in_order even when sendmsg passes0;
  its receive buffer requires the earlier sequence prefix for ordered delivery.
  Reliable delivery can therefore outlast the bridge's probe acceptance window.
- `apply()` does not emit a command trace for probe_busy/probe_not_pending
  alone. Their absence from the trace supplies no attempt or rejection count.

The diagnosed source hashes and provider source paths are in `analysis.json`.
No production timing, queue, retry or scheduling rule has been changed.

## Native ordering evidence

The fixed diagnosis window is60373601819..71240717739ns: two seconds before the
old anchor through two seconds after the recovery anchor. Both native v2 streams
are complete and share the proven VM monotonic clock. Active tuple/socket IDs
are associated with the same provider session/generation on both peers.

All matching outer CONTROL headers are retained in
[`analysis.json`](analysis.json). DATA sequence, message number, boundary,
ordered/retransmit bits, wire timestamp and UDP length are decoded using the
pinned provider header layout. Payloads remain encrypted. At these timestamp
magnitudes,157-byte UDP DATA is compatible with a TimeReply; **length and timing
do not authenticate its kind or bind its echoed t1**.

| Reply-length candidate entering operator | First receiver tap | Necessary earlier-prefix availability | Native prefix wait |
|---|---:|---:|---:|
|sequence608997432 /message18|66158291446ns|66158291446ns|0 observed extra wait|
|sequence608997443 /message29|65636107154ns|67846142822ns|**2210035668ns (2.210035668s)**|
|sequence608997455 /message41|69239261906ns|69239261906ns|0 observed extra wait|

For443, earlier sequence442 was first observed at67846142822ns. All preceding
current-flow sequences are accounted for from the captured first DATA/message1;
the wire ordered bit is set. Thus the complete native prefix for443 was not
available for at least2.210s after that candidate's first receiver-tap observation.
If this candidate is a TimeReply, its initiating probe necessarily predates it,
so this wait alone exceeds the bridge's2s acceptance window. This is a
conditional compatibility result, **not an observed probe_not_pending decision**.

Candidate455 precedes the recorded new mapper anchor by1455833ns (1.455833ms)
and has no additional observed earlier-prefix wait. That is compatible with
recovery; it is not proof that455 carries the accepted reply. Zero observed
prefix wait does not mean immediate SDK admission, decryption or application read.
The calculation withholds availability after any missing predecessor and refuses
sequence-wrap interpolation. Its guards and captured-data assertions pass.

## Independent owner, provider and path context

Within the fixed window, the operator owner records104 available provider reads,
maximum sample-start spacing110.811500ms; the robot records108, maximum
101.470292ms. These reads run on the transport owners. This excludes a continuous
whole-gap owner stop, while leaving shorter stalls, scheduling jitter and CONTROL
receive backpressure unmeasured. All selected socket states are5/connected,
same generation/session; no CONTROL loss, session change or invalidation is
recorded in this window.

Every matched CONTROL direction continues DATA/ACK/ACKACK/NAK activity, with the
largest fully observed adjacent gap below0.992s. The earlier cohort's three
>=1s primary CONTROL gaps occur much later, and cannot be assigned as this
early intent's cause.

Fully contained provider read-pair deltas between the retained anchors record
operator39 and robot256 retransmissions; the operator sends8 NAKs and the robot
receives8. No undecrypt increment is observed. Maximum sampled buffers over the
context window are robot17 send packets and operator9 receive packets. These are
aggregate counters/gauges, not unique packet deliveries or probe identities.

Both peers have108 contained neighbor reads: stable expected MAC, REACHABLE,
no read error. No scoped ARP-reply lifecycle intersects the window. This does
not prove continuous neighbor state or global absence of ARP activity. Contained
whole-interface root samples show operator0 and robot2708 drop increments;
robot overlimits increase6787. Root statistics include other traffic and cannot
identify a particular probe's drop or distinguish every queuing stage.

## What remains unresolved

The retained records distinguish **accepted-clock renewal** from packet activity
and show an ordered-delivery delay long enough to invalidate a reply candidate.
They cannot establish each probe's generation/queue/SDK-handoff/t1/t2/t3, its
actual receive/admission time, busy/timeout/late-echo decision or exact root drop.
No single per-probe transport/scheduler cause is claimed, and no new fact
retroactively classifies historical118,34,98 or12.

For exact attribution, the next diagnostic increment would be separately
calibrated, default-off per-probe lifecycle visibility at the existing decisions:
timer attempt/result, queue/handoff, correlated echo and reply-admission result.
It must preserve the one-pending-probe rule and current2s/5s bounds. No such
instrumentation, build or experiment is introduced here. PR2 stays draft,
M3/full qualification open, Intrinsic/M4 untouched.
