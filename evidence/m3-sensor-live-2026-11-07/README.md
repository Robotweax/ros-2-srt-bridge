# Finite authenticated SENSOR FEC

Transport development evidence only. Full ROS N3 and M3 acceptance remain open;
PR #2 remains draft. SDK, bridge and ROS runtime sources were unchanged. The new
finite fixture links the existing installed pinned provider static archive.
Selected provider/fixture/observer hashes match before and after measurement.

The original plan/code was frozen in `94f4ade` with 166 host tests. Exactly one
ordered cohort (baseline, one loss, two losses) ran. Baseline and one loss pass;
two losses fail the predeclared provider-loss-counter gate. Its manifest remains
failed. No old evidence was edited or retrospectively accepted.

| Case | Source packets observed per endpoint | Parity | Delivered payload IDs | Provider repairs | PCAP file/captured/filter per endpoint |
| --- | --- | --- | --- | --- | --- |
| Original baseline | 16 | 4 | all 16 | 0 | 69 |
| Original one loss | 15 | 4 | all 16 | 1 | 66 |
| Separately planned revised two loss | 14 | 4 | 14; IDs 6,7 absent | 0 | 64 |

Each case creates an isolated owned IPv4 fixture with explicit permanent peers and
N0 netem, sends 16 distinct 128-byte messages at requested 10-ms spacing with
250-ms TTL, then observes for about one additional host second before collecting
receiver/provider results. Messages have complete deterministic payload checks,
not just unchecked IDs. Both endpoints negotiate SENSOR, GCM, 32-byte keys,
enforced encryption, SESSIONAUTH, secured key states, and
`fec-sensor-v1,cols:4,rows:1,arq:never`. Application I/O uses the installed public
API; this is independent of ROS message publication and bridge age authorization.

Before any source DATA, both endpoints read `SRTO_ISN` and agree. The receiver's
accepted socket handle is used as the destination wire socket ID, as assigned by
this pinned provider's `src/compat/socket_registry.cpp`. This is provider-specific,
not a portable SRT assumption. Selection is row 1, position 3/message 8 for one
loss, or positions 2,3/messages 7,8 for two losses. The returned `srt_sendmsg2`
message numbers are checked, source send operations are bracketed in VM monotonic
time, and captured outgoing handshakes confirm the negotiated initial sequence.
The complete captured DATA/parity identities also confirm the expected origin,
message numbers and destination socket; no first-observed-DATA origin inference.

The original two-loss case delivered the expected 14 payloads with zero repairs,
but `pktRcvFilterLossTotal` was zero instead of the planned two. Source inspection
shows `RowFecDecoder::expire_row` only appends irrecoverable ranges for
`arq:onreq`; SENSOR `arq:never` does not populate a generic irrecoverable-loss
counter. The original counter expectation was wrong. Original case 2 failed before
its final bounded-drain/analysis path, so it has no drain qualification, even
though its shutdown footer happens to reconcile. It is not used as accepted
two-loss evidence.

A separate prospective revision (`revision-plan.json`, frozen `150eaf6`, 167 host
tests) ran exactly one fresh two-loss fixture. It reports exact missing IDs at the
finite observation cutoff separately from the zero provider filter-loss report.
All packet identity, drop, security and capture gates remain in place. Both
selected identities have exactly one gact drop; all four parity packets survive,
including parity sharing selected last-source sequence. Fourteen payloads arrive,
zero are repaired and IDs 6/7 remain absent at the cutoff. This is a finite
observation, not an assertion about all possible future delivery. All executed
cases report zero source DATA retransmissions and receiver undecryptable packets.

For the accepted cases, native v2 observation counters are complete with zero
reserve/copy losses, DATA/parity identities match exact expected populations in
both native and PCAP captures, final standalone footers reconcile with zero kernel
drops, bounded drain returns stable equality and features remain unchanged.
Classifier removal is verified. Capture timestamps are same-VM monotonic with
recorded boot/time-namespace proof. No physical wire delivery, overhead-free
observer, comparable CPU, ROS publication/age or CONTROL command claim follows.
Raw original result field `unrecoverable:0` in the first two cases is a legacy
label of the old validator, not a generic loss metric.

`source-provenance.json` distinguishes original and revision code. No new full
SDK/ROS/M2 regression run is claimed; only the finite installed-provider cases and
host suite above ran. Raw payload captures stay under `.local/m3-sensor-live/` and
`.local/m3-sensor-live-r2/`; hashes and selected logs/readbacks/results are retained
here. Credentials, full container inspect and environment dumps are excluded.

Next: carry trusted connection identity and the validated selector into ROS N3
sensor publication/accounting/age tests, including late/repaired ordering. N4
command-phase barriers, old failed capture/N5 cohorts and all other M3 gates remain
open. Intrinsic/M4 is untouched.
