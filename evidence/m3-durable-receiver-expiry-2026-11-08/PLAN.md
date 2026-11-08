# Durable expiry of a received command, with qualified proof

Freeze plan before implementation, source before validation/live. Preserve all old
FAILED/UNKNOWN verdicts. PR2 draft, M3 open, Intrinsic/M4 untouched.

A received COMMAND must already pass authentication, structural/payload/identity/
route/budget/sequence checks. Only a qualified AgeResult with lower age bound
strictly greater than original valid_for_ms proves expiry. Upper bound exceeding
budget is merely unsafe-to-start, not expiry proof. Retain ambiguous straddling
intervals within existing bounded FIFO/resource/context rules. Never infer expiry
from timeout/NOT_FOUND/absence/expired or invalid clock/future timestamp/underflow.

Calculate latest possible converted deadline from evaluated_ns-(age.lower-budget),
requiring positive representable past deadline. This is evidence only, never an
execution eligibility extension. Transport marks an internal expiry-only journal
notification with original immutable command/context/source epoch/timestamp/body.
It may not dispatch. The dedicated endpoint completion path uses existing journal
admission semantics (new entry past deadline -> EXPIRED/start_deadline, revision1,
no result/no dispatch), sends STATUS only after commit, and preserves existing
records. Capacity/storage/context failures retain conservative uncertainty.
No wire/protobuf/provider/clock configuration change, no sender resend/new budget.
Both initial qualified stale arrival and later retained revalidation must work.

Tests before live: lower-bound/equality/straddling/invalid/future/underflow checks;
full Release/Werror SDK+ROS suites and host/syntax/diff. Real IPv4/IPv6 loopback
CONTROL gate delays500ms-budget commands650ms: qualified direct arrival and
clock-gap retention/requalification must commit expiry, yield matching sender/
receiver records, one SDK handoff, no dispatch/effect, QUERY recovery after peer
restart, duplicate-ID reconciliation without replay, and later fresh-ID success.
Existing short-gap recovery/resource-expiry/context-loss/shutdown and negative
Session contracts remain. Retain every failed source/log before corrective revision.

Live only after gates pass, two slots once, stop on first integrity/durable-outcome
failure: N0/4211/15s then N5/4211/300s. Same pinned image/provider, dynamic neighbors,
200/50Hz sensor targets,2s offered commands, original5s budgets,8s result drain,
command/provider diagnostics and stable tcpdump drain. Freeze8 rebuilt runtime
hashes; no builds/tests overlap live. No extra seed/retry this cohort.

Report TWO separate metrics prospectively: strict all-success (unchanged) and
success-or-verified-durable-expiry completion. The latter passes only if every
attempt has a matching confirmed SUCCEEDED or EXPIRED/start_deadline pair, unique
SDK handoff, original source budget, valid original-context trace/worker proof,
qualified lower-bound proof for new expiry, no expiry dispatch/result, and final
effects equal successes. UNKNOWN, NOT_FOUND, failed/rejected/nonadmitted/unresolved
attempts fail it. Preserve original workload verdicts and all-success failures;
new completion metric is not all-success/full N5 qualification or a relaxed SLA.
Retain all skipped slots, live/closed statuses, sensor gaps and provenance.

Raw captures/journals/resources/provider samples local with hashes; explicit public
selections, complete trace/provider/capture/footer gates, owned cleanup. No old
unknown is retroactively resolved. Underlying CONTROL delay/clock expiry, loaded
ROS discovery and remaining M3/hardware/clock/security/resource gates stay open.
