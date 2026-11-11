# Bounded receiver retention candidate

Freeze plan before implementation and source before validation/live. Preserve old
failed cohorts unchanged. PR2 draft, M3 open, Intrinsic/M4 untouched.

Candidate: after authenticated, structurally valid, sequence-consumed COMMAND
admission reports soft ClockError unqualified/expired, retain the immutable frame
in a fixed FIFO. Do not retain future_sample, hard clock errors or invalid frames.
Recheck original context/identity/origin/budget with Session::check_command before
one forwarding; never call admit_control again or resend through SRT. Other control
traffic (especially clock probes) continues. Later COMMANDs queue behind held ones.

Receiver ready+retained CONTROL occupancy <=64, COMMAND occupancy <=56, reserving8
slots for other control messages. Fixed FIFO storage, no dynamic per-message
allocation; bounded8 revalidations per owner loop. Overflow reports BUSY, never
evicts an older command. Incoming ready command counts decrement under existing
poll mutex. Original receive generation/session retained; sensor-only replacement
does not invalidate CONTROL. Context replacement/shutdown clears held entries.

Each entry has a resource hold ceiling of original valid_for_ms after local receipt,
never renewed. This is not an execution deadline or a new source budget. Every
forward still derives the conservative deadline from freshly qualified age of the
original source timestamp. Trusted stale age is dropped with diagnostic START_EXPIRED;
unknown clock at resource-ceiling expiry remains a diagnostic clock failure. No
journal mutation, durable negative inference, deadline extension, absence seal or
accepted-command replay is authorized by a dropped entry.

Validation phase before live: Release/Werror build, full SDK+ROS suites, host tests,
source/syntax/diff checks. Add deterministic FIFO/capacity/reserved-space/ceiling/
context tests, fresh-age and stale-age checks. Real IPv4/IPv6 cases must show a
150ms receiver qualification gap recovering with original5s command budget, one
SDK handoff/forward/effect and matching closed journals. Separate500ms ORIGINAL
fixture route/command budget expires before next1s probe: no forward/effect,
no fabricated terminal result, retained uncertainty/one SDK handoff. Also test
context loss and shutdown with a held entry, no forwarding/replay. Preserve prior
controlled rejection evidence; direct Session rejection contracts remain valid.
Record all attempted validations including failures; any corrective revision must
retain its failed source/log before a separately frozen validation revision.

Live only after gates pass, exactly once and stop on first failure:
1. N0 seed4211,15s; 2. N5 seed4211,300s. No further seeds/retries this cohort.
Same pinned image/provider, dynamic neighbors,200/50Hz sensors,2s offered command
slots, original5s source budget,8s result drain, command/provider diagnostics and
stable tcpdump drain. Freeze rebuilt8 runtime hashes across live; no concurrent
builds/tests. New revalidation trace is distinguished from initial gate decision;
every success needs a unique forwarding-admission/worker pair bound to original
request/session/route/origin/sequence plus durable journal/dispatch/one-SDK proof.

Record old/new runtime artifacts, source/build/test provenance, original workload
versus progress verdicts, unresolved live/closed states and telemetry delivery gaps.
Raw captures/journals/providers/resources local with hashes, explicit public
selections. Cleanup owned namespaces only. Even a pass is bounded candidate
coverage, not resolution of historical uncertainty, clock-expiry cause, full N5/M3,
physical-wire/clock/security/resource qualification or transport superiority.
