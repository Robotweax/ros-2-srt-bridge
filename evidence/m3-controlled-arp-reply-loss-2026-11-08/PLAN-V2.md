# New scoped recorder-span revision, original V1 remains failed

V1 clean-pass retains FAILED native/PCAP full-ARP identity comparison; its loss
slot remains NOT_EXECUTED. Closed raw source hashes verified before this change.
One unmatched observed packet is gratuitous ARP with senderIPv4==targetIPv4,
outside the requested cross-peer reply path. No unique reason for its one-recorder
presence is inferred from realtime timestamps or repaired retrospectively.

New frozen source, fresh namespaces, two new slots once each: clean-pass and
reply-drop-restore. Keep all original PIPE/verdict, initial ABSENT dynamic peers,
N0 roots,1.15/1.25s snapshots,1.35s removal/<2s timing,3once-only original UDP plus
one distinct fresh control, full native and file/filter/kernel population gates,
source/runtime/cleanup requirements and stop-on-first-failure/no-case-retry.

Prospective cross-recorder identity scope is exactly ARP operation1/2 between the
two owned peer IPs plus all labeled synthetic UDP. Native ownership/MAC/packet-type
checks stay strict. Preserve every other ARP record in separate per-recorder
background tables, with an explicit equality flag; never silently discard it or
use peer-scope equality to rescue a file/footer/kernel/native population failure.
This is a new narrower synthetic fixture, not an acceptance of V1 or its unexecuted
fault case. No recorder/runtime/production/default tuning, cache mutation, extra
seed or SRT/ROS/N5 qualification. Archive both cohorts and revision lineage.
