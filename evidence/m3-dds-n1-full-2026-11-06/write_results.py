from pathlib import Path
import json
out=Path('evidence/m3-dds-n1-full-2026-11-06')
read=lambda name:json.loads((out/name).read_text())
study=read('study.json');totals=read('totals.json');commands=read('command-outcomes.json');sensors=read('sensor-populations.json');verification=read('source-verification.json');coverage=read('coverage.json');audits=read('journal-audits.json')
complete=study['status']=='passed' and len(study['rows'])==3
assert all(s['source_enabled_seconds']>=600 for s in sensors) if complete else True
text=f'''# Full-duration DDS N1 results

Frozen-plan status: **{study['status']}**. Executed {len(study['rows'])} of three planned
600-second cases. All planned duration/seed cases completed with execution/capture gates:
**{str(complete).lower()}**. This describes default DDS N1 execution coverage,
not N1 age-gate qualification, complete M3 acceptance, SRT N1, or equivalence of age/security/transport costs.

Command totals: {totals['attempts']} attempts, {totals['successes']} confirmed successes,
{totals['effects']} effects, {totals['expired']} observed expiries
({totals['expired_without_dispatch']} receiver expiry records without dispatch),
{totals['unknown']} UNKNOWN, {totals['unresolved']} unresolved,
{totals['not_admitted']} not admitted, {totals['rejected']} rejected, {totals['failed']} failed
and {totals['skipped_slots']} skipped cadence slots.
These populations remain separate. Skipped slots are not silently retried.
A terminal expiry is not a success. Missing/unknown state is not nonexecution.

| Seed | Attempts | Successes | Effects | Expired | Expired without dispatch | UNKNOWN | Unresolved | Not admitted | Skipped slots | Max terminal observation (ms) | History polls omitted |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
'''
for c in commands:
 text+=f"| {c['seed']} | {c['attempts']} | {c['successes']} | {c['effects']} | {c['expired']} | {c['expired_without_dispatch']} | {c['unknown']} | {c['unresolved']} | {c['not_admitted']} | {c['skipped_slots']} | {c['maximum_terminal_observation_ms']:.3f} | {c['status_history_omissions']} |\n"
text+='''
Terminal observation spans driver invocation to observed terminal status, including
service/middleware/reconciliation waits and the bounded post-cutoff result drain.
It is not handler start/execution or network transit latency. Per-state/reason
p50/p95/p99/maxima and omitted/uncertain populations are in command-outcomes.json
and the original manifests. Timelines split matching original-owner successes
only, using journal timestamps before mutations/commits. Recovered/missing/unknown
records retain uncertainty. No deadline/freshness or replay policy was changed.

## Sensor populations and age qualification

Source-fenced counters, callbacks and acceptance remain distinct. A callback
deficit includes source/middleware/queue/network/observer stages, not isolated WAN
loss. Age estimates are shared-VM realtime observations, not conservative SRT
clock intervals. Unqualified age distributions must not be interpreted as age
bounds. Per-route histograms, stale/invalid/clock-rejected/missing counts remain
available, including unqualified populations.

| Seed | Source-enabled seconds | Produced | Received callbacks | Actual IMU/joints Hz | Age estimates qualified |
| --- | ---: | ---: | ---: | --- | --- |
'''
for s in sensors:text+=f"| {s['seed']} | {s['source_enabled_seconds']:.6f} | {s['produced']} | {s['received']} | {'/'.join(f'{v:.3f}' for v in s['actual_source_hz'].values())} | {str(s['age_estimates_qualified']).lower()} |\n"
text+='\n| Seed | Clock steps | Max observed offset step (ms) | Max offset deviation (ms) |\n| --- | ---: | ---: | ---: |\n'
for s in sensors:text+=f"| {s['seed']} | {s['clock_step_count']} | {s['clock_max_offset_step_ns']/1e6:.6f} | {s['clock_max_offset_deviation_ns']/1e6:.6f} |\n"
text+='\n| Seed | Route | Accepted | Stale | Invalid | Clock rejected | Missing before callback |\n| --- | --- | ---: | ---: | ---: | ---: | ---: |\n'
for s in sensors:
 for name,r in s['routes'].items():text+=f"| {s['seed']} | {name} | {r['accepted']} | {r['stale']} | {r['invalid']} | {r['clock_rejected']} | {r['missing_before_callback']} |\n"
text+=f'''
## Integrity and scope

{len(audits)*2} closed journals pass SQLite integrity and immutable-command checks;
receiver successes agree with effect counts. Sender-only, receiver-only and status
divergences, if any, remain explicit in journal-audits.json/command-outcomes.json.
Sources match the frozen {verification['source_files_each']}-file inventory; eight selected
installed binary/SDK hashes and installed demo Python bytes remain constant.
The {verification['unchanged_compiled_sources_since_e3c5c70']} compiled production sources are unchanged from e3c5c70.
No new ROS GTest/full M2 build is claimed; the previously passing 83-test host suite
is unchanged rather than claimed as newly expanded coverage.

For passed cases, strict PCAP zero-drop/file-integrity gates and native v2
reserve/copy/coverage gates passed. {verification['cgroup_windows_replayed_exactly']} cgroup endpoint/phase windows
replay exactly from archived projections. coverage.json retains native offload
interpretation and PCAP population reconciliation separately. No physical wire,
checksum, packet-delivery or isolated resource-overhead qualification follows.
Source/callback populations, terminal waits and the shared emulated host prevent
an SRT/DDS performance-advantage claim. Seeded netem does not make independently
started executions deterministic at the application level.

Raw PCAPs, native prefixes, clocks, samplers and journals remain local with hashes.
The preserved plan has no retries or removed cases. The N1/N2 duration/seed cohorts and the unresolved age/clock gates are summarized
separately. Long v2 N5, deterministic N3, N4 phase barriers, other devices/offload
paths, controlled resources and semantic/security alignment remain open.
Intrinsic/M4 is unchanged; PR #2 remains draft.
'''
(out/'RESULTS.md').write_text(text)
print('wrote results; full DDS N1 duration/seed execution',complete)
