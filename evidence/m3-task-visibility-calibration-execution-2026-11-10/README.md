# Bounded per-task visibility calibration — PASS

**Readiness PASS and controlled-fixture PASS; driver exit0.** Exactly one
invocation on freeze6357a2c0f58d5c40751a7e96e52d6825ade3a29b2ad03bc6bcef0ca903474f9c,
source1970eaa28701607cb78ce67b2fb62cffc73659ff, exact collector
6deab3c5e83e48b7c33dbbb4613c361469d9b62aa1bea86db0c1a8012cfae72e with explicit activation.
No tuning, retries, build/test overlap or N1/2903 rerun. All38 campaign case IDs
remain disabled; original1PASS/1FAIL/7NOT EXECUTED and N1/2903 failed assessment
SHA are unchanged. M3 open/PR2 draft/Intrinsic M4 untouched.

## Observed calibration

| Stage | Outcome |
|---|---|
|One native observer readiness self-check|PASS: exact collector/import/activation and role-policy proof; no target during this stage|
|One controlled parent/worker fixture|PASS: two readable observations of the registered worker, controlled release/join, later complete-enumeration absence while parent alive, then normal controlled parent shutdown|

The actual target is parent PID7/start_ticks609, worker TID8/start_ticks625 in its
own recorded PID namespace. Native ARM64 observer and pinned amd64 Python target
share the recorded boot and zero time-namespace offsets. This establishes the
scoped native access/emulated-TID mapping for this fixture, not other workloads.

Worker live samples span6,661,634,919–6,912,879,252ns. Release is7,028,505,960ns;
worker-return stage7,029,026,044ns; join recorded7,030,193,752ns. The later sample
7,164,042,710–7,164,353,294ns omits that TID from a complete enumeration and retains
its prior identity hint. Parent SIGINT begins7,234,302,919ns, after absence proof.
All stage identity/sequence/time/control bindings pass.

Footer:3 bounded samples,5 kernel stack readsOK/0unavailable, no exhaustion,
userspace stacks false, reason parent_stop. Five task records contain30 successful
content reads (five original files plus final stat each) and five successful
final directory checks. The missing-task hint matches TID8/start_ticks625, with
status not_in_complete_enumeration. Every confirmed_exit field remainsfalse.
Raw/per-task identity/read brackets and footer counts recompute consistently.

Parent exit0/unforced, signal-end-to-reap18,381,750ns under the original5s wait.
No post-SIGINT task-read availability is qualified; all three samples precede
SIGINT. Synthetic target shutdown time is not a bridge/SDK or overhead benchmark.
The live path observed later enumeration absence, not a forced mid-read ENOENT
race. Exact N1 race reproduction and real TID reuse remain outside this result.

## Policy, bounds and stop conditions

Three containers were created/started once: readiness observer, controlled target,
active observer; two private output volumes. Observer uses native ARM64/pinned
image, SYS_ADMIN only, NNP/default-deny unchanged filter, read-only root/bundle,
network none and the exact owned target PID namespace. Target/supervisor masks
are zero, NNP/seccomp enforced. No host PID namespace, broad repository mount,
Docker socket, debugger, SDK/ROS process or permission expansion.

Original collector8process/64task/65examined-entry/512history/16KiB/48sample/0.25s/
12s limits and5s child wait remain unchanged. This calibration used its declared
6s host phase,8MiB snapshot guard and bounded Docker commands, without extending
any timeout or adding a retry. Five initial Docker cp misses occur within the
predeclared bounded readiness-file polls (four target-info, one observer-ready);
they are preserved in the command log, not failed gates or restarted attempts.
Both actual stages pass. No campaign or additional calibration was started.

## Integrity and retained artifacts

Driver cleanup and independent final read-only verification pass: all three owned
containers and both volumes absent, frozen source/inputs/current14/preserved13/
full SDK/ROS/provider chain/native87/candidate/private host binding/read-only
bundle/prior public and raw hashes unchanged. Preparation public index and exact
N1/2903 failed assessment SHA verify. Seven later campaign directories stay absent.
The earlier import-failed preparation is also preserved, not relabelled.

run/ copies every raw output file byte-exact, including readiness/preexec/policy,
target/worker identity and stage records, observer JSONL, control authorities,
child shutdown, commands, driver report and postflight. authorization.json and
preflight.json bind the exact user grant; gate-report.json summarizes actual
scope/counts and schema-summary.json derives read/identity results. No capture
was edited to add metadata or change status.

Full raw output remains at
`.local/task-visibility-calibration-20261110T170526723486Z`, host log at
`.local/task-visibility-calibration-execution-20261110.log`;77 files/600,527bytes
(including the empty host stdout log) are SHA-bound in local-artifact-hashes.json.
public-artifact-hashes.json binds all public copies and summaries. No new tests
are credited; earlier23 preparation/28 candidate/511 existing results retain
recorded offline scope.

This passes one bounded native visibility calibration only. The campaign
assessor/filter/driver and original N1/2903 failure are unchanged. No confirmed
thread-exit acceptance rule, blanket ENOENT waiver, missing-as-readable conversion,
transport/protocol qualification, diagnostic-overhead equivalence or full M3
acceptance follows. Next engineering work is offline assessment rules for the
new evidence; no fix, fresh campaign freeze/grant, retry or later case is queued.
