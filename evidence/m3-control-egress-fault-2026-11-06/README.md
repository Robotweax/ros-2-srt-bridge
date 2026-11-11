# CONTROL-only egress fault harness — 2026-11-06

The single planned execution **failed in the harness validator**. No verified
six-second fault/restoration or provider-versus-egress signature is claimed.
The historical N5 initiating cause and full M3 qualification remain open.

The prospective [plan](diagnostic-plan.json) specifies one 45-second N0 run,
seed 1701, with a six-second operator→robot CONTROL drop about 15 seconds after
observing the measurement-start marker. A dedicated preference-49152 IPv4 UDP
u32/gact filter matches robot destination /32 and operator source port 10080.
SENSOR port 10081 is excluded by construction. This is an injected fault, not a
baseline or complete N4 command-phase qualification.

Source commit `b0e2204` was frozen before execution. All 178 manifest source hashes
match that commit, and eight runtime hashes match the previous tested SDK/ROS
build before/after. The pinned SocketRegistry source assigns the SDK handle to
protocol_socket_id; that association is constrained to the verified archive
fingerprint and remains routing evidence, not authenticated identity.

## Original execution

Local run: `.local/m3/20261106T203905001506Z`.
The tc filter installed successfully. The preference-scoped `tc -j -s filter
show ... pref 49152` output omits `pref` in all three returned entries. The
validator incorrectly required that field, raised `unexpected CONTROL filter`,
and aborted before scheduling timed restoration. At the initial readback the
action had zero drops; this does **not** establish its lifetime drop count.

The immutable [original manifest](failed-run/run.json) also retains secondary
errors: absent endpoint measurements and missing final command/provider status.
Those observations are incomplete and are not reconstructed. Both containers
and the internal network were removed with exit code zero. There was no second
execution after the fix. Do not reinterpret this failure as a passed fault,
command-safety, capture or qualification result.

## Fix and validation

The parser now accepts omitted preference only within its fixed
preference-scoped query; an explicitly conflicting preference, unexpected
protocol/kind, ambiguous action or invalid counters still fails. The actual
captured readback is a regression fixture. Install validation failures now
remove the filter before propagating the error. Final statistics failures also
remove it in a `finally` block and verify the restored readback. Both failure
paths have focused tests. Outer owned-container teardown remains the fallback.

**112 host tests passed before execution; 115 passed after the fix.** Syntax
checks pass. SDK, ROS, provider and protocol policy are unchanged; no fresh
SDK/ROS/M2 rerun is claimed. The previously recorded 69 SDK and 36 ROS tests
apply to the unchanged runtime, not to live validation of this new harness.

The new read-only analyzer selects recent pre-fault socket identities per peer,
requires complete native v2/common-clock coverage and the pinned archive,
maps the old UDP tuple/destination socket, and computes only adjacent available
same-identity provider deltas with both reads entirely inside guaranteed active
VM brackets. It checks reverse CONTROL, SENSOR observations and post-restoration
CONTROL separately. This logic has focused tests but **no successful live fault
validation yet**. The failed run lacks its required complete inputs.

[Findings](findings.json), original diagnostic logs, tc readbacks/install bracket,
cleanup logs, source/runtime provenance and local raw-artifact SHA-256 identities
are retained. Packet payloads, native prefixes, journals/WALs, clock samples and
resource samples stay local. No credentials or inspect/environment dumps are
published.

Next: prospectively validate the corrected harness in a fresh explicitly bounded
experiment, retaining this failure. Then use a verified signature for future N5
triangulation. No timeout/policy change or historical-cause attribution follows
from this attempt. PR #2 remains draft; Intrinsic/M4 is untouched.
