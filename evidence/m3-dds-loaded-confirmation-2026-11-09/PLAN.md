# Default DDS loaded cold-start confirmation

Purpose: decide whether the current matched ROS build completes default DDS
endpoint discovery and bounded combined sensor/command progress under N5. The
standalone4096-byte metadata/UDP native fragment mechanism already failed to
transfer to unburdened ROS in the earlier fragment-cut case; do not repeat that
experiment or infer a unique fragmentation cause. No new fault or tracer.

Frozen sequence, once each, stop at the first failed gate/exception, no retries,
startup-order fallback, pacing candidate or automatic extension:
1. DDS system/simultaneous N0 seed1701,15s observer measurement.
2. DDS system/simultaneous N5 seed1701,60s observer measurement, only after1 passes.

Use exactly calibrated sender-reconcile SDK/ROS81/41 installations and pinned
Linux amd64/Jazzy image. Python-only explicit matched layout/prefix selection,
cohort policy and host guards. Both DDS coordinator and simulator must use the
selected ROS prefix; preserve all earlier installed builds/provider. No rebuild.
Default system DDS transport/environment, simultaneous cold startup,200Hz IMU/
50Hz joints, Reliable journaled commands every2s with one pending and original5s
budget, existing250ms callback-age filter/1.5s HELLO lease/45s discovery waits.
N5 uses existing512kbit/s roots,16-packet children and measured128Kbit competitor;
dynamic neighbors remain default. No tuning, lease extension, forced expiry or
historical118 replay/resumption of stopped cohorts.

Acceptance gates: original harness success; matching image/layout/profile/seed/
duration; complete reconciled full PCAP populations/no kernel loss and clean
controlled shutdowns of all3 owned native children; both startup timelines
complete and ready observed; clock estimates qualified; both actual source rates
within1% of targets and >=1 accepted typed sample/route, invalid/clock-rejected0;
no unresolved/not-admitted/unsuccessful command attempts and matching closed
journals/effects through existing strict command_progress proof. N0 must confirm
>=8 commands with0 skipped command offers. N5 requires>=1 confirmed command and
no failed attempts; skipped offers and long gaps remain explicit, so passing is
bounded progress rather than2s continuous service or full N5 qualification.
N5 competitor must be observed live and verify actual offered-load configuration.
The source-enable fence can differ from nominal observer duration; report it.
No source-slot trace exists in this DDS fixture: do not claim zero skipped source
slots or use its aggregate cadence to repair the failed N3 zero-skip gate.

No tests/build/heavy unrelated analysis during live capture. Common VM clock/
namespace proof retained; DDS realtime age estimates do not equal SRT conservative
interval bounds. Standard existing startup timelines and captures suffice; no
new packet/ARP observer. If cold discovery fails, record sampled match/HELLO/
readiness classification and closed empty/unresolved journals, then stop. A
bounded offline RTPS decode is optional only if it changes the acceptance decision;
existing fragmentation observations do not establish a historical unique cause.

Outcome selects the consolidated acceptance report/explicit remaining gates,
not another automatic diagnostic cohort or new default. Existing SRT loaded
results are context, not contemporaneous matched sensor/security/resource/age
comparators. Keep original N3 audited FAIL, old DDS failures and historical command
uncertainty. PR2 stays draft/M3 open/Intrinsic-M4 untouched.
