# Controlled native DDS discovery-fragment loss and recovery

**The corrected baseline and fragment-loss case pass.** Dropping one continuation-
fragment position prevents operator endpoint matching and HELLO callbacks while
participant discovery and robot publishing remain live. Removing the selector
restores matching and callbacks on the original processes/GUIDs within the
observed805ms qualification checkpoint. This demonstrates a mechanism in an
explicit native fixture, not the unique cause or repair of the original ROS/N5
cold-start failure. Production defaults and binaries are unchanged.

Three earlier no-loss controls remain FAILED, with their fragment cases
NOT EXECUTED. The fixture participant listener intercepted the aggregate data
notification; that fixture defect was diagnosed and corrected before any fault
injection. No failed cohort or original workload verdict was replaced.

## Frozen design and scope

[PLAN.md](PLAN.md) and sourced12feb5 precede live execution. Subsequent observer/
listener revisions are independently recorded before their respective cohorts.
Each cohort has a fresh baseline and a fresh fault namespace; failure of the
baseline skips the fault without retrying it. Native fixture source5ba20c1 passes
both cases. No builds/tests ran concurrently with live cases.

The standalone executable links the installed Fast DDS library, not the bridge
SDK. Two native participants use UDPv4 only, fixed owned IPv4 locators26010
metatraffic/26011 user traffic, no multicast, SHM or data-sharing. Each participant
has a BestEffort/Volatile/KeepLast1 publisher and subscriber for bidirectional10Hz
HELLOs. These use an explicit28-byte diagnostic CDR type, not production
DdsCommandFrame, command journals or bridge sessions. Robot writer/reader discovery
user_data are deliberately4096bytes each; operator metadata are empty, with actual
native QoS/metadata readbacks. This creates fragmented endpoint announcements
while participant discovery and user HELLO DATA remain small.

Both cases use verified N0, owned permanent neighbors, eth0 MTU1500 and common VM/
time-namespace proof. There is no N5 bandwidth shaper/competitor, sensor load,
production ROS coordinator, hardware or comparative resource measurement. Explicit
UDP/locators/metadata are diagnostic settings, not a replacement system baseline.

## Preserved no-loss fixture failures

| Cohort source | Baseline | Fragment case | New observation |
| --- | --- | --- | --- |
| d12feb5 |FAILED at45s callback gate|NOT EXECUTED|Mutual matches,425/426 writes,0 callbacks|
| d3a47e8 |FAILED at same gate|NOT EXECUTED|Reader callback/deserialize/take-error counters all0|
| 2fe1737 |FAILED at same gate|NOT EXECUTED|Unread history1 on both peers; no reader callback or decoder call|
| 5ba20c1 |PASS|PASS|Participant listener DDS-status mask restricted; actual reader callbacks resume|

DATA was visible at both taps in the failed controls, and their native teardown
footers and child shutdowns are clean. Do not confuse those clean shutdowns with
passing workload gates. Their original matrices, logs and runtime/source hashes
are retained in `initial/`, `observer/` and `history/`.

A native participant listener registered with StatusMask::all() inherits an empty
DATA_ON_READERS handler. Fast DDS checks that aggregate handler before an
individual DATA_AVAILABLE listener. Register the fixture's participant listener
with StatusMask::none(), preserving its vendor participant-discovery callback
and explicit reader/writer listeners. No wire, codec, QoS, acceptance, polling-
fallback or deadline change was needed. The observed unread-history signature,
unchanged codec and corrected live callbacks support this fixture diagnosis.
This is not a diagnosis of the separate original ROS/RMW failure.

