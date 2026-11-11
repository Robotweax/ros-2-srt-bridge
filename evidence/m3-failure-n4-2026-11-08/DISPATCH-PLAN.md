# Additional durable-dispatch-before-start boundary

All nine cases in the corrected CLOCK-REVISION cohort pass. They cover receiver
admission before commit, handler already atomically started, and durable result
commit. Add the distinct boundary after durable DISPATCHING commit but BEFORE a
handler execution grant/start, using existing JournalPoint::dispatch_committed.
This avoids treating after-start and before-start interruption as equivalent.

After231 host tests, syntax/diff and standalone peer Release/Werror build pass,
freeze source/plan and run exactly once:
`python3 tools/m3_n4.py --output .local/m3-failure-n4/dispatch --dispatch-only`
Three fresh cases in order dispatch-{both,to-robot,to-operator}; stop at first
unexpected failure and leave the rest unexecuted. No re-execution of earlier cases.
Same original5s command budget,20s test coordinator watchdog,2s VM hold and measured
guaranteed cut>=2s, explicit kernel readback/drops, same worker identity guard,
conservative mapped deadline gates, original owners/ingress/hash proof, QUERY-only
subsequent requests, one SDK handoff, matching durable outcome, bounded shutdown,
closed journals and restored ready/clock qualification. No production SDK/ROS/
worker/provider change; only the standalone fixture gains this phase selector.

The live WAL-aware read must show state DISPATCHING and barrier effects0. Its
recorded dispatched_ns precedes barrier_ns, which precedes worker resume. Any
pre-effect success/rejection/expiry result timestamp must follow resume; success
requires original conservative receiver deadline still valid, exactly1 effect and
matching100Hz/generation1 proof. Safe context rejection/expiry requires0 effects
and no result. The native existing hook holds before returning the dispatch ticket,
so no handler start ticket can be consumed until resume. Same-context restoration
before expiry can legitimately succeed. All prior trace/lifecycle/journal/no-replay
gates remain; no crash/ROS sensor-age/full N4 or M3 acceptance is claimed.

The revised native fixture has a distinct binary hash from the completed nine-case
cohort; preserve separate source/binary provenance and its earlier recorded
post-run inventory. Installed production runtime hashes remain unchanged. Historical
failed originals and missing-footer cause remain untouched. No further live runs
are specified by this additional plan. PR2 stays draft, Intrinsic/M4 unchanged.
