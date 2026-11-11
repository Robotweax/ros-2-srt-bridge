# DDS command freshness and unresolved-intent diagnosis

This follow-up identifies an admission/completion limit while preserving every
execution gate. It adds diagnostics and observation data, not a retry, alternate
success condition or new terminal outcome. The SDK, SRT source, wire v1 and worker
IPC v3 are unchanged. The default DDS startup/transport and workloads are unchanged.

The prior N2 run ended with both peers ready but one intent unresolved. Separate
read-only inspection found its sender entry still LOCAL_QUEUED/revision 0 and no
receiver entry. Its first observed outgoing COMMAND capture was about 2.13 seconds
later than the application timestamp relative to median local HELLO timing.
Subsequent captured ERROR replies carry NOT_FOUND. This is an offset-relative
publication/queue/capture estimate, not isolated network delay; it cannot locate
the delay inside DDS or the kernel. See prior-n2-analysis.json. The fixed-layout
inspection anchors the recorded clock-namespace digest and CDR encapsulation;
it is not a general RTPS parser. Original raw artifact hashes are retained.

The new live diagnostics make the boundary directly observable:

- control_checks separates accepted session validation from session, peer,
  namespace, sequence, invalid-time and stale rejections. It runs after message
  kind/route/request-ID checks. The first failed check wins. Accepted here does
  not imply queue admission, durable journal admission or a handler start.
- stale_commands records a count plus the last stale ID, application send time
  and callback ingress time under the session mutex. The freshness cutoff stays
  exactly 1.5 seconds, including when independent HELLOs keep the session live.
  A rejected frame never advances the replay cursor.
- remote_not_found counts receipt-matched ERROR/not_found frames at the sender.
  It is separate from repeated local status polling observations.
- control_publish_max_ns and control_publish_over_freshness measure the Reliable
  publish call only. They do not measure pre-call scheduling, post-call history,
  transport repair, kernel/network queueing or receiver executor delay.

Workload rows now retain the last local status snapshot, observation count and
NOT_FOUND snapshot count, including for the final unresolved row. found describes
the local sender journal lookup, while local_error can carry the cached remote
lookup error. A locally found LOCAL_QUEUED entry with NOT_FOUND is therefore not a
confirmed receiver admission. budget_elapsed means five seconds since the local
client submission timestamp, not an authoritative receiver deadline or expiration.
None of these observations creates a terminal result or evidence of nonexecution.

Execute QUEUED confirms local queue admission only; the receiver journal and
handler outcome still require subsequent status evidence.

A live session does not guarantee that every Reliable message arrives while it is
fresh. If a COMMAND is dropped by the freshness gate before receiver admission,
QUERY has no receiver entry to report. The sender must retain the original ID
and uncertainty; it cannot infer EXPIRED/SUCCEEDED or send an old intent again.
The existing workload continues to block later slots while that intent is pending.
The new fields make this distinct from a session rediscovery deadlock. A future
resolution protocol would require explicit durable receiver evidence and a defined
start fence; a timeout or bare NOT_FOUND alone is insufficient.

See [results](RESULTS.md) and command-diagnosis.json for the three short N2 seeds,
N0/N4 checks, the preserved N5 startup failure, and full DDS fault acceptance.
All source inventories, binary hashes and installed Python bytes are verified.
Raw PCAPs/journals remain local; only sanitized results and their hashes are stored.
No full-duration impaired matrix, M3 acceptance, cross-host clock/security parity,
matched CPU/wire result or performance advantage is claimed. Intrinsic/M4 remains
untouched. The previous full M2/five-minute N0 evidence belongs to commit 940b4cb.