[LISTENER-REVISION.md](LISTENER-REVISION.md) links the
[Fast DDS2.14 dispatch implementation](https://raw.githubusercontent.com/eProsima/Fast-DDS/v2.14.5/src/cpp/fastdds/subscriber/DataReaderImpl.cpp).
Relevant API context is the official
[Subscriber notify_datareaders documentation](https://fast-dds.docs.eprosima.com/en/2.x/fastdds/python_api_reference/dds_pim/subscriber/subscriber_class.html)
and [listening locators](https://fast-dds.docs.eprosima.com/en/2.14.x/fastdds/transport/listening_locators.html).
The installed runtime outcome is the local validation, not a general portability
or conformance claim. The revisions preserve the earlier evidence and assumptions.

## Corrected no-loss control

The two peers discover each other and match exactly one native writer/reader each.
Valid callbacks and deserializations occur on both sides with invalid/error0.
The qualification-to-end fence contains30 fresh callbacks per direction. Inside
the narrower three-second steady-origin window, counts are29 operator/28 robot. Processes, participant/writer/reader GUIDs and ownership
stay unchanged. Both full-run captures contain136 records and8 fragment frames;
all70 unique HELLO payload identities agree at both taps. Four endpoint bindings
are decoded per tap. The deliberate large discovery metadata therefore fragments
without preventing unimpeded native discovery and delivery.

## Controlled continuation-fragment loss

Before starting either participant, install an owned robot clsact egress u32 rule
for IPv4 IHL5, UDP, exact robot→operator addresses and fragment offset185 (1480-byte
continuation). MF is ignored. UDP ports are not read from a continuation fragment.
Refuse an existing classifier hook. Record the VM install bracket, exact preference
readback and zero initial counters. Small participant/HELLO DATA are not selected.

The deliberate VM hold is8.000577254s after mutual participant discovery. The
selector's guaranteed installed interval is9.638923087s including startup and
readback overhead; it is not an exact8s whole-network outage. At the blocked
checkpoint:

| Native observation | Operator | Robot |
| --- | ---: | ---: |
| Peer participant discovered |true|true|
| Writer / reader matches |0 /0|1 /1|
| HELLO write attempts |78|78|
| HELLO callbacks |0|0|
| Invalid / codec errors |0|0|

All observed operator pre-removal match events remain unqualified; no transient
positive match is silently ignored. The rule records18 packets/18 drops,
27252bytes. It drops that fragment position, not the whole DATA path. Only the
owned hook is removed, with VM bracket and empty preference readback.

Both peers qualify again on the same process IDs/start epochs and participant/
writer/reader GUIDs. Qualified snapshots are793.143250ms operator and804.947583ms
robot after the removal-end bracket. Those observations include endpoint matching,
>=3 valid callbacks and state sampling; they are not pure discovery latency bounds.
The restoration-to-steady-end fence contains33 fresh callbacks each direction.
Restricting origins to the three-second steady interval gives28 operator/29 robot,
still above the original>=20 gate. No restart/recreation, discovery reset, intent replay or
command execution is used. No claim of permanent absence follows from the earlier
zero callback count.

## Independent closed-capture crosscheck

Existing filtered packet-socket capture attaches its final udp filter while the
socket is disabled, before eth0 bind. Ready/status/drain/file hash and full kernel
population gates pass for both endpoints of all five executed baselines/cases.
The three earlier failed controls have958,970 and958 records per tap respectively;
corrected baseline136/136, corrected fault282 robot/264 operator. These are per-
tap populations, not paired packet losses. Original PCAPs stay local and immutable.

Pinned tshark4.2.2 runs offline in a separate capability-dropped, network-disabled
analysis container. Its immutable image ID/commands, original hashes and decoded
metadata are retained. Submessage-scoped writer GUIDs and actual original endpoint
identities bind the known28-byte CDR HELLO: exact header/magic/role/sequence/origin
and payload digest are checked. Full-run HELLO identity sets agree at both taps:
70 baseline,152 fault. Discovery fragmentation is observed; after restoration,
all four endpoint bindings appear at each tap.

For the fault case, all78 robot HELLO samples whose **encoded origin** falls in
the controlled VM hold/removal-begin interval appear identically at both taps.
All78 occur before the first complete robot publication advertisement in operator
capture order (frame175). This independently supports the unknown-writer DATA/
missing-discovery signature. It is origin-time plus observer file order, not a
qualified realtime-PCAP arrival time or proof every selected DATA arrived before
selector removal. Native callback/match histories provide the live application
gates; packet observation alone never supplies a successful application outcome.

## Validation and provenance

262 host tests pass. New checks cover exact fragment selection without fictitious
UDP continuation ports, owned drop counters, preserved identity/participant
eligibility, no early matches, fresh fenced callbacks and bounded recovery,
strict trace/teardown populations, exact native payload identity, DATA-before-
advertisement order, and nonzero CLI failure with skipped fault/no retry.
Standalone fixture builds Release with -Wall/-Wextra/-Wpedantic/-Werror; syntax/
diff checks pass. Initial standalone namespace/return-code compile errors are
retained as build preparation, not new SDK failures. Two public build-log display
copies remove trailing whitespace only; original local byte hashes are retained
in validation/build-display-provenance.json.

Original live reports count some fresh shutdown-tail callbacks. The separate
[FENCED-RECHECK.md](FENCED-RECHECK.md) narrows counts to the recorded steady-end VM
fence without modifying result.json:30/30 baseline and33/33 fault still pass.
That stricter analysis and packet adapter are source5606cdf. A further
steady-fenced-recheck.json separates qualification/restoration-to-end counts from
the narrower steady-origin counts (29/28 baseline,28/29 fault); it records the
final assessment source hash and does not overwrite the earlier recheck. Later CLI hardening
returns nonzero on a failed baseline/skipped fault; the earlier three CLI calls
returned0 while their manifests correctly said FAILED. Their exit codes/verdicts
are not repaired retrospectively. The new exit behavior is host-tested only.

All corrected native traces are complete and zero-exhaustion: baseline58/58 records,
fault99 operator/101 robot. Native DDS teardown times are12.7..14.2ms, below5s;
all owned native children stop with requested SIGINT/exit0 without forced kill.
Trace ownership and all observed state GUIDs remain stable. Every known fault is
restored, namespaces removed, and no credentials or host networking settings were
created/changed. The fixture ELF changes across declared revisions; all eight
production binary hashes remain unchanged and are independently rechecked after
measurement. Previous full SDK70/ROS41 remain earlier validations; no production
SDK/ROS/provider rebuild or full M2 acceptance.

The original eight-slot [matrix](execution-matrix.json), all failed/skipped
cohorts, source/binary/image provenance, brackets/readbacks, states, traces,
shutdown and packet statuses, corrected closed-capture analyses, tests/builds and
raw hashes are archived. PCAPs/PDML stay local; full inspect/environment dumps and
credentials are excluded. [post-run-runtime.json](post-run-runtime.json) distinguishes
the final standalone probe from unchanged production binaries.

Next: use this controlled mechanism to design a separately frozen ROS/N5 discovery
mitigation/confirmation, and prospectively extend SRT N5 progress coverage. The
original default DDS failure, historical UNKNOWNs and full N5/M3, clock/security/
resource equivalence, cross-host/physical sensor/hardware acceptance remain open.
Do not promote the paced candidate or this UDP-only fixture into a new default.
PR2 remains draft; Intrinsic/M4 is untouched.
