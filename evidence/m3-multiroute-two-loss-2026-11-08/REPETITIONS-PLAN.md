# Separate two-loss repetitions with observed child shutdown

Precondition: the separately planned lifecycle diagnostic5d9b9f3/seed1701 passed
with complete source/sample footers, all three child processes live before SIGINT,
clean exit0 without kills, exact selected two-loss gap and all original gates.
This does not determine the missing-footer cause in original cb2468b/1701, whose
FAILED verdict and skipped original2903/4211 cases remain unchanged.

Freeze this plan before these two fresh executions, in order, once each:

1. `python3 tools/m3_ros_multiroute.py --output .local/m3-multiroute-two-loss/lifecycle-2903 --capture --losses 2 --seed 2903`
2. Only after1 passes all gates:
   `python3 tools/m3_ros_multiroute.py --output .local/m3-multiroute-two-loss/lifecycle-4211 --capture --losses 2 --seed 4211`

Stop at first failure; no retry or selector changes. Same Python code, pinned
seven runtime hashes, ten-second source window,200/50Hz measured within1%, fixed
SDK messages7/8 in row1 spanning both routes, strict independent capture/trace/
hash/session/QoS/age/empty-pipeline/conservation gates as PLAN.md. Exactly two
classifier drops (one per rule), selected source keys absent at both taps, parity
present, exactly selected receiver-decision gaps and no selected typed observation,
later typed progress on both routes before cutoff. No permanent absence or generic
irrecoverable-loss counter claim. Include explicit child-shutdown reports from
DIAGNOSTIC-PLAN.md; any preexisting/nonzero exit, missing footer, timeout or kill
fails the case even if its measurement counters otherwise balance.

These are new independent-start repeatability fixtures under observed cleanup,
not continued/rescued cases of the stopped original cohort. N0 qdisc seeds affect
no random impairment here; do not infer random-loss coverage, performance parity,
causality or superiority from different local BUSY/DDS/replacement populations.
Retain all stages/IDs explicitly and do not infer individual replacement stages
from aggregate counters. Three short passing base seeds (including the separate
1701 diagnostic) would still not complete baseline/one-loss seed repetitions,
long-window N3, N4/M3 or any physical-age/security/resource/hardware acceptance.

Retain original logs/verdicts, separate source provenance, shutdown records,
metadata/hash/capture status, inventories and raw-artifact hashes; exclude raw
captures/prefixes/journals/resources, credentials and inspect/environment dumps.
Remove all owned containers/network/passphrases. No SDK/ROS/provider/runtime
change or rebuild; previous SDK70/ROS41 and current Host218 remain the full
validation references. Intrinsic/M4 remains untouched, PR2 stays draft.
