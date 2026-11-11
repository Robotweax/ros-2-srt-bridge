# Offline M3 closure preparation — 2026-11-09

No tuning, builds, Docker/ROS/fixture launches, captures, traffic, journal recovery,
forced expiry or replay. All38 proposed cases remain disabled. M3 is not accepted
as complete, PR2 stays draft and M4 is untouched.

N4 runners now select explicit SDK/ROS layouts and verify child prefixes. The
standalone peer takes its worker path from the imported SDK target. A future
isolated build emits a binding covering peer, worker, SDK headers/archives,
provider and fixture sources. Nonbaseline native runs refuse missing/stale
bindings before creating the output directory or lab. IPC frames remain version4;
the existing worker launch flag `--worker-ipc-v3` remains unchanged.

`tools/m3_closure_assessor.py` assesses closed artifacts only. It reuses original
N3 source/SDK/packet validators, combined SENSOR and strict durable command progress,
and phase-specific N4 journal/freshness/crash checks. Gates include frozen
source/runtime/image, zero N3 skips, source duration, complete captures, source
capture brackets, outage kernel seed/loss/drop/brackets, child shutdown and recorded
owned cleanup. Combined capture validation consumes the original capture summaries;
it does not independently reparse every packet. The sequence controller takes
callbacks only: producer, strict assessment, then next slot. Failure leaves later
slots unexecuted; an inner harness PASS cannot override rejection.

Validation:427 offline Python tests pass. Focused initial logs and both full-suite
logs are retained. Synthetic controls cover stale/missing bindings, refusal before
lab creation, source skips, incomplete observers, unresolved command progress,
outage metadata tampering and stop ordering. Read-only retained N3 baseline passes;
the original two-loss2903 is still rejected for skipped slots. No new N3 outcome.
All13 candidate manifest entries and86 recorded native inputs match; the pinned
provider remains clean and unchanged. See `verification.json`.

This is source preparation, not compiled or live validation. The current native
fixture binding is absent, and its preflight correctly refuses. CMake changes
were source-reviewed only. An isolated fixture build/link remains pending. No
live dispatcher is implemented or wired; its authorization and freeze checks
remain work before any campaign. `source-snapshot.json` is an offline snapshot,
with a null fixture binding, not a completed live freeze. The original planning
artifacts remain immutable; `readiness-update.json` records the current delta.
