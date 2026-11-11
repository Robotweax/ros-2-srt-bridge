# Short baseline/one-loss cohort and bounded30-second pilot

All seven conditional single executions in frozen plan81a39e0 passed: six fresh
nominal10s cases, then one30s baseline pilot only after the six-case cohort passed.
No retry, selector adaptation, failed-cohort replacement or production runtime
change. Prior original missing-footer failure remains FAILED and unexplained.
Full N3/M3 is incomplete; PR2 remains draft, Intrinsic/M4 untouched.

## Short captured baseline/repair repetitions

| Case | Actual IMU /joints Hz | Source total | SDK/receiver samples | ROS publications | Typed observations | Source IDs unobserved |
| --- | --- | --- | --- | --- | --- | --- |
| Baseline1701 |200.017542 /50.029251|2514|2432|2432|2432|82|
| Baseline2903 |200.067455 /50.016864|2515|2423|2423|2423|92|
| Baseline4211 |200.030360 /50.032457|2514|2431|2430|2430|84|
| One-loss1701 |200.010030 /50.027372|2514|2435|2435|2435|79|
| One-loss2903 |200.054263 /50.013566|2515|2434|2434|2434|81|
| One-loss4211 |200.037539 /50.034253|2514|2424|2424|2423|91|

Each fenced interval is10.053..10.057s, both rates satisfy the declared1% gate,
and no source slots were skipped. Every observed typed hash/stamp and per-route
order matches the original source. Complete source/admission/SDK/receiver traces
retain rejected and unmatched inputs. All cases have SDK-to-receiver gap0 and
receiver rejection0; those are now explicit window gates in addition to six
conservation equations. None is a lossless source-delivery result.

| Aggregate local stage | B1701 | B2903 | B4211 | O1701 | O2903 | O4211 |
| --- | --- | --- | --- | --- | --- | --- |
| Upstream DDS |0|10|0|0|0|0|
| BUSY admission |2|5|4|1|3|2|
| Ingress replacement |0|1|0|1|0|0|
| Outbound replacement |80|76|79|77|78|88|
| Receive replacement |0|0|1|0|0|0|
| Observer DDS |0|0|0|0|0|1|
| All other loss terms |0|0|0|0|0|0|

All six balances are0 with stable empty checkpoints. Aggregate replacements do
not supply an exact loss stage for each unmatched ID. Different local populations
are not causal performance comparisons. Underlying N0 qdisc base/base+1 seed
readback has zero random impairment; these are independent-start repetitions,
not random-loss coverage. Permanent neighbors and Docker emulation remain explicit
fixture conditions. No COMMAND workload or resource-parity claim.

Each one-loss case installs a fixed classifier before source arming: row1 position3,
SDK source message8, actual handshake ISN/tuple/socket; parity is excluded. Every
actual SDK row5/6/7 is IMU and8 joints. Selected8 maps to joint source counter2 in
all three cases. Initial counter0, exactly1 final drop, selected source absent
at both native/full-PCAP taps, row parity present, explicit accepted Session
decision and original typed hash/stamp observed while classifier remains installed.
VM order is parity <= decision end <= typed observation < hook removal, and SDK
begin follows installation. No target is inferred from nominal ROS publish index.

## Independent captures and shutdown

| Per endpoint | Native/full-PCAP source | Parity | Equal file/dispatch/kernel records | Source/sender/receiver trace records |
| --- | --- | --- | --- | --- |
| B1701 |2432|608|3040|2514 /4947 /2432|
| B2903 |2423|606|3029|2515 /4929 /2423|
| B4211 |2431|608|3039|2514 /4946 /2431|
| O1701 |2434|609|3043|2514 /4950 /2435|
| O2903 |2433|608|3041|2515 /4950 /2434|
| O4211 |2423|606|3029|2514 /4939 /2424|
|30s baseline |7242|1810|9052|7514 /14754 /7242|

