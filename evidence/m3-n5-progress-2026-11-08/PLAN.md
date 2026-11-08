# Bounded N5 forward-progress and cold-start diagnostic plan

Freeze this plan and implementation in Git before execution. Exactly one ordered
set, fresh owned namespaces per slot, seed1701; no retry, no replacing failures.
Do not change defaults, SDK/ROS/provider binaries, timeouts, command budget,
workload rates or shaping. No dependency repository changes. No concurrent builds,
tests or experiments during measured runs. PR2 stays draft; M4 untouched.

1. SRT N0 preflight15s, existing command/provider traces and capture drain check.
2. If preflight passes, SRT N5 steady60s, same diagnostics, default dynamic
   neighbors, unmodified512kbit/s/16-packet shaping and128kbit/s competitor.
   This checks prospective progress, not reproduction of the old spontaneous reset.
3. DDS N5 system/simultaneous,15s measurement after qualification or original45s
   readiness failure. Both peers and telemetry start under active impairment/load.
4. DDS N5 system/control-first,15s measurement. Source stays disabled until
   control qualification, with zero produced samples verified. Separate candidate.
5. DDS N5 paced-sensors/simultaneous,15s measurement. Separate existing candidate;
   sensor-only asynchronous flow controller, unchanged command/liveness QoS.

DDS slots are independent diagnostic contrasts: execute each once even if another
DDS slot fails. SRT N5 is skipped only if its N0 preflight fails. Stop within each
run at existing failed gates. Keep original outcomes and unexecuted slots explicit.

A new2048-record, <=1Hz same-phase/readiness development history records local
DDS command diagnostics and typed callback counts, plus phase/readiness transitions.
It fails on exhausted/truncated history; final counts must match. Distinguish no
diagnostics, no complete endpoint match observed, no received HELLO observed,
HELLO received without readiness, and readiness observed. These are sampled
observations, not RTPS decoding, authenticated delivery or a unique causal proof.
Local state may miss transitions. No runtime discovery policy is changed.

All DDS children require explicit pre-signal status/SIGINT/exit/forced-kill
reports. A peer/parent abort releases waiting scenarios for controlled cleanup
before namespace removal. Failed startup is still FAILED even with clean shutdown.
Parent12s allowance covers cleanup only, not startup/readiness extension.

For completed runs preserve all attempts, skipped slots, uncertainty, source
fences and original5s deadlines. Read journals only after workers close/checkpoint.
Confirmed successes require matching durable identity/context/result proof and
receiver dispatch before its earlier/equal deadline. SRT sender trace requires
exactly one provider_sent per successful intent and never more than one per ID;
all bridge incarnations require complete zero-drop trace lifecycles. UNKNOWN,
NOT_FOUND or elapsed time never become success/nonexecution/expiry evidence.
Report gaps/skipped slots explicitly, without a latency or command-every-slot claim.

Record all manifests/logs/errors, source commit/image and eight binary hashes
before/after, shaping/readbacks, competitor load and closed-journal hashes.
Capture-population and clock gates retain independent verdicts; failed capture
populations are not rescued by command success. Preserve raw original files local;
archive selected metadata and hashes, exclude journals/packets/credentials/full
inspect/environment/resource dumps. No full N5/M3, age/security/resource parity,
physical sensor/hardware, cross-host or transport-superiority acceptance follows.
