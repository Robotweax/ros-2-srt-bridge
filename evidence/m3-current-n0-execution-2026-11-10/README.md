# Current-build N0 seed1701/300s execution — 2026-11-10

**FAIL at robot bridge startup capability attestation. One attempt, zero retries.**
The exact prepared N0-combined-1701 case was explicitly authorized and invoked
once on freeze1c15050c5208. Driver exit1; no tuning, rebuild, source/helper/gate
change, completed N3 rerun or other campaign case. All28 other unexecuted cases
remain disabled. M3 stays open, PR2 draft and M4 untouched.

## First retained failure

Robot Diagnostic.start_bridge raises `role capability set differs from declared
scope` at `require_role(status(self.bridge.pid),0)`. The traceback is retained.
Both bridge pre-exec JSON records show zero effective/permitted/bounding/
inheritable/ambient capability sets and NoNewPrivs1. The operator additionally
records its bridge identity; the robot does not reach that identity write.
The actual /proc status values used by the failing call are not retained, so
these records do not establish the later observed values or a unique cause.
No startup permission or gate was changed or waived.

The 300s source measurement never starts: measurement-start.json and complete
operator/robot results are absent. The normal shutdown-ready/release markers,
observer readiness and strict case assessment are absent. No observer is created
or armed. There is no current-build N0 coverage PASS, clean child-exit claim,
qualified shutdown result or complete measurement/capture population.

The failed runner also reports unreconciled tcpdump counters, missing/duplicate
final command status and missing/duplicate provider final status. These remain
recorded secondary failures; none is waived or promoted to qualification. Partial
operator stage output is retained without a lifecycle/socket coverage PASS.

## Cleanup and integrity

The frozen driver's failure path records owned emergency cleanup. Removal of
both owned lab containers returns0; observer/volume are absent and network removal
reports already absent. Final independent Docker metadata verifies both lab
containers, network, observer and output volume absent and credential deleted.
This is verified object absence after failure, not normal shutdown qualification.

Source, all frozen inputs, preparation public hashes,14 matched current entries,
preserved13/full earlier build chain and87 native inputs verify unchanged. All
retained raw indexes, including the fresh N3 nine-case PASS and historical failed
cohort, verify. The new closed raw archive has64 files/387,888bytes; hashes are
in local-artifact-hashes.json. Public copies include the exact authorization,
execution/cohort records, failure/pre-exec/identity/partial-stage/capture/cleanup
logs, gate summary and final integrity/absence report.

No tests or native builds ran during this attempt. Prior511+8 offline PASS results
retain their preparation-only scope and did not predict live startup success.
The preparation remains immutable; this separate execution record preserves its
failure. No retry, replacement freeze, additional experiment or later case is
queued. Retained-evidence diagnosis is the next unresolved step.
