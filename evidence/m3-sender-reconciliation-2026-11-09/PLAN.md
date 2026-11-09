# Sender receipt correctness change

Implement the next DELIVERY_PLAN blocker: a lossless opaque receipt on the
original one-use sender proof. Only the transport can publish queued/SDK-accepted/
abandoned disposition; only the minting live worker generation can consume an
abandoned receipt once. BUSY preserves it. No trace-derived authority, new ticket,
expiry, receiver result or unrelated-session invalidation.

Coordinator retains at most one receipt per64 tracked admissions and services
dropped ones after its original job finishes. Reject new admissions before durable
insert when tracking is full. Worker/journal validate original peer role, owner,
session, origin/deadline, command/route/hash and current state. Change only sender
local_queued/rev0 to provisional UNKNOWN/reconcile_required; preserve higher peer
states and duplicate reconciliation. Query-first UNKNOWN remains nonterminal.

Bump private worker IPC to4 for the added operation; old workers fail closed.
SRT/ROS wire, rates, budgets, clock rules and queues unchanged. Isolated new SDK/
ROS build/install prefixes preserve all calibrated binaries/provider/historical
evidence. No new N5 cohort, tuning, live forced expiry or historical118 replay.

Tests: journal exact-row/state/context/storage/result races; real worker rejects
raw/foreign/stale/reused/unclaimed/SDK-accepted receipts; bounded admission and
recovery; native IPv4/IPv6 actual pre-handoff abandonment and endpoint consumption
with fresh journals. A default-false test-only command-handoff hold, never ROS/
CLI/env configured, permits deterministic context-loss before SDK acceptance.
No shortened lease or command expiry is needed. Run full affected SDK/ROS and
host guards; no builds/heavy tests overlap native calibration. Retain failures.
This closes status delivery, not historical nonexecution or full M3 qualification.
