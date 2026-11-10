# Corrected-readiness N0 execution — 2026-11-10

**FAIL at launch registration, before the300s measurement. One attempt, no retry.**

User explicitly authorized the new N0-combined-1701/300s freeze7b5c7d922206 with
launch-specific readiness, stop first failed gate, no tuning/automatic retries,
other28 cases disabled. The unchanged frozen driver was invoked once and exited1.
No source/helper/gate/build or policy change occurred. M3 stays open, PR2 draft,
M4 untouched; completed N3 is not rerun and old failures remain unchanged.

## Failure and retained snapshots

Both roles fail register→stable with `KeyError: 'ppid'`. The first recorded
registration snapshot is operator bridge PID111, followed by robot wrong-hash
negative launch PID133. Both identity brackets contain only pid/start_ticks/state.
Their permissions snapshots include PPid75 and all capability/NNP/seccomp fields.
Unique per-launch tokens/paths and separate parent-failure files were retained.
The new failure capture therefore worked, but successful launch registration did
not occur. The zero-capability attestation gate was not reached.

The registration snapshots precede wrapper reduction and contain nonzero caps/
NoNewPrivs0. Registration does not require zero capabilities at that phase; those
values are retained observations, not this failure's cause or evidence of later
privileged bridge execution. No readiness acceptance, qualified application
startup or successful exec is claimed.

Static retained-source inspection explains the schema mismatch: launch_readiness
imports `identity` from the unqualified module name shutdown_observer. The runtime
scenario puts tools then ROS demo scripts before the evidence-local observer
helper. ros2/robotweax_srt_bridge_demo/scripts/shutdown_observer.py returns exactly
the three observed identity fields; the intended evidence-local helper also
returns ppid/name. Offline tests put the evidence helper ahead of ROS scripts and
therefore exercised the richer schema. Module __file__ was not logged in the
failed process, so module origin is a source/import-path inference supported by
the exact retained schema, not a separately recorded runtime module fingerprint.
No new experiment or reproduction was run to reach that conclusion.

This is another harness integration defect missed by the offline tests. No SDK
transport failure, capability-reduction syscall failure or privilege waiver is
inferred. The frozen revision remains unchanged; no fix was attempted here.

## No coverage credit or advancement

Neither robot-ready nor measurement-start exists. Full measurement results,
normal shutdown-ready/release, observer readiness and strict case assessment are
absent. No observer was started or armed. There is no N0 measurement/capture/
shutdown qualification. Secondary tcpdump population reconciliation and missing
command/provider final-status failures remain recorded, without waiver.

Both roles were concurrent parts of the same single startup attempt, not retries
or additional campaign cases. The frozen failure path records cleanup; the
emergency owned-object checks/removals are also retained. Final independent Docker
metadata confirms both lab containers, network, observer and observer volume
absent and the fixture credential deleted. This is object absence after failure,
not a clean child-exit/shutdown qualification claim.

## Integrity and next boundary

Frozen source/inputs/corrected harness/current14/preserved13/full build chain and
native87 inputs remain unchanged. All prior raw/public indexes verify, including
the original failed N0, original N3 failure and new N3 nine-case PASS. The closed
new archive has57files/286,585bytes, bound by local-artifact-hashes.json. Public
copies retain authorization, preflight/driver log/cohort, role tracebacks, exact
per-launch failure snapshots, workload/capture/cleanup records and final integrity
report. No tests or native builds ran during measurement/startup.

A future correction needs explicit identity-helper binding and regression
coverage using the real runtime import order. No code change, new freeze,
automatic retry or further experiment follows this failed run. Other28 campaign
cases stay disabled; N0 remains unqualified and full M3 acceptance remains open.
