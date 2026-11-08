# Retrospective DDS discovery analysis

Analyze the six original per-endpoint PCAPs from the three DDS slots frozen in
57f415b, archived in m3-n5-progress-2026-11-08. This is explicitly retrospective;
no rerun, changed original verdict, new transport default or application outcome.
Select all three slots before full decoding, not a favorable packet subset.

Use isolated Wireshark/tshark4.2.2 with IPv4 reassembly, record actual package,
binary/library hashes and immutable analysis-image ID. Mount originals read-only,
network disabled during analysis. Benchmark/runtime image remains unchanged.
Only qualified existing per-endpoint file/filter/footer populations and matching
original raw hashes authorize decoded observations. No realtime timestamp age or
cross-endpoint latency authority; whole-run capture intervals differ.

Extract submessage-scoped source GUID/writer/reader/sequence, discovery topic and
endpoint GUID from DATA/decoded fragment payloads. Do not pair flat field arrays
across submessages. Record fragments, expert errors and unsupported forms rather
than fabricating complete advertisements. Attribute user DATA to a topic only
when GUID binding is unambiguous across the two captures; bind by advertised
writer GUID, not by UDP port or topic string anywhere in a packet. Preserve
publication/subscription differences and source/peer capture observations.

Inspect all four command/HELLO topics: operator, robot, operator_hello,
robot_hello. Match repeated SEDP advertisements by source writer GUID/sequence
and raw submessage digest; count source/peer presence without interpreting
missing capture observations as proven kernel/application loss. A packet may
be tapped without middleware accepting/reassembling/processing its sample.

Validate the adapter with one independently encoded minimal RTPS/PL-CDR packet
fixture and pinned tshark decoding; host regressions must reject GUID ambiguity,
malformed/oversized/truncated PDML and wrong submessage association. An offline
known-missing advertisement fixture tests withholding rules, not live discovery
causality. Any live known-loss intervention needs its own frozen plan.

Archive selected metadata and raw-input/decoder hashes, not PCAPs, full PDML,
user data, host metadata, journals or credentials. Keep the default FAILED case,
control-first limited progress and paced candidate separate. If the evidence does
not uniquely localize the failure, retain that limitation and do not change
journal/replay/deadline/session semantics. No full N5/M3 or superiority claim.
