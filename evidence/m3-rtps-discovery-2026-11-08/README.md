# DDS discovery localization from the original N5 captures

The failed default-DDS case has **six decoded command endpoints rather than eight**.
Both captures lack a complete advertisement for the robot HELLO publisher and
its operator-HELLO subscription. Nevertheless, both taps contain the same154 robot
HELLO samples, independently validated with the original generated ROS message
type and process UUID. Archived coordinator diagnostics report0 received HELLOs.
This narrows the observed failure toward DDS discovery/reader acceptance, rather
than an absence of all HELLO DATA on the network or command-journal failure.
It does not uniquely establish a middleware/kernel cause or fix default startup.

This is retrospective analysis of all six original captures from the three DDS
slots in [the N5 progress set](../m3-n5-progress-2026-11-08/README.md). No new live
scenario, selected rerun, changed original verdict, transport default, SDK policy
or production binary. Default/simultaneous remains FAILED; control-first retains
its limited2-command/6-skipped outcome; paced remains a separate candidate.

## Scope and method

[ANALYSIS-PLAN.md](ANALYSIS-PLAN.md) selects all three cases before full decoding.
An isolated analysis image adds tshark4.2.2 (Ubuntu package4.2.2-1.1build3) to the
existing local runtime base. Its immutable image ID, executable/library hashes,
version and command lines are retained. Original PCAPs are mounted read-only;
analysis containers have networking disabled and capabilities removed. This does
not replace the benchmark image or rebuild SDK/ROS binaries.

The adapter uses submessage-scoped PDML, IPv4 reassembly and GUID/sequence identity,
not packet-wide parallel arrays or guessed UDP-port/topic associations. Advertised
publication GUIDs form an explicitly retrospective directory across both captures.
A missing publication binding yields null attributed-DATA counts, never a false
zero. Incomplete fragments and unknown user writers remain separate. INFO_SRC,
ambiguous fields/bindings, malformed complete decodes, unsupported schema versions,
truncation and fixed byte/record/field budgets fail closed.

Original per-endpoint PCAP file/filter/footer populations and SHA-256 hashes are
rechecked before interpretation and remain unchanged afterward. Whole-run capture
intervals differ; no realtime timestamp latency/age authority or physical-wire
claim follows. Cross-capture advertisement presence is by complete submessage
identity (writer, sequence and digest), not a datagram-loss counter.

