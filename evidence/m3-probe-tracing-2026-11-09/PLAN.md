# Default-off per-probe lifecycle tracing

Preserve one pending probe, one-second attempt scheduling, two-second reply
admission and five-second mapper-age rules; no rate/budget/timeout/queue/fence
changes. No historical118 replay, live forced expiry or new loaded cohort.

Add probe_diagnostics requiring CommandTrace, off by default. Fixed transport
lane POD observations: timer attempt/result with pending-before/after; actual
management queue result; first SDK would-block and final SDK result/bracket;
correlated reply/request admission with decoded fields only after existing
identity/schema validation; natural pending clear observed at existing tick.
No extra decode/check, callbacks, owner allocation/I/O or journal operations.
Queue-to-SDK correlation uses existing management sequence/session/epoch/generation,
so no diagnostic metadata needs to alter queues or wire messages. SDK success
means local acceptance only; trace loss/absent fields remain unavailable.

Use optional stack observation output from Session::receive to expose its existing
decoded times and actual mapper call/result. Null when disabled; no new decision.
No worker/wire format change. Keep fixed trace capacities/drop counters; added
POD size and enabled observer work prevent performance comparisons.

Build SDK/ROS in new probe-tracing prefixes; preserve baseline/start-trace/sender
installs and provider checkout/archive. Validate host contracts, full SDK/ROS,
fresh IPv4/IPv6 enabled/disabled loopback sessions and one successful fresh
command per mode/family. Native calibration requires actual reciprocal probe
attempt/queue/SDK/admission joins; no fault/pause/short lease/expiry experiment.
Session-only virtual-time checks cover busy/mismatched/late replies and explicit
absent observations without submitting or expiring a command. Preserve failures.
No build/test/heavy analysis overlaps calibration capture. Archive exact source,
new/preserved binary/raw hashes, closed journal selections and cleanup.

Expose optional ROS/scenario/runner flag with a separately calibrated layout and
positive versioned records gate; defaults remain unchanged. Historical intent3
and118/34/98/12 evidence retains its original scope. PR2 draft/M3 open/Intrinsic
untouched. A later loaded cohort needs its own prospective plan.
