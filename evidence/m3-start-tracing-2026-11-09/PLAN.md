# Targeted start tracing, no tuning

Add a default-off start_diagnostics flag requiring existing CommandTrace. Capture
post-dispatch start submission, owner check decision/error/clock and actual grant,
coordinator decline, execute submission/token, and worker consume/second-gate
observations. Explicit absent observations remain unavailable. Correlate original
request/session/route/origin, check and worker tokens, slot/generation/deadline.
Trace outcomes are observations, never command/journal authority.

No rate/queue/neighbor/clock-policy/budget/timeout/retry/fence-decision changes.
Keep consume/second-gate decision timestamps and original decision ordering. No
new callbacks, storage/I/O, allocation or retry on the worker/owner trace path.
Use fixed POD observation fields in the existing64-slot sealed shared memfd,
with generation check and release/acquire publication; parent reads after reply.
Bump private mapping version/size so mismatched builds fail closed. Socket IPC
v3 frame and SRT/protobuf/CDR wire unchanged. Build both sides together. Preserve
one-use CAS/revocation and original journal outcomes, capacity/drop reporting.

Build SDK and ROS in NEW isolated build/install prefixes; preserve the installed
8runtime+2native observer+ARP tracer baseline and provider/dependency checkout.
Default flags false, no worker diagnostics when disabled; invalid flag dependency
fails explicitly. Expose optional ROS/scenario/runner flag without running a new
N5 cohort here. Freeze source/new binaries before controlled captures.

Calibrate once per defined case/family with fresh isolated loopback journals,
no tuning of production defaults: successful and disabled controls, actual
pre-consume lease lapse, session revocation, post-consume second-gate lapse,
original-budget expiry and coordinator start-check denial. Existing test barriers
used; add only test-only atomic resume API for coordinator-controlled child pause.
Short lease used only in the named synthetic coordinator fixture to fit between
existing1s probes, not a production setting. Preserve failed preparations/cases;
no retry to obtain favorable result. No claim reproduce historical command34.

Negative checks: wrong slot/generation, stale/reused slot observation, disabled
and unpopulated observation, malformed fields, trace saturation/populations,
missing/misjoined events and distinct context/enum/deadline scopes. Run appropriate
SDK/native/ROS and host tests, record full versus focused validation explicitly.
Archive calibrated events/closed journal extracts/hashes, source and installed
baseline preservation. Original failedN5/34 and UNKNOWN98/12 remain unchanged.
PR2 draft/M3 incomplete/Intrinsic untouched. No mitigation or new loaded cohort.
