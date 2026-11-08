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