References for the decoder/wire terminology are the
[Wireshark tshark manual](https://www.wireshark.org/docs/man-pages/tshark.html),
[RTPS field reference](https://www.wireshark.org/docs/dfref/r/rtps.html) and
[OMG DDSI-RTPS2.5](https://www.omg.org/spec/DDSI-RTPS/2.5/PDF).
Installed decoder output and local generated-type checks determine these results;
this bounded adapter is not a general RTPS implementation or conformance claim.

## Complete discovery observations

| Original case | Original verdict | Command endpoint bindings | Operator advertisements at both taps | Robot advertisements at both taps |
| --- | --- | ---: | ---: | ---: |
| System/simultaneous |FAILED before workload|6|4 unique|2 unique|
| System/control-first |Passed bounded gates, limited progress|8|4 unique|4 unique|
| Paced/simultaneous |Passed separate candidate|8|4 unique|4 unique|

For each source, every complete command-topic advertisement identity observed at
one tap is also present at the other; source-only and peer-only complete-identity
sets are empty. Repetitions and destinations are not treated as extra endpoints.
This cannot establish that the live DDS reader processed those advertisements.

In default/simultaneous both full-capture decodes contain:

- Publication and subscription bindings for both command topics.
- The operator HELLO publication, but no complete robot subscription advertisement
  for that topic.
- The operator subscription for robot HELLO, but no complete robot HELLO publication
  advertisement.

The previous startup histories independently retain the sender's missing complete
endpoint matches, receiver's matches, eligible journal/handler/QoS, and0 HELLO
callbacks. They are sampled local diagnostics, not proof of exact packet reception
or continuous callback state between samples. No workload commands were issued.

Both successful candidates supply all eight bindings. Their attributed full-run
DATA submessage observations agree per tap: control-first command topics79/74 and
HELLO topics596/250; paced command topics16/24 and HELLO topics209/235. These
include protocol QUERY/STATUS/retransmissions and full-run startup/drain tails;
they are not command successes, distinct application effects or per-window counts.

## Independent HELLO payload validation

The missing robot publication GUID prevents directory-only attribution of its
user DATA. A second, offline check uses the original generated DdsCommandFrame
ROS deserializer, protocol2, kindHELLO and the original source process UUID.
Reserialization must preserve every semantic byte; a mask derived from generated
field declarations excludes only CDR alignment padding. Require supported CDR1
little-endian encapsulation and exact schema length, permitting only zero outer
RTPS end padding up to alignment4. No guessed adjacent entity ID, partial-layout
byte cast, authentication claim or live callback is used.

Six generated-type checks pass before inspecting captures: valid roundtrip,
wrong owner rejection, nonzero trailing-byte rejection, reflected alignment-padding
acceptance, zero RTPS end-padding acceptance, and non-HELLO rejection.

| Selected captured source / tap | Candidate user DATA | Validated HELLO |
| --- | ---: | ---: |
| Default robot / operator tap |155|154|
| Default robot / robot tap |155|154|
| Paced robot / operator tap |261|235|
| Paced operator / robot tap |230|209|

Default's154 unique identities match exactly across taps by RTPS writer/sequence,
application sequence and CDR digest. Application sequence range19..441, with gaps
retained. Remaining candidate DATA is not classified as HELLO. This establishes
that identifiable HELLO content was captured despite the incomplete discovery
binding; it does not establish callback delivery or why the live reader withheld
it. Original publish/callback counters, capture populations and sparse startup
snapshots have different boundaries and are not equated.

## Fragment observations and strict partial-header separation

| Case | Fragment frames operator / robot | Frames lacking decoded reassembly reference operator / robot |
| --- | --- | --- |
| Default/simultaneous |106 /109|4 /7|
| System/control-first |158 /212|3 /57|
| Paced/simultaneous |0 /0|0 /0|

Final fragment totals match the original independent IPv4-fragment frame counters.
A missing decoder reassembly reference is a capture observation, not a proven
network-drop cause. Even the control-first case contains incomplete groups and
nevertheless establishes all endpoint bindings. The paced candidate also changes
packetization and scheduling; these three cases do not isolate either intervention.

A separate pass disables IP defragmentation **only for all11 preselected default
first fragments lacking reassembly references**. It exposes header-only SEDP writer
sequences and partial topic text. For example, operator frame426 contains partial
operator-HELLO publication sequence12 and sender-state sequence13; frame594 contains
partial robot-command subscription sequence10 and robot-HELLO subscription11.
These source-tap groups lack a complete reassembly in that capture, while complete
advertisements for the corresponding operator endpoints occur elsewhere. Robot
partial groups include batched early discovery/service announcements. They do
not uniquely identify the missing robot HELLO announcement's lost fragment.

Truncated bodies can produce expected decoder expert errors in this explicitly
separate pass. Partial topic text never enters the complete GUID directory and
never rescues a missing advertisement. Multiple SEDP samples can share a fragmented
datagram; source/peer taps and DDS acceptance are distinct stages. Exact qdisc,
bridge, socket, reassembly or middleware loss/drop branches remain unproven.

## Corrections, validation and provenance

[SCHEMA-REVISION.md](SCHEMA-REVISION.md) and preserved adapter failures distinguish
analysis corrections from original workload failures. The initial adapter used
the wrong INFO_DST field; ff06a7a then rejected HEARTBEAT's two sequence-range
values as an ambiguous DATA sequence. Corrected830fc3a completed the three decodes,
but intermediate reporting lacked withheld counts for unbound topics and omitted
first fragments whose pinned boolean show value is True. Final reparses correct
both without modifying packet inputs. A new digest regression also initially had
two test-fixture errors; the missing synthetic digest was supplied.

Generated-type validation first stopped at a missing container working directory,
then its raw-byte equality self-test correctly exposed unspecified serialization
padding. No payload claim was accepted from either failure. The final reflected
semantic comparison passes six checks and the four captured-source validations.
Tool preparation's invalid digest and BuildKit local-digest resolution failures
are preserved as labeled display copies with CR/LF and trailing whitespace normalization,
original local byte hashes retained; preparation then succeeded from the existing local
image via an owned container. These are tooling failures, not new N5 scenarios.

255 host tests pass, including submessage/INFO_DST scope, HEARTBEAT ranges, GUID
ambiguity and known-missing advertisements, fragment boolean handling, hard budgets,
truncation and strict partial-header withholding. A separately encoded minimal
RTPS/PL-CDR packet decodes through the external tshark to its expected topic/GUID/
sequence. Syntax/diff checks pass. Final full analyses use438ae9d's adapter;
partial headers use34d06a4. Per-artifact commit/SHA provenance distinguishes
intermediate stages and generated-type runs.

All eight production runtime hashes and generated message-library hashes remain
unchanged. Prior SDK70/ROS41 remain the last full validations; no new SDK/ROS
build or full M2/M3 acceptance run. All owned analysis/preparation containers were
removed. Local tool-image cache remains available for reproducible offline use.

`final/` is the corrected descriptive analysis; `typed-validated/` and
`partial-headers/` are separate evidence routes. `adapter-failures/`,
`schema-failures/`, `intermediate/` and validation logs retain earlier rejected or
superseded interpretations with their original metadata. Full PDML, raw captures,
opaque payloads and preparation/source artifacts stay local with hashes. Public
artifacts contain selected metadata, decoder/runtime provenance and summaries;
no journals, credentials, full environment/inspect dumps or new physical-age claim.

Next: freeze a controlled discovery-fragment/reliability loss-and-recovery test
with independent capture and real DDS endpoint/callback observations before
changing any default. Preserve the paced candidate separately and define longer
SRT N5 progress coverage. This analysis does not replace that live causal test,
resolve historical UNKNOWNs, qualify full N5/M3, or establish transport superiority.
PR2 remains draft; Intrinsic/M4 is untouched.
