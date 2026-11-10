# Single two-loss seed2903/30s shutdown diagnostic — 2026-11-10

**PASS: the one prepared two-loss seed2903/30s diagnostic.**
Exactly one separately authorized attempt used the unchanged prepared freeze,
current socket-disposition14 build, tracing and native observer. It passes fault,
SENSOR/capture/accounting, lifecycle, stage/disposition and cleanup gates.
No tuning, native rebuild, two-loss-4211, command, expiry/replay, additional attempt
or other campaign stage. All29 remaining cases stay disabled; M3 open/PR2 draft/
M4 untouched. Original N3 remains8 PASS/1 FAIL/unknown hang cause; no cohort splice.

## Fixed scope and measured two-loss proof

The authorization binds preparation freezeb9edfe65b927, one seed2903/30s session,
first mixed source row1/positions2/3, SENSOR messages7/8. Fresh captured ISN,
destination socket ID and UDP tuple define two exact u32 selector rules before
publication. Both counters start0 and end exactly1packet/1drop (494/438bytes).
Rules stay through both result barriers, then the owned hook is removed and its
empty readback verified before capture closure and observer arming. This is
deterministic source selection, not random netem loss or production tuning.

Independent SDK/native/PCAP/parity/typed proof confirms selected messages7/8 and
exact SRT-accept-to-receiver gap2, with the existing two-loss validator. The source
fence is30.053584597s:200.009419Hz IMU/50.010673Hz joints, zero skipped source slots.
All six accounting balances are0; modeled published-age maxima26ms/41ms.
7514produced versus7254observed leaves260 samples accounted across upstream DDS8,
admission19, outbound replacement230, selected SRT gap2 and receive replacement1.
This is latest-only bounded delivery, not lossless availability, physical age or
full N3/M3 qualification. Full final packet populations and raw hashes retain
their original controls; no missing phase is inferred.

## Shutdown evidence

Observer startup/exec/clock/capability/identity/ready gates pass before SIGINT.
It targets only operator bridge and registered journal-worker descendants; native
ARM64 image/filter/SYS_ADMIN-only/NNP/read-only/private-PID/output constraints and
bridge capability reduction are unchanged. Original5s child waits remain.
There are25 successful kernel-stack reads/zero unavailable;24 nonempty reads
inside the child wait, including one contained post-signal sample. The known
worker is explicitly absent after valid join evidence; PID reuse/read errors are
not waived. Bounded observer finalization passes without debugger or forced kill.
Kernel stacks under amd64 emulation are not application user frames or overhead
qualification; worker exit cause/code is not inferred from the join marker.

Operator59/robot43 zero-drop records pass common-stage and explicit socket gates.
Robot final slots are all already invalid, with no local close bracket. Operator
session-stop closes its data sockets first; its two remaining listeners close in
the final sweep. All four traced operator srt_close calls return0. This does not
reconstruct an earlier untraced robot close result or prove whole-process fd
leak freedom. Prior missing-marker FAILs remain unchanged.

All children exit0/unforced: operator216.091042ms, robot bridge316.515126ms,
source167.677083ms after signal completion. Underlying SENSOR adapter and final
diagnostic both PASS, driver exits0. No bridge hang occurs here; the original
seed4211 shutdown failure was neither retried nor attributed by this run.

## Integrity and disposition

Owned selectors restored, packet captures closed, observer exported/reaped before
lab removal. All lab/observer containers, internal network and observer volume
are removed/absent; credential deleted, no forced cleanup. Prepared source/input/
helper freeze,14 current entries, oldshutdown13/full earlier chain/provider and
87reused native inputs match postflight. All prior raw evidence indexes remain
unchanged, including the earlier failures and healthy N0 PASS. No heavy tests,
native builds or other fixture runs overlapped measurement; prior497 offline
tests retain their scope and were not rerun for this execution.

PLAN/authorization/preflight bind the sole grant. Primary assessments, selected
source proof, counter/restoration logs, actual stage/slot/result/observer/child/
ready/exec/policy records and postflight are public.124 closed local artifacts,
including exact packet/log populations, are hash-indexed. Fault logs originally
reside in measurement/; their public copies preserve exact bytes. Preparation
files remain immutable/disabled; its separate one-shot output now exists and
cannot be reused. No additional case, retry, campaign advancement or acceptance
follows this bounded diagnostic PASS.
