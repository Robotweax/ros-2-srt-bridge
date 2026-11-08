# Separate conservative clock-domain deadline correction

The identity-revised first admission/both case FAILED after the planned outage.
New child records confirm /proc/exe=/run/rosetta/rosetta, exact worker argv,
stopped state and stable PID/start ticks, so the new identity guard works.
The worker resumed, performed one effect and committed success, but the fixture
incorrectly required the receiver's local deadline to equal source origin+5s.
Observed receiver deadline537595890394ns vs source deadline537601704201ns: the
receiver's mapped deadline is5813807ns EARLIER. This is expected conservative
ClockMapper behavior, not evidence of a production deadline extension. The
original failed verdict and unexecuted remaining eight cases remain unchanged.

Correct only the test's cross-domain assertion: sender journal deadline must
remain exact original ingress+5s and submitted deadline; receiver original source
identity/origin/hash/session must match but its conservative deadline may be
shorter, must remain>source origin and must never exceed sender expiry on the
proven shared VM monotonic clock. Use the receiver deadline for fresh-dispatch/
resumed-effect checks. Success still requires matching durable result/state,
exactly1 effect,100Hz/generation1 and one SDK command handoff. Rejection/expiry
requires0 effects and no result. Committed success must still reconcile. This
corrects a clock-domain test assumption without weakening the production deadline.
Add explicit restored ready/clock qualification before the2s settled observation
and final snapshots, with a bounded15s qualification wait. All previous gates stay.

230 host tests, including shorter-mapped/extended-deadline negatives and unqualified
restoration, pass. Standalone peer rebuild passes Release/Werror; no production
SDK/ROS/provider/worker code or binary change. Commit plan/source, then exactly once:
`python3 tools/m3_n4.py --output .local/m3-failure-n4/n4-clock`
Same nine phase/direction order, stop at first unexpected failure, preserve all
originals and leave remaining cases unexecuted. No additional live execution or
unplanned retry. Both prior cohorts remain failed fixture development evidence,
not accepted production/N4 cohorts. Failure controls remain independently passed.
