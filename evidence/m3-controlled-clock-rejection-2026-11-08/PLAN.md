# Controlled clock rejection and uncertainty coverage

Freeze plan, then implementation source before execution. This is controlled
negative coverage, not a reproduction/retry of the historical N5 seed4211 failure.
No new N5 cohort in this step. No production/provider, clock-policy, start-budget,
expiry-seal, replay or DDS-default change. M3 open, PR2 draft, Intrinsic/M4 untouched.

1. New direct production Session/CommandJournal contract: no-loss valid command
   positive control, expired receiver clock negative, and future-age negative.
   Construct normal management handshake/probes and canonical command payloads.
   Logical times are explicit; future case advances only sender logical time by
   200ms after zero-offset qualification. This deliberately violates the clock
   model, not the host clock or production transport; it is not a wire/SDK test.
   Verify future_sample9 with clock state none0 versus expired2, both mapped to
   SessionError clock_unqualified13; no endpoint closure, no receiver admission.
   Keep original sender context/5s deadline, QUERY/NOT_FOUND without negative
   outcome inference, duplicate admission replay watermark, closed/reopened sender
   UNKNOWN and no fresh transmit permission. Positive control must admit normally.
2. Extend existing native real SRT IPv4/IPv6 receiver-expiry test, one invocation
   per family in final SDK suite. Receiver test configuration keeps qualification
   age150ms with existing1s probes. Correlate receiver rejection and original
   COMMAND peer error by identity/session/sequence; preserve original5s budget.
   Explicit QUERY before/after deadline must report local LOCAL_QUEUED and peer
   NOT_FOUND without result. Restore normal receiver policy on a test-owned peer
   restart; same accepted command stays UNKNOWN/reconcile_required and is queried,
   never replayed. Re-executing the existing ID is reconciliation only. Closed
   journals must retain original context/deadline, no receiver record, no result;
   fixture effects0 is observed, not a general inference from NOT_FOUND.
3. Final Release build/Werror and full SDK suite once with stop-on-first-failure;
   host suite and source/syntax/diff checks. No runtime install or ROS rebuild is
   needed for test-only changes; prior ROS41 remains prior validation. Record all
   eight runtime hashes and provider pin before/after; they must remain unchanged.
   Retain originals, logs, source/build identity and local journal hashes. Native
   sockets are owned loopback inside pinned network-none Docker; no PCAP/traffic
   shaper or wire/age/resource qualification claimed. No tests/builds overlap live
   qualification runs. Stop on failure; preserve failed attempt, no retry-to-PASS.

Acceptance means controlled boundary and uncertainty contracts pass, not full N5,
clock-model validation on hardware, a historical root cause or production fix.
If a failure requires implementation changes, archive that failed source/run
before a separately frozen revision; never silently replace its verdict.
