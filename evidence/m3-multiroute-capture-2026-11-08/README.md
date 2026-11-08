# Captured full-rate mixed-route baseline and selected FEC repair

Both conditional single executions in PLAN.md passed from frozen source517a940.
The baseline passed before the one-loss fixture was started. No retry, changed
selector, failed-verdict replacement or production runtime change was used.
This is short controlled N3 evidence, not the full N3 seed matrix or M3 acceptance.

| Case | Measured duration | Source IMU /joints | Actual Hz IMU /joints | Typed observed | Unobserved source IDs |
| --- | --- | --- | --- | --- | --- |
| Baseline |10.054813463s|2011 /503|200.003710 /50.025791|1928 /498|88|
| One exact source loss |10.054942713s|2011 /503|200.001139 /50.025148|1933 /498|83|

Both rates meet the declared1% gate with zero skipped source slots. Source traces,
actual admissions, SDK message numbers, receiver Session decisions and all remote
typed hashes/stamps/order reconcile. All six accounting balances are0. This is
not lossless source delivery:

| Aggregate loss term | Baseline | One loss |
| --- | --- | --- |
| Upstream DDS |2|0|
| BUSY admission |2|6|
| Outbound replacement |84|77|
| All other terms, including SDK-to-receiver gap, receiver rejection and observer DDS |0|0|

Different local admission/replacement populations make these separate fixtures,
not a causal performance comparison of fault vs baseline. Per-ID queued inputs
without handoff remain unmatched; aggregate counters do not identify each one's
exact loss stage. No source/admission/pacing/mailbox/retry/provider policy changed.

## Independent captures

Each fixture closes an identity phase before arming source publishing, then opens
a separate measurement phase. Handshake ISN and one binding message agree at both
taps; identity PCAP file/dispatch/kernel counts are8/8 per endpoint in both cases.
No continuous-capture claim spans the gap between phases.

| Measurement, per endpoint | SDK SAMPLE accepts | Native/full-PCAP source records | Parity records | Reconciled file/dispatch/kernel records |
| --- | --- | --- | --- | --- |
| Baseline |2426|2426|606|3032|
| One loss |2431|2430|608|3038|

All actual SDK-assigned source numbers/ISN agree with captured keys. Every expected
four-source parity row agrees, including the initial binding offset and incomplete
final row handling. The only excluded source key in the fault case is message8.
Both endpoints independently agree on exact native and full-PCAP source/parity
multisets. Recorders start with kernel count0 and final BPF attached before bind;
file/dispatch/kernel counts stabilize equally, with zero kernel/native losses,
truncation or exhaustion and verified file length/hash. Native observers start
first, close last and cover each source-enabled window. Interface features remain
unchanged. Realtime PCAP timestamps are not qualified timing/age evidence; native
kernel monotonic times are skb observations, not physical-wire times.

## Selected mixed-route repair

Before source arming, an owned egress classifier selects row1 position3, source
message8, exact SENSOR tuple/socket/ISN; message-zero parity is excluded. Its final
counter records exactly one dropped packet (438 bytes); the original hook remains
installed through both result barriers and is then removed/read back empty.

Actual SDK row messages5/6/7 are IMU, and8 is joints. Message8 maps through the
actual admission stamp to source joint counter2 / envelope sequence2. Its source
packet is absent at both native/full-PCAP taps, while row parity is present.
The receiver emits an explicit accepted Session decision for message8 and the
remote typed joint is observed once with its exact original payload hash/stamp.
The original classifier is still installed at that point. VM monotonic ordering:

- Incoming row parity:47375327895ns.
- Receiver decision end:47377568728ns (2240833ns after parity).
- Typed observation:47378953561ns (3625666ns after parity).
- Classifier removal begins:60051112984ns.

This supports reconstruction of the selected mixed-route source in the pinned
provider fixture, not a cryptographic-FEC identity or physical sensor-age claim.
There is no SDK-to-receiver gap or receiver rejection in either fixture. Accepted
publication age upper maxima are IMU14011182ns /joints27148919ns for baseline,
and14179458ns /29336477ns for one loss, under250ms with matching route histograms.
No per-sample conservative age estimate is invented from capture timestamps.

## Validation, provenance and remaining work

210 host tests pass, including source/parity binding offsets and wrap, exclusions,
strict population failures and negative mixed-route/decision/hash/classifier/
parity-order gates. Python syntax and diff checks pass. No SDK/ROS source/library
changed; previous SDK70 and ROS41 remain the latest full validations, not new runs.
No new full M2 or resource-comparison acceptance is claimed.

Source/sender/receiver trace populations are2514/4939/2426 baseline and
2514/4946/2431 one-loss, all complete with zero drops/exhaustion. Clock/QoS/session/
owner/generations/isolation and empty stable checkpoints pass. Seven runtime
hashes remain unchanged across both runs and match the post-run inventory.
Owned containers/network and passphrases were removed.

Plans, original results, provenance, hashes, selected lifecycle/clock/qdisc/fault/
capture statuses, source/sample traces, typed hashes/metrics and tests are archived.
Raw PCAP/native prefixes, journals and resource/endpoint detail stay local with
hashes; credentials and full inspect/environment dumps are excluded. New passing
cases do not repair or reinterpret historical capture/UNKNOWN/reset failures.

Next: sustained mixed-route two-source unrecoverable row case and predeclared
seed repetitions; then remaining N4 barriers and M3 comparison gates. Bounded
source traces currently hold10000 records, so longer runs require predeclared
windows/budgets. Default DDS N5 discovery, historical uncertainties, physical-age,
security and resource parity remain open. PR2 stays draft; Intrinsic/M4 untouched.
