# Current-build N0 coverage preparation — 2026-11-10

**Prepared only. Execution disabled; zero live cases and no authorization file.**

The closure plan declares exactly one N0 case: `N0-combined-1701`, ordinal10,
300 seconds of combined SENSOR/COMMAND traffic. The nine fresh N3 cases already
passed separately and will not be reexecuted. The other28 N4/N1/N2/N5 cases remain
disabled. No automatic follow-on, retry, resume, tuning, rebuild or M3 acceptance.
All29 previously unexecuted cases remain unexecuted in this preparation.

The same frozen socket-disposition matched SDK/ROS binaries are reused:14 current
manifest entries, preserved13 shutdown entries/full earlier chain and87 native
inputs. The pinned amd64 target image and native ARM64 observer image, provider,
IPC4, original5s child waits, observer policy and sampling budgets are unchanged.
The old N3 failure remains8PASS/1FAIL with unknown cause; the fresh9/9 PASS does
not relabel it or prove the original hang fixed. PR2 stays draft; M4 untouched.

## Exact proposed case

| Case | Seed | Source duration | Profile | Workload |
|---|---:|---:|---|---|
| N0-combined-1701 |1701|300s|N0|200Hz IMU,50Hz joints, command slot every2s|

No selected-source fault, outage, competing load or ARP/qdisc/neighbor intervention
is installed. The original combined runner's dynamic-neighbor N0 path is retained;
N3's permanent-neighbor fixture is not silently imported. Seed1701 names the
existing independent start; N0 contains no random impairment, so it is not random
loss coverage. No shortened smoke, extra seed or old10s diagnostic supplies credit.

## Prepared adapter and gates

`workload.py` is an evidence-local copy of tools/run_m3.py scoped to this single
N0/1701/300s case, selected matched install and existing command/provider/SENSOR/
start/sender diagnostics plus monotonic and PCAP capture. Native source and
installed binaries remain byte-identical. `scenario.py` keeps the original
Benchmark workload unchanged; a subclass adds the calibrated bridge-only capability
wrapper, bridge identity, actual signal brackets and retained child outcomes.
After source pause/result drain, the operator's existing finish request waits for
a host release: the isolated native observer must be ready before SIGINT. The
original stop implementation still owns its5s wait and forced-failure behavior.
This combined-path integration is offline prepared, not live calibrated yet.

The strict combined assessor retains typed/isolation and modeled freshness gates,
source duration/cadence and accounting, common-clock proof, capture completeness/
zero drops, provider trace completeness and durable command/journal progress
(including refusal of unresolved attempts). Both-role shutdown stages, explicit
socket dispositions/close returns and registered-worker observer lifecycle checks
are required. Readiness/exec/capability/identity/filter evidence is retained.
Cleanup, absent owned objects, deleted credential and frozen source/input/build/
prior-evidence integrity are part of the case gate. Any failed gate ends this
one-case sequence; there is no later-stage dispatch or automatic retry.

`case-plan.json` lists the one allowed case,28 disabled IDs and completed N3 IDs.
`freeze.json` binds source, build, helpers, unchanged prior inputs/evidence, local
read-only observer bundle and a fresh output path. `readiness.json` records only
preparation readiness. The driver refuses an existing output, old N3/full-campaign
grants, subsets, broader profiles, changed duration/build or absent exact grant.
No execution authorization is created by preparation. A future explicit user
instruction must be recorded separately, bound to this freeze and exact N0 scope.

## Validation and limits

Eight targeted offline tests cover exact scope, authorization refusal, no-Docker
entry refusal, wrong profile/seed/duration/build refusal, once-only sequencing,
no resume, byte-identical calibrated components, shutdown outcome retention and
observer-release ordering. All511 existing Python tests also pass. Tests use
mocked callbacks/processes and temporary metadata; no live fixtures or Docker
containers are started. Logs are in validation/. Native builds are not rerun.

Read-only Docker metadata inspection verifies pinned images/runtime and absence
of existing owned objects; it is not live qualification. No capture, bridge,
observer, readiness experiment, network, volume or container is started. Source,
helper, build and retained raw/public evidence hashes are verified before freeze.
Public hashes cover the resulting package and validation records.

Future N0 PASS would close this current-build combined N0 case only. Physical
sensor age, diagnostic overhead equivalence, lossless latest-only availability,
other current-build profiles and remaining M3 acceptance gaps stay explicit.
