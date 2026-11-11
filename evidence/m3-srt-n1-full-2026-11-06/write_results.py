from pathlib import Path
import json
out=Path('evidence/m3-srt-n1-full-2026-11-06')
read=lambda name:json.loads((out/name).read_text())
study=read('study.json');totals=read('totals.json');commands=read('command-outcomes.json');sensors=read('sensor-populations.json');verification=read('source-verification.json');audits=read('journal-audits.json')
complete=study['status']=='passed' and len(study['rows'])==3
assert all(s['measurement']['source_enabled_seconds']>=600 for s in sensors) if complete else True
text=f'''# SRT N1 full-duration results

Frozen-plan status: **{study['status']}**; executed {len(study['rows'])} of three planned
600-second cases. Complete duration/seed execution with runner gates: **{str(complete).lower()}**.
This is SRT N1 execution evidence, not complete M3 acceptance, physical delivery,
controlled resource qualification or an SRT/DDS superiority result.

| Seed | Attempts | Successes | Effects | Expired | Receiver expiries without dispatch | Rejected | Failed | UNKNOWN observed | Unresolved | Not admitted | Skipped slots | Maximum terminal observation (ms) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
'''
for c in commands:text+=f"| {c['seed']} | {c['attempts']} | {c['successes']} | {c['effects']} | {c['expired']} | {c['expired_without_dispatch']} | {c['rejected']} | {c['failed']} | {c['unknown']} | {c['unresolved']} | {c['not_admitted']} | {c['skipped_slots']} | {c['maximum_terminal_observation_ms']:.3f} |\n"
text+=f'''
Totals: {totals['attempts']} attempts, {totals['successes']} confirmed successes,
{totals['effects']} effects, {totals['expired']} observed expiries,
{totals['rejected']} rejected, {totals['failed']} failed,
{totals['unknown']} observed UNKNOWN, {totals['unresolved']} unresolved,
{totals['not_admitted']} not admitted, {totals['skipped_slots']} skipped slots.
Closed-journal states remain separate from driver observations in
command-outcomes.json and journal-audits.json. A missing record or NOT_FOUND is
not nonexecution. Generation checks withhold final equality across uncertainty.
No retry/replay or policy change is introduced.

Terminal observation includes service, journal, transport and reconciliation waits
and any bounded result drain. It is not network transit or execution latency.
Full per-state/reason p50/p95/p99/maxima remain in command-outcomes.json; no uncertain
population is silently reclassified as success. This does not use DDS's offline
journal-clock decomposition on SRT's clock-mapped contexts.

## Source-fenced populations and publication-age bounds

The checkpoint accounting reproduces six conservation equations per completed
case. Every local admission/replacement/rejection population is retained below.
The SRT accept-to-receiver gap is not automatically network loss or isolated FEC
benefit. Different age origins, transport packing/pacing/reconciliation, crypto
and host conditions prevent a transport-advantage inference from the DDS cohort.

| Seed | Source-enabled seconds | Produced | Bridge published | Observer received | Missing | Actual IMU/joints Hz |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
'''
for s in sensors:
 m=s['measurement'];text+=f"| {s['seed']} | {m['source_enabled_seconds']:.6f} | {m['source_produced']} | {m['published']} | {m['observer_received']} | {m['missing']} | {'/'.join(f'{v:.3f}' for v in m['source_actual_hz'].values())} |\n"
text+='''
Bounds below cover the source-fenced published population. Their origin is bridge
callback ingress, not physical sensor sampling or DDS Header emission time. The
250-ms publication gate and conservative clock-model assumptions remain intact;
these bounds do not establish all-source delivery, cross-transport age equivalence
or physical network delay. Histograms round up to 1 ms.

| Seed | Route | Published count | p50 upper (ms) | p95 upper (ms) | p99 upper (ms) | Maximum upper bucket (ms) |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
'''
for s in sensors:
 for name,h in s['measurement']['age_upper_histograms'].items():text+=f"| {s['seed']} | {name} | {h['count']} | {h['p50_ms']} | {h['p95_ms']} | {h['p99_ms']} | {h['maximum_ms']} |\n"
text+='\n| Seed | Attributed stage | Count |\n| --- | --- | ---: |\n'
for s in sensors:
 for name,count in s['measurement']['losses'].items():text+=f"| {s['seed']} | {name} | {count} |\n"
text+=f'''
## Integrity and qualification scope

{len(audits)*2} closed journals pass integrity/immutable-command checks. Authoritative
terminal agreement is checked where both sides hold terminal records; missing/
unknown/divergent observations remain explicit. Receiver successes agree with
device effects. Original sources match the frozen {verification['source_files_each']}-file inventory,
eight selected installed application/worker/capture/SDK hashes and installed demo
Python bytes. All {verification['unchanged_compiled_sources_since_d2912fc']} compiled production sources are unchanged from d2912fc.

Strict PCAP zero-kernel-drop/written-file-integrity and native v2 reserve/copy/
coverage gates pass for passed cases. Filter-received population reconciliation
is independent and preserved per endpoint. Realtime windows require both clock
and population qualification; native counts do not confer realtime or physical
wire/delivery qualification. {verification['cgroup_windows_replayed_exactly']} cgroup endpoint/phase windows replay exactly
from archived projections, and the three source-fenced summaries replay exactly
where completed. Diagnostic held-state unqualified/not-ready durations include
startup/tails/gaps; no exact source-window availability bound is inferred.

All 83 host Python tests pass, including rejection of mixed rotating-file
retention configurations in study comparisons. Capture tooling now records and
uses sixteen 16-MB files (256,000,000 nominal bytes), while installed binaries,
SDK, kernel buffer, snapshots and command/publication policies remain unchanged. No new ROS GTest/full M2 build is claimed. Raw captures, prefixes,
journals, clocks and sampler files remain local with hashes; no full inspect/env
dumps are published. The plan has no retries or removed cases. Full DDS N1, remaining
age/security/semantic alignment, long v2 N5, deterministic N3, N4 command-phase
barriers and controlled resources remain open. Intrinsic/M4 is unchanged;
PR #2 remains draft.
'''
(out/'RESULTS.md').write_text(text)
print('wrote results; full SRT N1 execution coverage',complete)
