# Authoritative sender receipt and journal reconciliation

A command discarded before SDK handoff can now update its exact sender journal
row after the original endpoint job has finished. The transport publishes an
opaque receipt on the original one-use admission proof. The coordinator retains
at most64 receipts and submits an abandoned receipt to its minting worker once;
BUSY preserves the capability. Lossy diagnostics never authorize this mutation.

Only matching sender `local_queued`, revision0, becomes provisional
`UNKNOWN/reconcile_required`, with original session, origin, deadline and invalid
result preserved. No EXPIRED/success, new ticket, replay or unrelated-session
invalidation is introduced. Existing query-first UNKNOWN handling remains;
authoritative peer acceptance/final results survive a delayed receipt. A refused
unsubmitted ticket uses the same exact-row path. Real session loss retains its
existing session-wide invalidation contract.

Worker generation identity, peers, owner epoch, route, payload/hash, session,
source epoch, origin and deadline fence receipt consumption. Empty, unclaimed,
SDK-accepted, foreign, stale and reused receipts are rejected. Private worker
IPC is now version4/operation11; old workers fail closed. Rebuild SDK consumers,
supervisors and ROS workers together. SRT/protobuf/ROS schemas and the provider
are unchanged. A full tracking table returns BUSY before durable admission.

## Verification

SDK81/81, ROS41/41 and host399/399 pass on the pinned Linux amd64/Jazzy image.
See [validation.json](validation.json), the complete [logs](validation/),
[closed records](closed-journals.json) and [binary chain](binary-verification.json).
All1101 earlier raw hashes and28 new fixture files verify unchanged; the provider
pin/archive and all earlier installed baselines are preserved.

Fresh IPv4/IPv6 fixtures use a default-false, C++ test-only handoff hold and real
peer disconnect before the original5s deadline. No ROS parameter, CLI flag or
environment setting exposes the hold. Raw-owner tests isolate exact-row mutation
from session invalidation; endpoint tests observe operation11 and UNKNOWN, then
reconnect/query without execution. SDK-accepted receipts never regress on close.
A paused real worker exercises bounded saturation/BUSY, one-use consumption,
foreign worker rejection and replacement-worker generation rejection. The
64-entry coordinator test proves the65th command leaves no durable row.

Journal tests cover wrong-context/payload receipts, idempotence, UNKNOWN followed
by peer acceptance and final success, delayed receipt preservation, restart owner
fences and storage failure. Closed raw journals also retain the deliberate
replacement-worker recovery: unrelated queued rows become UNKNOWN on recovery,
separately from the in-process assertion that exact-row reconciliation preserves
them. The accepted-only fixture intentionally remains local_queued: SDK handoff
is not peer execution proof.

The initial focused native run failed because the fixture queried while
disconnected, which the existing endpoint API refuses. The fixture now reconnects
before querying. A subsequent journal test failed because the fault injector had
not been armed (`writes_before_failure` remained disabled); corrected to0.
Both failure logs are retained. The initial colcon test invocation selected the
enclosing SDK package because it lacked `--base-paths ros2`; the corrected scoped
invocation passes all41 ROS tests without rebuilding. Its invocation failure is
also retained. These are test corrections; runtime policy was
not tuned. Validation results and binary provenance accompany this report.

## Scope and next delivery gate

This closes the transport-to-journal status-delivery gap for proved local
abandonment. No live clock-deferral/deadline-drop cohort was run and no N5 result
is claimed for this new build. Historical118 remains UNKNOWN/reconcile_required;
its journal was not opened, expired or replayed. Historical34/98/12 and stopped4211
keep their prior verdicts. Remaining M3 work is actual ROS SENSOR N3 freshness/
repair qualification, loaded DDS discovery/comparison and consolidated acceptance.
PR2 stays draft; Intrinsic/M4 is untouched.

New isolated SDK/ROS prefixes are `install/bridge-sender-reconcile` and
`install/m3-sender-reconcile-ros`. Explicit `--runtime-layout sender-reconcile
--skip-build` verifies the new matched build and every preserved baseline in the
start/sender/probe chain. Default paths stay fixed. No clock/network/rate/budget/
queue/provider tuning, forced expiry or historical replay was performed.

Fourteen closed SQLite fixtures and their owner files stay local under
`.local/m3-sender-reconciliation-calibration-2026-11-09`; all28 hashes and immutable
decoded records are published. Validation logs retain complete text with trailing whitespace stripped; exact
originals remain local with hashes in `validation-log-hashes.json`; databases contain
fresh synthetic identities only. Builds and broad tests did not overlap the
retained native fixture capture. Earlier evidence is preserved and rechecked.
