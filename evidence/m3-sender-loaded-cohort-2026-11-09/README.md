# Sender-visibility cohort stopped at N0 harness failure

**The cohort failed its N0 gate; N5 was NOT_EXECUTED.** The frozen plan's stop
condition was honored. There was no retry, replacement case or extra duration.
No actual sender deferral was captured. This is not a loaded result or completed
qualification, and the earlier stopped4211 slot remains unexecuted.

The cause is a Python harness naming bug introduced with the sender-visibility
wiring in `9e7557d`. A function-local `from m3_sender_trace_analysis import
summarize` causes Python to treat *every* use of `summarize` in `main` as local.
The earlier packet-decoding call therefore raises UnboundLocalError before that
import executes. This affects the harness even when the sender flag is false.
It is not a sender clock or command failure.

The import is now aliased to `summarize_sender`; the packet parser keeps its
global binding to `m3_capture.summarize`. A new regression guard checks the
compiled Python scope, since `--help` alone would miss this failure. All390 host
tests pass after the fix. The live harness has **not** been rerun, so the repair
has no new end-to-end cohort qualification yet.

## Frozen plan and original outcome

[Plan](PLAN.md), frozen source
`9b221a0563d7317d759caedbabec4be59026056a`. The only planned slots were:

| Slot | Original outcome |
|---|---|
|N0/1701/15s|Harness exit1, cohort gate FAIL; workload reported8/8 success|
|N5/1701/300s|NOT_EXECUTED due prior failure|

Exact calibrated `sender-visibility` SDK/ROS binaries, `--skip-build`, sender/
start/command/both-provider/native/packet/drain/path tracing were selected. No
runtime build or policy change occurred. Preflight host389 checks passed; exact
SDK77/ROS41 binary qualifications were reused. The failed source was verified
against every captured source hash **before** editing the harness. The original
file is also checked against the frozen Git blob after the fix. Original
`run.json`, execution status, exception and exit codes remain unchanged.

Original run: `.local/m3/20261109T134421999439Z`.
[`execution.json`](execution.json) preserves failed/not_executed states;
`validation/original-harness.log` retains the failure. The source fixture used
fresh journals, sessions, process epochs and credentials. It submitted only
numeric intents1–8, with no use of historical118 or its context.

## Read-only audit after closure

[`offline-audit.json`](offline-audit.json) decodes retained captures and joins
the original command/start/sender records to immutable closed journals. It
explicitly keeps `original_harness_status:failed`, `original_exit_code:1` and
`promoted:false`. It does not modify the original report or promote the failed
capture/cohort gate.

- Eight confirmed successes, eight effects, zero skips or unresolved intents.
  Sender/receiver journals agree; all eight start groups invoked the handler.
- New sender counts:45 clock0,46 releases8,47 journal replies63,48 events36.
  All complete original trace incarnations have zero loss. No clock-error cause
  or deferral/recovery is available from this control.
- Offline packet decoding reconciles both tcpdump footers/populations, with no
  unaccounted frames. Both native v2 records validate complete and zero time
  namespace offsets. These independent checks retain useful control evidence;
  they do not erase the original failed harness gate.
- ARP packet diagnostics recorded one driver-start reply per peer, zero qdisc
  drops or other/consumed frees. No N5 CONTROL-gap/reply-step/telemetry diagnosis
  can be claimed because that slot never ran. Raw N0 observations remain retained.
- All148 new raw files are hashed before/after;323 prior raw artifacts (303 from
  original1701 plus20 sender calibration artifacts) remain unchanged. Complete
  raw PCAP/native/provider/SQLite/sample files remain local, with selected public
  trace/report/log copies and exact omissions in `public-disposition.json`.
- Calibrated sender binaries, both older runtime baselines and three native
  observers are unchanged. One owned network and its two containers, observer
  rules and credentials were removed. Root configurations and interface features
  match before/after. No tests/builds/heavy analysis overlapped live capture.

The [archive script](validation/archive.py) performs only post-closure reads,
hash verification and public artifact selection. It never runs commands,
application journal recovery or live experiments. Generic trace fields do not
authorize outcomes, expiry, nonexecution or replay.

Next: freeze a **new**, separately declared cohort after reviewing this harness
repair; do not resume or relabel this failed plan. Actual loaded sender deferral
and deadline-drop reconciliation remain uncaptured. Historical118 stays UNKNOWN/
reconcile_required, old34/98/12 remain unchanged, PR2 stays draft, M3/fullmatrix
open and Intrinsic/M4 untouched. No tuning, forced expiry or118 replay occurred.
