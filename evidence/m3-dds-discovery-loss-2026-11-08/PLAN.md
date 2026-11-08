# Controlled native DDS discovery-fragment loss/recovery plan

Freeze implementation and plan in Git before the first live execution. Exactly
one ordered baseline then fragment-cut case, fresh owned internal Docker peers,
no retries/replacement. If baseline fails, fragment-cut is NOT EXECUTED. Preserve
any contradicted hypothesis as FAILED. No production default/binary changes.

A standalone Fast DDS2.14 fixture uses UDPv4 only, explicit owned IP locators
(meta26010/user26011), no multicast/SHM/data-sharing, two bidirectional BestEffort/
Volatile/KeepLast1 HELLO topics at10Hz. HELLO is an explicit fixed28-byte diagnostic
CDR type, not the production command protocol. Robot publisher and subscriber
user_data are deliberately4096bytes each; operator metadata empty. This creates
large endpoint discovery announcements while participant discovery and user
HELLO datagrams stay small. Read back metadata sizes. No sensor/command journal,
ROS command coordinator, N5 competitor/shaper or resource comparison is involved.

Both cases use verified N0 and permanent owned L2 neighbors, same probe binary and
image. First verify eth0 MTU1500. Captures start before native participants, with
existing filter-before-bind packet-socket lifecycle/population/hash/footer gates.
A broad udp filter covers IPv4 fragments. Same VM/time-namespace proof is required.

Baseline: require participant discovery, exactly1 writer/reader match each peer,
valid HELLO callbacks each direction within45s. Observe3s more; at least20 valid
callbacks per peer must originate after the qualified checkpoint. All trace
populations complete, no invalid payload/order/timestamps, no exhaustion; clean
native teardown and owned supervisor shutdown <=5s.

Fault: before participants start, add an owned robot-only clsact selector for
IPv4 IHL5/UDP/src robot/dst operator, fragment offset185 (1480-byte continuation,
MF ignored). It drops that exact position, not all UDP, SPDP or small user DATA.
Refuse pre-existing classifier hook. Retain install VM bracket/readback/zero
initial counters. Both participants must still discover each other. Hold8s on
VM monotonic clock. Require real drop counters>0, operator writer/reader matches0
and callbacks0 throughout observed pre-removal history, robot writer/reader
matches1 and sent>=30. This is a prospectively tested asymmetric signature,
not an assumption to weaken after execution.

Remove only the owned hook, save VM bracket/counters, verify selector absent.
Require mutual matching/valid callbacks within45s on same processes, participant/
writer/reader GUIDs, then3s steady progress and>=20 fresh post-restore-origin
callbacks each way. No node/endpoint recreation, discovery-reset or intent replay.
Cut snapshots are preserved even if later outcome gates reject the hypothesis.

Independent packet follow-up: validate all original capture populations. Decode
closed captures using pinned tshark4.2.2 in a separate offline tool image; use
submessage-scoped RTPS fields and the fixture's known wire type. Verify large
SEDP announcements/fragmentation, small HELLO DATA at source/peer taps during the
controlled cut and post-restore callback association where observable. Keep
capture observations, partial headers, middleware matching and callbacks distinct.
No timing claim from realtime PCAP. Actual callbacks use proven common VM time.

Record source/image/probe/eight production hashes before/after; no builds/tests
concurrent with live cases. Archive original success/failure/skipped outcomes,
network/counter/bracket/state/shutdown/trace metadata and raw file hashes. Raw
PCAP/PDML stay local; no credentials/full inspect/environment dumps. Bounded
2048 trace records and110s native watchdog/115s supervisor are fixture limits,
not production defaults. No hardware/full ROS/N5/M3, historical root-cause,
security/clock/resource parity or transport-superiority acceptance. PR2 draft,
Intrinsic/M4 untouched. Longer SRT N5 coverage remains separate.
