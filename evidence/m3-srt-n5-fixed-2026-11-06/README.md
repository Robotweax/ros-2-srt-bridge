# Fixed-command-runtime N5 cohort: failed diagnostic completeness

A new, frozen plan at ffd4fb2 (command fix 899a6eb) specified three sequential
300-second SRT N5 executions, labels 1701/2903/4211. Command and recorder diagnostics
were enabled explicitly in addition to native monotonic capture. Fresh owned
endpoints, fixed source/selected-binary/installed-script inventories, no tuning,
retries or replacement. N5 has no stochastic impairment; labels do not identify
independent random-loss samples. Complete M3 acceptance is not claimed.

| Label | Overall case status | Successes/effects | Expiry / unresolved / nonadmission | Skipped slots | PCAP kernel drops, robot/operator | Operator trace retained/attempted |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| 1701 | Passed | 115 / 115 | 0 / 0 / 0 | 35 | 0 / 0 | 359 / 359 |
| 2903 | **Failed diagnostic completeness** | 129 / 129 | 0 / 0 / 0 | 21 | 0 / 0 | 397 / 398 |
| 4211 | **Not executed** | — | — | — | — | — |

The second case completed its application window, captures and journals but lost
one diagnostic observation. Sequence 235 is absent; the final dropped counter is
one. Do not reconstruct a missing record or relabel the case passed. Both robot
incarnations retain all four lifecycle records. The shared try-lock design could
drop on either lock contention or a full buffer, and its combined counter cannot
uniquely establish which mechanism caused this loss. The original run manifest,
failed study, plan and independent trace reanalysis are retained unchanged.

Across the two executed cases there are 244 confirmed successes/effects, no
uncertain command outcomes, five clock deferrals and zero packet-recorder losses.
All deferred intents succeed. Captured/filter/file records agree at 108712 per
endpoint for 1701 and 109964 for 2903. Native reserve/copy losses are zero; four
closed journals agree, including result rate/generation, and eight projected
cgroup endpoint/phase windows replay exactly. All source-window conservation
summaries replay exactly. Maximum measured publication-age upper buckets are
187 / 227 ms within the 250-ms gate. These are conditional shared-VM bridge-age
estimates, not physical sampling/delivery guarantees. All realtime packet windows
remain withheld by clock checks.

The shaping fixture remains root TBF 512 kbit/s per direction, burst 4096,
requested limit 32768, child netem queue 16 and base/base+1 seeds, without random
loss/delay. Pinned tc JSON normalizes the TBF limit to lat=448000; no fabricated
explicit limit readback. Both competitor liveness/whole-run offered-load checks
pass. Those checks do not prove matched-window delivery or isolate WAN loss.
Observers and logging add workload; no causal cost or transport superiority
comparison follows from these cases.

168 sources match the frozen Git inventory; eight selected installed files and
installed script bytes were constant through the cohort and checked before the
subsequent trace-buffer patch. Raw manifests report two different values for
image_platform_id, one matching the manifest digest and one config-like value.
Both cases' recorded container Image fields and configured immutable image
reference agree, and boot identity is shared. All reported values are preserved
in verification.json and per-role isolation projections; no canonical config ID
is invented and no resource comparison assumes identical raw platform-ID fields.
Full inspect/environment dumps and credentials are excluded. Raw PCAP/native
prefixes, journals and clocks stay local with hashes. Audit reads are immutable
and hashes are checked before/after.

## Subsequent trace-buffer patch

The trace buffer now uses one single-producer/single-consumer lane per owner,
128 events each / 256 total. Coordinator and transport producers no longer
contend on a mutex with each other or the consumer. Each lane has exactly one
producer, producer replacement requires join, and there is one external consumer.
Release/acquire indices protect slot reuse. A full lane still drops new events
explicitly and fails the unchanged completeness gate. Cross-owner sequence merge
order is not causal order. Reservations differ from the former shared buffer;
this is a new observer configuration requiring a fresh full cohort, not a waiver
or replacement for the failed case.

The patch removes a contention-loss mechanism without uniquely attributing the
retained loss. Command holding/deadline/proof/lease/start-fencing/replay policy,
SRT wire, worker IPC, capture buffer/dispatch/snapshot/retention are unchanged.
Consumers were rebuilt for the trace representation. Focused tests cover overflow,
per-owner reservation, concurrent FIFO/accounting, a 2000-event concurrent drain
with at most one outstanding event per lane (zero loss), IPv4/IPv6 command
lifecycle/recovery and clock-deferral/revocation. Subsequent smoke/build records
are separate under trace-buffer-fix/: the 15-s N0 smoke passes with eight successes
/effects, complete 34/4/4-record traces and zero recorder/trace losses. It does not
qualify the unexecuted N5 case.

The full 68-test SDK suite and 36 ROS-reported tests were already passing on the
cohort runtime. For the trace patch, five focused SDK/native tests, the additional
non-full concurrency test, 36 ROS-reported tests (32 GTests plus wrappers), and
92 host tests pass. No new full M2 acceptance or full 68-test rerun is claimed.

Next: freeze the new trace configuration for a fresh complete N5 cohort. Retain
all earlier recorder failures and historical UNKNOWN intents; N3/N4, default DDS
N5 and age/clock/security/resource alignment remain open. M3 remains incomplete,
PR #2 stays draft, and Intrinsic/M4 is untouched.
