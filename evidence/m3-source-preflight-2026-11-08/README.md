# Sustained source and multiroute accounting preflights

Both separately planned single executions passed. This is short N0 evidence;
full seeded N3/FEC and M3 remain incomplete, PR2 remains draft, Intrinsic/M4 is
untouched. Instrumented Linux amd64 Docker emulation, pinned existing SRT image.

| Fixture | Measured source interval | IMU / joints produced | Actual Hz | Typed observed |
| --- | --- | --- | --- | --- |
| Isolated local source, no bridge |10.001907129s|2001 /501|200.061846 /50.090447|2001 /501|
| Two isolated peers, N0 bridge |10.057059463s|2012 /503|200.058477 /50.014619|1930 /498|

The independent source diagnostic buffers logical payload fields in a fixed
10000-record buffer only when enabled (default off). SHA256 and JSON output are
deferred until the source-pause fence. Canonical little-endian field encodings
match C++/Python golden tests, excluding CDR padding. This adds bounded timer
work/storage and does not establish overhead-free operation or resource parity.
Both measured windows meet the predeclared1% cadence tolerance with zero skipped
source slots, complete source traces and zero diagnostic drops/encoding/hash
failures. Every observed typed payload matches its original source hash/stamp;
per-route order and uniqueness hold.

The isolated source run has2502 records, all locally observed. Its source and plan
are2edfe3c; the subsequent two-peer source/plan is99c4d1d. Each ran exactly once;
no failed verdict was replaced, no retry or fault was injected.

## Two-peer accounting

2515 source messages entered typed bridge callbacks. One IMU admission (counter379)
returned BUSY and consumed no SDK index. There are85 queued inputs without an
observed SDK handoff: aggregate counters report one ingress replacement and84
outbound replacements. Their IDs remain unmatched; those aggregate counters do
not individually locate each missing input.2429 samples were SDK-accepted and
received, all with explicit accepted Session decisions. One accepted IMU source
(counter18) lacks typed observation; the aggregate receive-replacement count is1,
with observer DDS loss0. No per-ID replacement-stage trace is claimed.

| Aggregate loss term | Count |
| --- | --- |
| BUSY admission |1|
| Ingress replacement |1|
| Outbound replacement |84|
| Receive replacement |1|
| Other loss terms, including upstream/observer DDS, SDK-to-receiver gap and receiver rejection |0|

All six conservation balances are0. Pending queues are empty at stable endpoint
checkpoints; age histograms reconcile2428 typed publications (1930 IMU,498 joints).
Accepted-publication upper-age maxima are17576587ns IMU and27740143ns joints,
under250ms; these are callback-ingress upper ages under the existing clock model,
not physical sensor ages. Source/sample traces are respectively2515/4945/2429
records, complete with zero drops/exhaustion. Exactly one SDK binding and contiguous
SDK message indices share the read-back ISN. This run does not independently
verify them against packets: no PCAP/native observer was armed.

The overall accounting preflight passes with87 unobserved source IDs retained.
It is not a lossless-delivery result. No admission/pacing/mailbox/provider/retry
policy was changed to eliminate these losses. Explicit permanent-neighbor setup,
N0 qdisc seeds1701/1702, common boot/zero-time-namespace proof, stable endpoint
owners/generations/session/readiness/clock/QoS and zero direct-DDS leakage are
checked. All owned containers/network were removed and the passphrase deleted.

## Validation and provenance

206 host tests pass, including negative gates for malformed/lost traces, cadence,
source phases/fences, hashes, context, BUSY index shifts, mailbox replacements,
SDK receive gaps and observer DDS gaps. Rebuilt ROS reports41 tests, zero errors,
failures or skips. Python syntax and diff-whitespace checks pass. The earlier70
SDK tests remain the last full SDK validation; no SDK source/library changed and
no new full SDK or M2 acceptance run is claimed.

The five selected simulator/bridge/transport/endpoint/provider runtime hashes were
checked unchanged across the multiroute measurement and independently inventoried
afterward. Plans, original verdicts, source/receiver/admission hash traces, typed
hashes/metrics, selected lifecycle/qdisc/clock logs, build/tests and provenance are
archived here. Local-artifact hashes also cover withheld raw resource/endpoint
samples and journals; those contents, credentials and full inspect/environment
dumps are not archived. Hash manifests are provenance, not delivery evidence.

Next: independently capture sustained mixed-route SDK identities and deterministic
N3 row faults, keeping BUSY/replacement mappings explicit; then run the predeclared
seed matrix. N4 barriers, historical uncertainties/default DDS discovery, remaining
M3 age/security/resource gates and Intrinsic/M4 remain open.
