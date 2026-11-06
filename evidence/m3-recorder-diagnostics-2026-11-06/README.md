# Recorder and command development diagnostics

These are separate development controls, not replacements for the failed frozen
SRT N5 cohort. M3 and full SRT N5 qualification remain open. No capture mode,
buffer, retention, production C++, SDK, wire, deadline, lease or replay policy
changes. Diagnostic observers add workload; do not transfer their costs to earlier
cohorts. Intrinsic/M4 remains untouched.

`tools/m3_recorder_diagnostics.py` optionally samples tcpdump process identity,
state, scheduler counters, context switches, wchan and permitted I/O counters
at a nominal 100-ms interval. Reads have monotonic brackets, explicit errors and
missing identities, and are bounded to 75000 observations per endpoint. PID/start
identities are never merged. Sampling is opt-in via `run_m3.py
--recorder-diagnostics`; the default workload is unchanged. wchan=0 can mean
restricted/unavailable, and scheduler counters depend on kernel configuration.
No sample or delta proves a cause, completeness, physical delivery or cost bound.

## Controlled pause and recovery

`python3 tools/check_m3_recorder.py --out .local/recorder-control-new` creates two
fresh network-none containers with synthetic loopback UDP. PCAP uses the current
immediate/full-snapshot/buffer/rotation options. The recorder is deliberately
stopped for approximately 1.5 seconds only in the negative case. Both containers
are removed, including on failure.

| Case | Sent / application received | PCAP records | Kernel drop counter | Stopped samples | Recovery marker |
| --- | ---: | ---: | ---: | ---: | --- |
| Baseline | 2076 / 2076 | 2076 | 0 | 0 | Captured |
| Deliberate pause | 2116 / 2116 | 1310 | 1612 | 14 | Captured |

The baseline passes written-record integrity and zero-drop checks. The pause is
correctly rejected by that gate and resumes capture after SIGCONT. Linux loopback
filter counters are 4152/4232, twice the sent populations; they are not reconciled
to captured records. The drop counter is not equated to missing application
datagrams, physical frames or veth behavior. This validates the diagnostic and
negative gate for a known pause; it does not attribute the historical N5 failure.

## Separate N5 development runs

| Source | Source-enabled duration | Successes/effects | Unresolved driver / sender UNKNOWN | Skipped slots | PCAP kernel drops |
| --- | ---: | ---: | ---: | ---: | ---: |
| 013927f, no command poll history yet | 60 s | 2 | 1 / 1 | 27 | 0 / 0 |
| 56b7b8a, bounded command poll history | 30 s | 12 | 0 / 0 | 3 | 0 / 0 |

Both original harness manifests report passed under development semantics, which
permit unresolved command outcomes. That is not full command/N5 acceptance. The
60-second case retains sender UNKNOWN/reconcile-required for ID 3 and no receiver
record; two common successes agree. It demonstrates uncertainty can be observed
with zero recorder drops. It does not establish the exact transition or causally
separate all workload/transport effects. Absence is not nonexecution; no replay,
expiry or fabricated result is introduced. Historical ID 105 remains unresolved.

The SRT driver now uses the existing bounded poll-history helper: first 32 plus
latest 32 observations, explicit omission counts, found/state/reason/revision,
local/peer errors and query-queued status. The 30-second case records 86 polls
across 12 intents (each starts observed LOCAL_QUEUED and ends SUCCEEDED). The
history is observational and does not change admission, polling cadence, result
classification or replay policy. It cannot reconstruct missing historical polls.

On actual N5 endpoints, /proc I/O reads are PermissionError and wchan is 0 after
tcpdump privilege dropping. The observations preserve this limitation. No extra
capability or altered tcpdump credentials were used in N5 to obtain those fields.
The controlled loopback probe explicitly uses `-Z root`, so its I/O visibility is
not transferred to the application workload. N5 scheduler/state counters are
available, sample gaps are retained, and no I/O/root-cause claim follows. The
60-second run saw one operator D-state sample, insufficient for root-cause proof.

All 88 host Python tests pass. The 30-second ROS/SRT development run exercises the
new adapter; no new ROS GTest or complete M2 build is claimed. Eight selected
installed files still match the earlier frozen N5 plan when checked after these
runs. Source manifests match their named Git commits byte-for-byte. Original
manifests are unchanged; recorder-replay.json recomputes their observations and
adds explicit unavailable-field counts. Closed journals are audited read-only
with before/after hashes. Raw packets, native prefixes, clocks and journals stay
local with hashes; full inspect/environment dumps and credentials are excluded.

Next: instrument command invalidation/transport handoff boundaries to distinguish
live reconciliation state from shutdown/recovery transitions, and correlate any
new recorder loss with the optional observations. Preserve original failures;
N3/N4, default DDS N5, age/clock/security/resource gates remain open.
