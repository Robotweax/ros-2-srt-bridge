# Default DDS cold start: control passes, loaded case fails before measurement

Frozen plan/source `f54f783` executed exactly two fresh cases on the matched
sender-reconcile SDK/ROS build. N0 passes8/8 commands/effects; N5 fails sender
readiness before measurement. Cohort exit1; no retry, changed startup order,
fragment cut, pacing candidate or new tracer. Default DDS settings are unchanged.

| Case | Nominal measurement | Workload outcome | Capture outcome |
|---|---:|---|---|
|System DDS simultaneous N0/1701|15s|PASS,8/8 succeeded/effects,0 skipped offers|PASS, robot7282/operator7252 records|
|System DDS simultaneous N5/1701|60s requested, not started|FAIL at45s sender-readiness wait;0 submitted commands/effects|PASS, robot7294/operator7312 records|

This is a failed workload comparison case, not a failed capture. The60s is the
requested observer window; it was never measured. Both fresh N5 journals are
empty, and the measurement-start marker is absent. The standard simultaneous
fixture starts the simulator before command readiness, so unqualified warmup
traffic existed; no steady-window sensor/command result is inferred from it.

## Observed loaded startup

Both complete startup timelines contain46 snapshots, one process epoch per
coordinator. No sampled complete operator endpoint match or readiness occurs.
These are local RMW match/callback observations, not packet delivery proof:

| Last observation | Operator | Robot |
|---|---:|---:|
|CONTROL publishers / subscribers|0 /1|1 /1|
|HELLO publishers / subscribers|0 /1|1 /1|
|HELLO sent / received|434 /0|438 /407|
|Journal ready / handler ready / QoS verified|true /true /true|true /true /true|
|Coordinator failed / ready|false /false|false /false|
|Commands / effects|0 /0|0 /0|

The sampled maxima also retain0 operator robot-side publishers and0 received
HELLOs, rather than just a final transient value. Robot receiving operator HELLOs
and matching endpoints does not establish the reverse direction or mutual ready.
The robot scenario aborts after the operator's sender-readiness timeout.

The N5 root/child configuration stays512kbit/s with16-packet children; dynamic
neighbors and default DDS transport remain. The128000bit/s competitor is observed
live189 times; its whole-run offered rate128024.432286bit/s over48.182803s passes
configuration/load checks. This is offered load, not receiver delivery bandwidth.
No kernel-drop subtraction or unique fragment/ARP/qdisc/CPU cause is assigned.

The earlier native large-metadata continuation-loss mechanism and contradicted
ROS N0 transfer hypothesis retain their scopes. Another offline RTPS decode would
not change this acceptance decision, so none was run. The current result confirms
that default DDS loaded cold start remains unqualified on this matched build;
it does not prove that the original failure has one identical cause.

## N0 control and qualification limits

The actual source-enable interval is15.097493797s. IMU3019 produced/3005 accepted
callbacks, joints755/755; source rates199.966964/50.008300Hz, all within1%.
Fourteen missing IMU callbacks remain explicit before-callback loss, not isolated
network loss. No stale/invalid/clock-rejected callbacks in this window; qualified
shared-VM realtime age histograms have rounded-up maxima6ms/21ms. These are not
SRT conservative bridge-ingress age bounds or physical sensor ages.

All8 commands close matching sender/receiver success journals with valid original
results/generations and eight device effects. Original5s sender budget and earlier
receiver start fences are checked by the existing strict read-only journal audit.
Maximum terminal observation209.008667ms includes service/transport/poll waits;
no latency or2s-service guarantee follows. No source-slot trace is configured in
this DDS fixture, so its aggregate cadence cannot satisfy the failed N3 zero-skip
source contract. No SRT superiority, security/resource parity or matched-window
performance result is inferred from these separate controls.

## Reproducibility and cleanup

Host407/407 passes before live. Exact SDK81/ROS41 binary qualification is reused,
not re-run; no native rebuild. Python runner/scenario/load paths now explicitly
select and verify the matched ROS prefix for both simulator and DDS coordinator;
nonbaseline rebuild requests fail before Docker work. All112 frozen Python source
hashes, full matched/preserved runtime/archive chain and provider remain fixed.
No tests/build/heavy unrelated analysis overlapped capture.

[execution.json](execution.json) retains original harness/outer verdicts and
closed command proof; [gates.json](gates.json) publishes compact startup/capture/
clock/command/workload/shutdown selection. All146 new raw files are retained with
hashes in [local-artifact-hashes.json](local-artifact-hashes.json). Four fresh
closed journals are read immutable: N0 contains8 matching successes per side;
N5 contains no entries. Raw packets, resources, detailed typed/timeline streams,
full source manifests, inspect/environment dumps and journals stay local. No
credential was created for this DDS-only cohort.

All6 controlled native children exit0 without forced kill; both scenarios exit
before namespace teardown, including the failed case. All4 owned containers and
2 networks are removed. The full PCAP file/footer/kernel populations reconcile
with zero kernel drops and no unaccounted frames. Counts differ between taps;
that difference is not an exact packet-loss count.

The failed N3 cohort, old DDS failures, historical118 UNKNOWN and old34/98/12/
stoppedN5/4211 remain unchanged. No tuning, forced expiry, command replay or
prospective acceptance-rule relaxation. PR2 draft/M3 open/Intrinsic-M4 untouched.
Next is the consolidated [M3 acceptance review](../../M3_ACCEPTANCE_REVIEW.md),
not another automatic cold-start experiment or a requirement to make DDS pass.
