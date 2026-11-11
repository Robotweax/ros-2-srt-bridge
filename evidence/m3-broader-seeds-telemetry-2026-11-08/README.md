# Remaining N5 seeds and closed telemetry diagnosis

The frozen additional-seeds cohort **fails** on seed2903. Remaining base seeds
were run exactly once on the unchanged runtime used by the separate prior4211
cohort. No retry, tuning, dependency edit, budget extension or verdict relaxation.
PR2 remains draft; full N5/M3 and Intrinsic/M4 are not accepted or advanced.

| Slot | Seconds | Success/attempt | Skipped slots | Unresolved | Strict success | Success or qualified durable expiry |
|---|---:|---:|---:|---:|---|---|
| new N0/1701 | 15 | 8/8 | 0 | 0 | PASS | PASS |
| new N5/1701 | 300 | 125/125 | 25 | 0 | PASS | PASS |
| new N5/2903 | 300 | 97/98 | 52 | 1 | FAIL | FAIL |
| prior N5/4211, separate cohort | 300 | 136/136 | 14 | 0 | PASS | PASS |

Zero verified expiries in these slots. Skips remain visible, so successes do not
prove every offered two-second slot was served. The base run harness passed its
own gates for all three new slots; the additional command-progress audit correctly
failed2903 and the cohort exited1. Historical failed/UNKNOWN evidence is unchanged.

Seed2903 intent98 has one original SDK handoff at VM monotonic609918618068ns,
sender journal state8/reason2/revision0 (unresolved reconciliation), no receiver
record, and no original COMMAND receive/defer/expiry event. Robot CONTROL loss
(epoll-error trace, value9) follows at614211332487ns, with session invalidation;
operator SENSOR loss follows, then operator CONTROL loss619247803781ns. Available
old-session provider brackets show retransmissions and send backlog increasing.
Later QUERY traffic in a new session receives NOT_FOUND (worker value2), which is
not original execution or expiry authority. This does not prove nonexecution or a
unique network/provider cause. No original command replay or retrospective expiry.
See [selected command evidence](analysis/seed-2903-intent-98.json), full trace
population and closed audit in [execution.json](execution.json).

## Telemetry localization

Identical frozen analysis was applied to original prior N0/N5 captures and all
three new closed slots. Application-window counts below are distinct from whole
capture counts (which include setup/teardown). SDK accepted is derived from the
conservation equation decoded + accept-to-receiver gap; it is not emission proof.
All six accounting residuals are zero in every case; sources remain ~200/50Hz.

| Case | Produced | SDK accepted | Decoded SAMPLE | Observer | Accept-to-receiver gap | Receiver rejected |
|---|---:|---:|---:|---:|---:|---:|
| prior N0/4211, 15s | 3780 | 3665 | 3665 | 3665 | 0 | 0 |
| new N0/1701, 15s | 3793 | 3674 | 3674 | 3672 | 0 | 0 |
| prior N5/4211, 300s | 75022 | 72387 | 1200 | 871 | 71187 | 329 |
| new N5/1701, 300s | 75037 | 72037 | 28363 | 27890 | 43674 | 473 |
| new N5/2903, 300s | 75023 | 69447 | 27192 | 26465 | 42255 | 716 |

Every rotation/file/footer reconciles with zero reported capture drops. Exact UDP
5-tuple/payload-hash **multisets**, including duplicates, match in both directions
for all five closed cases. This rules out a missing observed datagram between
these taps, not loss before egress observation. Qdisc counters have distinct tails
from application and capture windows; root/child mirror drops and must not be summed.

| N5 seed | Robot root drops | Operator root drops | Whole-capture SENSOR DATA | DROP_REQUEST | Repeated retirement controls |
|---|---:|---:|---:|---:|---:|
| prior4211 | 2716297 | 0 | 22205 | 39761 | 7837 |
| new1701 | 116533 | 0 | 28261 | 670 | 346 |
| new2903 | 166531 | 396 | 27075 | 3201 | 2211 |