Actual SDK source/ISN and complete four-source parity keys match native and full
PCAP multisets exactly at both endpoints; only message8 is excluded for one-loss.
Binding offset and partial final rows are explicit. Identity capture is separately
closed at8/8 per endpoint in every case before measurement arming. No continuous
capture claim spans phase gaps. Native observers start first/close last and cover
source windows. All filtered packet recorders have final BPF before bind,
initial kernel0, stable equal populations, verified file size/hash and zero
kernel/native losses, truncation or exhaustion; interface features stay unchanged.
Realtime PCAP timestamps are not a qualified age clock; native times are skb
observations, not physical-wire measurements or cryptographic-FEC identity.

Each case records all three owned children initially live, then controlled SIGINT
exit0 with no timeout/forced kill and complete final trace statuses. The cohort
wrapper preserves original per-case verdicts and is tested to stop immediately
at any failure/exception and mark remaining cases NOT EXECUTED. Its final PASS
means the planned six short cases passed, not full N3 qualification.

## Bounded30-second baseline pilot

Measured source interval30.053896430s:6011 IMU/1503 joints, actual200.007344 /
50.010154Hz, no skipped slots.7514 source records and14754 sender records remain
below declared7750/15501 allowances and unchanged hard limits10000/75000.
No buffer expansion, truncation, undocumented window stitching or production
scheduling/admission/TTL/mailbox/provider/retry changes were used.

SDK accepts and receiver decisions7242, ROS publications/typed observations7241.
Source-to-observer missing273 balances as upstream DDS3, BUSY9, ingress replacement2,
outbound replacement258 and receive replacement1; other stage terms0, all six
balances0. Every observed typed hash/stamp/order matches, receiver gap/rejection0.
Both endpoint captures reconcile7242 source+1810parity =9052 records. All clock/
QoS/session/owner/generations/isolation, empty-pipeline and controlled-shutdown
checks pass. Age upper maxima IMU23610879ns/joints28470853ns; route histograms
match publications. This extends baseline evidence to30s, not30s one/two-loss,
long-duration seed coverage, physical sensor-age or full M3 acceptance.

## Window budgets, validation and remaining gates

Only explicit10/30-second source windows are accepted. Actual fence duration must
be[nominal,nominal+1]s and source/sender populations fit their declared allowances:
(nominal+1)*250 and twice that plus binding1. These are preflight budgets, not
substitutes for measured cadence or complete zero-loss diagnostics. Production
and measurement deadlines stay unchanged; only source-pause/host barrier waits
follow the declared window. Baseline/one-loss requires no SDK-receiver gap/rejection;
two-loss retains exactly SDK7/8 gap2 and its existing selected-source checks.

223 host tests pass, including duration/record budgets, unsupported windows,
receiver-gap/rejection gates and cohort stop/exception/order behavior. Python
syntax/diff checks pass. No SDK/ROS C++ changes/rebuild; previous SDK70 /ROS41
remain last full validation, not new executions or a new full M2 acceptance.
Seven runtime hashes are unchanged across all seven runs. All owned networks,
containers and passphrases were removed. Short-case maximum accepted-publication
upper age is40929297ns (IMU baseline2903), below250ms; these are callback-ingress
bounds under the existing clock model, not physical sensor age or overhead-free
resource/security/superiority results.

Plans, original cohort and per-case verdicts/provenance, execution matrix,
metadata/hash/typed metrics, selected shutdown/capture/clock/qdisc/fault/lifecycle
status, tests, runtime inventory and local-artifact hashes are archived. Raw PCAP/
native prefixes, journals and detailed resource/endpoint samples remain local;
credentials and full inspect/environment dumps are excluded.

Together with separately planned observed-cleanup two-loss cases, short baseline/
one-loss/two-loss repeats now exist at all three base values, with separate
provenance. Original failed/skipped cases remain authoritative and the missing
receiver-footer shutdown cause is still UNKNOWN. Next:30s one/two-loss cases and
predeclared longer-duration budgets/windows, remaining N4 barriers and full M3
age/security/resource/comparison gates. Intrinsic/M4 remains untouched.
