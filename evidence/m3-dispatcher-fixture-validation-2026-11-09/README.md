# M3 dispatcher and fixture build/link validation — 2026-11-09

The user authorized campaign dispatcher wiring and native fixture build/link
validation, without tuning or starting experiments. No campaign case, fixture,
worker, ROS workload, capture or impairment was launched. No forced expiry,
journal recovery or replay. M3 remains not accepted as complete, PR2 draft,
Intrinsic/M4 untouched. All38 planned cases remain disabled and unscheduled.

## Implemented dispatch

`tools/m3_campaign_dispatcher.py` maps the exact predeclared38-slot order to
single-case N3, combined SRT, native N4 and ROS N4 adapters. QUERY dispatches one
bounded2s case; legacy six-second/batch entry points are not called. Combined
adapters select the fixed candidate, immutable image, exact profile/seed/duration,
existing command/start/sender and CONTROL/SENSOR provider diagnostics plus native
capture. No production setting, probe expansion, ARP study or tuning is added.
`run_m3.main(argv)` now accepts an explicit fresh output and immutable image
reference so the dispatcher can bind each case without guessing a timestamped
output directory. Existing standalone defaults remain available.

Preparation only reads/hash-checks files. `campaign-freeze.json` binds the exact
original plan, all38 invocations, candidate/preserved build chain, native peer
binding, provider, native capture helpers and source inventory including root
CMakeLists. It explicitly sets execution_authorized=false and automatic_start=false.
It is a readiness snapshot, not runtime qualification or permission to execute.
No authorization grant has been created. A future execution entry requires a
separate explicit grant binding the exact freeze hash, entire case order and
fresh `.local` output. The existing output cannot be resumed/retried through it.
The future operator must obtain the requested scope change before supplying that
grant; the current instruction does not authorize one.

Before dispatch, after return, and around independent closed-case assessment,
the full freeze is compared again. Missing/stale inputs, inner failure, assessor
rejection or recorded cleanup failure stop every later case. Inner harness PASS
is kept separately and cannot authorize advancement. Case/assessment/campaign
records preserve failures; the active-case record identifies dispatch if a process
is interrupted. Even a fully passing cohort does not itself accept M3.
Combined capture gates retain the prior limitation: they consume original capture
summaries, rather than independently reparse every packet.

## Native build/link proof

One isolated build succeeded in the pinned amd64/Jazzy image with `--network none`,
no network capabilities and the existing installed SDK/provider. Output is
`build/m3-n4-sender-reconcile-peer`; production libraries and archived fixture
prefixes were not rebuilt. Release C++20 with existing warnings/Werror compiled
and linked. No peer/worker execution, `ldd`, interface, socket or fixture test.

`verify-build.py` is a repeatable static audit. It verifies imported SDK/provider
prefixes, compile-time selected worker, linker-map archive/object contributions,
ELF64/little-endian/x86-64 metadata, needed-library names and absence of RPATH.
Six selected SDK archives and the pinned provider appear in the link map.
The36-file fixture binding covers installed SDK headers/archives/worker, peer,
provider and fixture sources. Private frames remain IPC4; the worker launch flag
is still `--worker-ipc-v3`. See `link-proof.json` and `fixture-binding.json`.
Static needed-library inspection does not prove dynamic-loader/runtime/IPC success.
The native nonbaseline preflight now passes against the generated binding.

All13 candidate manifest entries and86 native inputs still match. Provider commit
52be7c86 remains clean and its installed archive hash is unchanged. Prior SDK81/
ROS41 runtime tests retain their own recorded scope and were not repeated.

## Offline checks and remaining work

440 Python tests pass, including13 new dispatcher checks. Every adapter boundary
was mocked. Controls cover exact slot mapping/output, missing/mismatched grants,
source drift before/after dispatch, cleanup rejection despite inner PASS, no
advancement, no existing-output reuse and no M3 auto-acceptance. No live case was
used to test dispatcher behavior.

All validation logs are retained. Versioned build/ELF/excerpt logs have trailing
whitespace removed; exact raw copies remain locally hash-indexed by
`raw-log-manifest.json`. The first optional ELF symbol filter found `rg`
absent in the build image; a direct readelf-only inspection succeeded. One added
output-path test initially used macOS's /var symlink alias; canonicalizing its
temporary fixture fixed it. An initial static-audit assertion expected SQLite as
a direct peer dependency; the linker omits that unused direct dependency, so the
final audit records actual needed libraries. None required a native rebuild or
experiment. Failed Python-suite output remains in full-python-tests-second.log.

Next live step, only after a separate scope change: the declared strict N3 cohort,
then N0/N4/N1/N2/N5 in fixed order, stopping on the first failed gate. Compilation
and mocked dispatch do not close any acceptance-matrix case. The original failed
N3 cohort, historical118, comparison limits and older build-labelled evidence are
unchanged. Original planning/readiness snapshots are preserved; this directory
records the current preparation delta.