All observed SENSOR source DATA are distinct sequences/messages within their
flow/destination socket, solo-boundary3, retransmission bit0; parity is separately
classified. Thus DATA repetition alone does not explain the4211 count. Its main
flow has22163 distinct source DATA, but application decoded count is1200 across
the measurement window. These are different populations without encrypted typed
mapping; the difference is a diagnostic signal, not an exact provider discard count.
Only324 of4211 decoded samples fail bridge age qualification (zero stale), so
bridge freshness rejection alone cannot explain its71187 accept-to-receiver gap.
The new seeds have388/631 unknown-age rejects and1/0 stale rejects respectively.
Other stage losses and all identities are in [comparison.json](analysis/comparison.json).

N5 actually uses TBF512kbit/s,4096-byte burst, a16-packet netem child, and an
iperf3 UDP competitor **128Kbit/s**, not6Mbps. Competitor offered traffic/liveness
checks passed. These are offered-load evidence; interrupted-client receiver-zero
summaries are not proof of receiver delivery. Configured sensor traffic, FEC,
CONTROL and feedback share the constrained direction. Heavy qdisc drops are
consistent with substantial loss before the observed taps; counters cannot allocate
those drops to a specific flow or typed sample. Prior independently qualified
software-root PASS/loss controls in the qdisc-stage evidence support this tap
placement interpretation, not a new same-flow causal intervention here.

Pinned provider52be7c8 source, inspected read-only, explains header fields and
SENSOR sequence-only singleton retirement semantics. TTL retirement and bounded
10ms retry scheduling (up to32 prefix controls per timer poll, plus retained
requests under runtime send budgets) provide a plausible feedback-pressure
mechanism. The actual pre-tap attempt rate and internal branch execution were not
measured. Capture file order finds **zero DATA after a prior same-sequence
retirement** in every case. This does not support an observed retirement-overtakes-
DATA explanation. Conversely,9673/122/317 observed source sequences in4211/1701/
2903 are eventually named by retirement. Later retirement could interact with
unread buffered data, but cleartext controls can be rejected or pending the peer
send horizon, and capture order is not provider processing/application-read order.
Neither an SDK bug nor a unique retirement/buffering/decryption cause is proved.
Source file hashes: [provider-source.json](analysis/provider-source.json).

## Provenance and next controlled work

Plan/source frozen before live: e391467 then abc0ebb; execution records full SHA
abc0ebb969f881e29b43e5ae5267bd6782234630. Source hashes verified before posthoc
changes. All8 runtime hashes equal prior4211, before/after live and archive; pinned
image/provider unchanged. No builds/tests/heavy analysis overlapped live. Owned
containers/networks removed; passphrase removed. Host278 passed before live;
posthoc retirement analyzer04c163b adds4 meaningful guard tests, host282 PASS.
SDK72/ROS41 are prior validations; no new native/ROS build or claim this turn.

The retirement-order tool was committed only after the cohort closed and frozen
source archive verified; it changes analysis, not the measured runtime. Original
raw PCAP rotations, journals, provider streams and resource samples remain local
with hashes. Public selected logs omit provider sample lines; selected run JSON
omits provider record/delta arrays. [public-selection.json](public-selection.json)
records exact omissions and raw/derived hashes. Analysis retains one failed
wrong-N0-path invocation and its corrected read-only result, not a repeated live
run. See [analysis provenance](analysis/analysis-provenance.json) and validation.

Next freeze a separate bounded diagnostic plan: reproduce the2903 CONTROL/session
failure with kernel-monotonic packet/provider correlation before any change;
separately expose SENSOR receive insertion/window, delivery, decryption and
retirement counters through a reviewed provider diagnostic surface. Follow with a
controlled paced/latest-data experiment against the unchanged baseline only after
that evidence is available. Keep original budgets, journal semantics and both
verdicts; no default tuning or provider edits justified by these correlations.
Loaded default-ROS discovery, full N3/N5 durations, clock/security/resource/hardware
and performance-comparison gates remain open.
