# Current-build N4 preparation —19 cases, not run

**Execution disabled; no authorization file and zero live N4 cases.**

Prepare the exact19 declared N4 rows on the same frozen socket-disposition SDK/ROS
build that passed fresh N3 and stabilized N0. The other9 unexecuted N1/N2/N5 cases
remain disabled. The10 completed N3/N0 cases are explicitly excluded from rerun.
No tuning, automatic retry, merge or M3 acceptance; PR2 draft, M3 open, M4 untouched.

## Fixed order and outcomes

| Ordinals | Cases | Required existing outcome |
|---|---|---|
|11–13|admission × both/to-robot/to-operator|Valid matching durable success/one effect, or permitted safe rejection/expiry/zero effects with its actual reason|
|14–16|dispatch × same three directions|Original dispatch/start/deadline fence; same phase-specific safe outcome rules|
|17–19|started × same three directions|Before-effect barrier; same phase-specific safe outcome rules|
|20–22|committed × same three directions|Original committed valid success/one effect preserved|
|23|withheld-result QUERY, both|Committed result recovered by QUERY; one original COMMAND handoff/effect|
|24–26|ROS freshness × same three directions|15s source,2s cut; restored qualified freshness, typed payload/order and six balances0, no stale queued replay|
|27|ROS crash before admission|UNKNOWN/reconcile_required, controlled0 effects, no replay|
|28|ROS crash after effect/before commit|UNKNOWN/effect uncertainty,1 effect, invalid success proof, no replay|
|29|ROS crash after committed result|Original SUCCEEDED/valid proof,1 effect, no replay|

The exact IDs, original ordinals, settings and expected-outcome text are in
case-plan.json. Seed1701 is retained (kernel egress seeds1702operator/1701robot).
All13 native cases use the existing2s hold, never the six-second overrun batch.
Freshness retains15s source/existing2s cut. Crash fixtures retain their declared
phase cuts, external simulator and restart sequencing; no new hold/duration is
invented for them. Original5s command budgets, conservative mapped deadlines,
20s native fixture watchdog, barriers and child waits remain unchanged.
A safe decline is recorded as that outcome, not renamed successful execution.
NOT_FOUND/absence never proves nonexecution or authorizes replay/forced expiry.

## Current-build fixture and adapters

Only the standalone N4 peer was compiled/linked in a new isolated prefix:
`build/m3-n4-socket-disposition-peer`. The production SDK/ROS/provider, old fixture
prefix and frozen source remain unchanged. The compile-only container used the
pinned amd64 image, network none and pull=never, and was removed. No N4 peer,
worker, ROS node, outage, lab network or readiness experiment was executed.

Static audit passes ELF64/little-endian/x86-64, no RPATH/RUNPATH, selected worker
string, six selected SDK archives plus pinned provider and IPC4 with the existing
--worker-ipc-v3 flag.37 bound fixture files include24 installed headers matching
frozen source. SDK import/prefix, archive/object link map, provider and dynamic
needed names are recorded in link-proof.json/fixture-binding.json. Compilation
and readelf do not prove runtime loader/IPC/transport behavior. Exact build/ELF
logs remain local/hash-bound; public logs remove trailing whitespace and ELF
symbol-table verbosity, retaining header/dynamic information.

native_adapter.py and ros_adapter.py are scoped copies of the existing single-case
runners. Native selection uses the new exact fixture/SDK binding; ROS scripts
require the current install prefix and cannot silently fall back to baseline.
Phase outcome/network/crash checkers and ROS workload class bodies are unchanged.
No legacy batch CLI or general38-case dispatcher is included.

These are the original bounded N4 fixtures, not the N0 combined300s harness.
Their existing permanent-neighbor condition, native simulated rate handler,
ROS sample/command diagnostics and phase-aware crash accounting are retained.
No N0 shutdown-stack observer, capability-wrapper/security-cost equivalence or
packet-capture/physical-sensor-age qualification is implied. Shutdown diagnostics
remain at their original N4 defaults; intentional crash exits are accounted as
controlled fixture events, not waived unplanned failures.

## Strict assessment and execution boundary

The assessor reuses the original phase/outage/freshness/crash gates with exact
socket-disposition image/source/runtime provenance and37-file native binding.
Kernel direction/seed/loss/counter/install/restore/2s brackets, matching closed
journals, original deadlines, result validity/effect counts and one handoff/query
proof remain mandatory. ROS context/freshness and declared crash ownership/state/
trace proofs remain mandatory. No gate or outcome is relaxed for this build.

run.py requires a separate exact future grant binding this freeze, all19 ordered
IDs, all9 disabled IDs, all10 completed exclusions,2s native holds, matched layout,
historical-failure preservation/no tuning/no retries/first-failure stop. Old N0/
N3/full-campaign grants are refused. No grant is created. Output must be fresh;
no resume, subset, ordering override or automatic build exists in the driver.

Every case's strict result, recorded cleanup, credential deletion, independent
owned-container/network absence and frozen source/input/build/fixture/prior-evidence
verification must finish before the next produce callback. Any failed gate leaves
all later rows not_executed. Unexpected host exceptions trigger bounded cleanup
of only recorded owned names and retain failure; no case is retried. The remaining
N1/N2/N5 stages cannot be dispatched by this package.

## Offline verification and limits

20 targeted tests and all511 existing tests PASS. New tests cover exact19/13+6
mapping/order, scope/grant/legacy refusal,2s-only and current-prefix guards,
all19 failure positions, assessment/postflight before advancement, full mocked
driver success/failure, no output reuse, owned cleanup/credential/hash refusal,
unchanged checker/workload ASTs and static native binding. Temporary metadata and
mocked runner/Docker boundaries only; no live case supplies test credit.

freeze.json binds code/scripts, current14/preserved13/full SDK/ROS/provider chain,
native87 inputs,37-file fixture, header/link/build artifacts, original plan,
pinned image/runtime, all prior raw/public archives and new local exact logs.
The N0 PASS and older native fixture artifacts are verified unchanged; nothing
is spliced or relabelled. readiness/postflight describe preparation only.

All19 current-build N4 runtime cases remain unqualified until separately authorized
execution passes. Static compile/link and offline controls do not qualify
phase scheduling, cold ROS startup, real IPC, crash outcomes or runtime cleanup.
N0/N3 retain their recorded PASS scope and historical failures remain explicit.
M3 remains open and the other stages remain disabled.
