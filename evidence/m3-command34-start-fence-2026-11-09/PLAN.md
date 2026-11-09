# Command34 start-fence diagnosis, no tuning

Read-only analysis of the retained loaded N5 source5544747, original run
.local/m3/20261109T075543179775Z and all122 intents; N0 control retained. Verify
original raw manifests/source provenance/qualified clock before joins. Original
N5 remains FAILED121/122 with intent34 REJECTED/context_lost, not expiry/UNKNOWN.
Do not replay, reopen writable journals, reissue commands or replace old outcomes.

Trace command34 and neighboring/all successful controls through logged admission,
closed sender/receiver entries, dispatch, result and observation; preserve context,
request sequence, source epoch/hash, budget, all QUERYs and original clock fields.
Admission clock deadline is NOT actual start grant deadline. Journal dispatched
is NOT handler invocation. Receiver-worker point34 covers admission/GET, NOT
execute. Enumerate every source path producing6/1, including coordinator decline
of a post-dispatch start check, worker consume failure and worker second gate.
Do not infer a unique branch, clock root cause or actual grant from absent trace.

Compile a separate diagnostic probe against unchanged execution_pool.cpp in an
isolated local output dir. At recorded timestamps demonstrate clock-lease elapsed
versus original budget, before/equal/after boundary, revocation versus expiry,
and same-timestamp fresh replacement grant. Synthetic supplied times are a
counterfactual contract, not a reproduction of the historical branch. No runtime
build, provider edit or policy/rate/queue/neighbor/clock/budget/idle changes.

Run existing built execution_contract and execution_start_ipv4/ipv6 once, bounded
by existing CTest timeouts in network-none pinned image. These already include
fixed barrier cases for session revocation, original budget expiry, running
completion and clock-lease lapse; no fixture/default modifications. Preserve any
failure; no retries. Freeze hashes of test binaries/worker and all8 runtime +
2existing observers +ARP tracer before/after. Archive controlled journals read-only
and capture zero-effect rejection facts separately from old N5. Existing test
configuration is not a production tuning proposal. No new N5 cohort in this step.

Add host guards against enum confusion, cross-context joins, unknown/missing
fields, timestamps, conflating grant with admission and claiming branch identity
from the old trace. Public hashes/omissions, source checks and exact validations;
SDK72/ROS41 remain prior full validation. PR2 draft/M3 incomplete/Intrinsic untouched.
