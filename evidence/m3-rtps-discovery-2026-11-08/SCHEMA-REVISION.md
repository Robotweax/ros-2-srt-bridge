# Decoder adapter corrections before accepted analysis

The uncommitted initial adapter rejects the first full operator PDML with missing
`rtps.sm.guidPrefix`; installed4.2.2 uses `rtps.guidPrefix.dst` for INFO_DST. Its
failed analysis metadata and original adapter hash are retained. No robot decode
or accepted conclusion followed from that attempt.

Sourceff06a7a passes251 host tests and independent encoded DATA validation, but
all three selected full analyses reject HEARTBEAT with ambiguous seqNumber.
Pinned PDML uses the same field name for its first/last sequence range (observed
1 and4), unlike DATA's single sample sequence. This is an adapter assumption,
not malformed RTPS or a DDS failure. All failed analysis artifacts remain retained.

Correct only DATA/DATA_FRAG sequence attribution; HEARTBEAT/ACKNACK retain raw
submessage identities without pretending a range/set is a single DATA sequence.
Add a two-value HEARTBEAT regression and explicit complete-advertisement presence
sets across source/peer captures. Repeat deterministic offline decoding of the
same six hash-verified originals under the corrected adapter, with new output
paths and source provenance. No live scenario reruns, input mutation, changed
original workload verdict or retrospective cause invention.

The corrected830fc3a adapter completes all three original analyses, but its new
presence-set regression initially has two errors because the synthetic dictionary
fixture lacks the newly required raw-submessage digest. The test fixture now
supplies that digest;252 host tests pass. This is a test-data correction, not
changed packet input or measured runtime. Failed test logs remain preserved.

Those completed analyses expose a separate reporting limitation: zero attributed
DATA for a missing publication GUID must be withheld, not reported as observed
zero. Final rechecks use null counts plus publication_binding_available=false
for that case and retain unassembled IPv4 fragment metadata. Earlier intermediate
outputs remain separately identified. Reparse the same already decoded PDML;
no new live execution or changed original verdict.

For any unbound command-participant DATA, independently inspect the captured CDR
using the original generated ROS DdsCommandFrame deserializer, exact reserialization,
protocol2/HELLO1 and original source process UUID. No guessed HELLO GUID from
adjacent entity IDs, partial-layout byte cast or execution/replay is authorized.
Run four positive/negative generated-type checks first, then inspect the failed
robot source at both taps and both paced HELLO directions as positive controls.
This is offline payload validation, not authentication or a subscription callback.

The first generated-type self-test stops before Python because the isolated CLI
container was not given /workspace as its working directory. Absolute tshark
inputs were unaffected; relative ROS setup paths were unavailable. Record that
setup failure and add explicit working-directory selection. Use a new typed
validation output directory; require its four checks before payload inspection.
No typed claim was accepted from the failed setup invocation.

The generated-type self-test then correctly rejects the proposed raw-byte equality:
serialization contains unspecified alignment bytes (observed306-byte message,
roundtrip differences only in padding). Replace guessed equality with a mask
computed from generated field declarations: compare every semantic byte after ROS
deserialization/reserialization, require CDR1 little-endian header and exact schema
length, and allow only zero outer RTPS end padding up to alignment4. Add six
positive/negative generated-type checks, including altered alignment padding.
No captured payload claim was accepted by the failed byte-equality self-test.

Fragment reporting also must accept pinned PDML boolean show=True, not just1.
A first fragment has offset0 plus MF=True; earlier intermediate counts omitted it.
Add that regression, and reparse the same six PDML inputs to final fragment totals.
This changes descriptive fragment metadata, not input population or original verdict.

After corrected reassembly metadata, inspect only default-run first fragments
explicitly lacking a reassembly reference in the original full-capture decode.
A separate header-only adapter uses a new tshark pass with IPv4 defragmentation
disabled for those preselected frame numbers. Its output never establishes a
complete advertisement or GUID binding, including when a partial topic parameter
is visible. Truncated-body expert errors are expected here. Inspect all4 operator
and7 robot incomplete first fragments, not a selected favorable topic. Preserve
the distinction between source-tap fragment, peer-tap observation, complete DDS
advertisement and actual application callback. This is retrospective localization,
not a new live known-loss intervention or a unique kernel drop-stage proof.
