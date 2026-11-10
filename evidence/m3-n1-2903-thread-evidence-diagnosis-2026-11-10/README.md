# N1/2903 missing thread stacks — retained-only diagnosis

**Observed mechanism: a task-list/read lifetime race inside SRT provider cleanup.**
The collector enumerates three provider TIDs that no longer have readable procfs
files when it reaches them. The assessor treats their still-live parent process
as requiring every listed task stack to remain readable, so it fails. Normal
provider thread exit during cleanup is strongly supported; exact per-task
exit/reuse proof is not retained. No SRT protocol defect or permission expansion
is established or needed by these observations.

Original live results remain **1 PASS /1 FAIL /7 NOT EXECUTED**. The N1/2903 case
is not requalified. No tuning, retries, new experiments, collector runs, tests,
builds, Docker calls, assessor/filter changes, new freeze or grant. All seven
remaining cases and all other campaign stages stay disabled;29 completed IDs
remain excluded. M3 open/PR2 draft/Intrinsic M4 untouched.

## What the captures establish

The failing root is operator bridge PID111/start_ticks64834, in this case's
recorded owned namespace. Its final launch token, boot/time proof, process
identity and per-launch shutdown trace are retained. Do not identify processes
or threads across cases solely by their reused numeric PID/TID values.

| Missing TID | Earlier task name | Earlier task start_ticks | Retained pre-signal evidence |
|---:|---|---:|---|
|128|rwx-shard-0|64890|3 successful stat/stack samples; futex wait|
|129|rwx-shard-1|64890|3 successful stat/stack samples; futex wait|
|130|rwx-readiness|64891|3 successful stat/stack samples; epoll wait|

These are provider scheduler/readiness threads, not the separate journal-worker
process PID127. The last successful sample ends221.795625ms before SIGINT end.
In the next sample, each listed TID has **stat, wchan, syscall and stack all
FileNotFoundError/errno2 (ENOENT)**:12 missing read outcomes, of which3 are stack
reads. It is not merely an unreadable stack with a still-readable task stat.
Other tasks remain readable, and the parent PID/start_ticks still match after
sampling. There is no recorded EPERM/EACCES or observer budget exhaustion.

All times below are milliseconds after supervisor SIGINT end:

| Event | Relative time |
|---|---:|
|provider_cleanup_begin, transport TID125|24.318083|
|journal worker_join_end, endpoint TID126|24.494792|
|observer sample4 begins|28.612958|
|observer sample4 ends, root identity still matching|30.201042|
|provider_cleanup_end|30.882958|
|endpoint transport join completes|31.426917|
|node endpoint join completes|32.004333|
|main context shutdown ends|58.209083|
|supervisor reaps operator, exit0/unforced|237.356458|

The entire failing sample lies within the6.564875ms provider cleanup call bracket
and after the separately registered journal worker joined. The journal worker's
missing process record is supported by the existing join-aware gate; the failing
objects are threads within the surviving bridge process. The next observer
sample begins281.317167ms after SIGINT end, after reap, and reports root/process
absence. Footer:5 samples,88 stack readsOK,3unavailable, completed/no exhaustion.
The old pure coverage function reproduces exactly `live target kernel stack
unavailable` from these retained inputs.

## Why the observer and gate disagree with task lifetime

The frozen collector's collect() lists `/proc/PID/task` once, sorts entries,
then sequentially reads each task's stat/wchan/syscall/stack. The returned task
list can outlive a task. Only the parent process identity is checked again;
there is no per-task identity/absence recheck or per-read timestamp. The failing
sample retains the TIDs because they came from that enumeration, even though
the first subsequent stat read already returns ENOENT.

The frozen coverage() sets in_wait from sample end versus supervisor reap,
checks the process PID/start_ticks, then requires every enumerated thread's
kernel stack to be OK. It does not distinguish a confirmed task disappearance
from a read failure. Parent liveness does not establish continued liveness of
all earlier enumerated tasks. This is the concrete collector/assessor evidence
gap responsible for the strict stop, without changing the recorded verdict.

## Pinned source and the passing control

The clean local provider source is exactly qualified commit
52be7c86ee1f303cbb0c8718c364217e4dd97a36; installed archive SHA256
3fa56e487e6c6408d9e41779d18aba9ff866978892ddbe3b88ac12fc51141673 matches the freeze.
The bridge places provider_cleanup_begin/end immediately around srt_cleanup().
Pinned provider source names scheduler threads rwx-shard-N and readiness thread
rwx-readiness. Its ordinary cleanup path stops the runtime scheduler; scheduler
stop stops/joins readiness and joins shard workers. This supplies the ownership
and expected cleanup mechanism, not an identity-specific runtime exit event.

For passing N1/1701, cleanup runs at21.903583–27.917958ms; its first post-signal
sample begins65.527041ms, after cleanup, and the provider TIDs are already absent
from enumeration. That case has76 readable stack observations/0unavailable and
passes. It did not sample the same short teardown window. This is a retained
comparison, not a new seed experiment or proof that the seed caused the race.

## What cannot be recovered from these captures

No failing-sample task start_ticks, explicit task-list timestamp, individual
read timestamp, post-ENOENT task identity/absence check or TID-specific provider
join/exit record exists. The aggregate provider bracket records return from
srt_cleanup, not its return value. Earlier successful identities plus the bracket
strongly support ordinary teardown, but cannot certify individual exit ordering,
exclude intervening TID reuse or invent the missing stack contents. Root exit0
and readable stacks elsewhere cannot fill that gap. No original historical hang
cause, protocol failure, blocked-thread diagnosis or N1/2903 acceptance follows.
Later strict combined/progress/profile gates remain uncredited as before.

The appropriate next change is bounded per-task identity/absence evidence around
reads, with a separate confirmed-disappearance classification. Any future gate
must preserve failures for genuine read errors, identity reuse/ambiguity,
truncation and missing proof; blanket ENOENT acceptance or counting missing
stacks as readable would not resolve this gap. Offline regression cases should
cover exit between enumeration/stat/stack, TID reuse, denied reads and live
readable tasks. **No such change or test is implemented in this diagnosis.**

## Verification and artifacts

analyze.py reads retained JSONL/stage/identity/shutdown records, compares the
passing case, checks the pinned source, and invokes only the unchanged pure
coverage function to reproduce the failure. It does not invoke collect/observe,
read live procfs, call Docker, run tests or restart anything. diagnosis.json
contains thread history, exact missing read statuses, both timelines, source
excerpts with line numbers/hashes and explicit evidence limits. analysis.log
retains its result; input-hashes.json binds the analysis code, source references,
old indexes and unchanged original decision files.

Before and after analysis, all frozen source/inputs/current14/preserved13/full
SDK/ROS/provider chain/native87 and old raw/public indexes verify unchanged,
including all238 stopped-run files/927,231,952bytes. Original cohort and both
strict decision hashes remain identical; all seven absent output directories
stay absent. postflight.json and public-artifact-hashes.json record this
read-only diagnosis only. Prior passes/failures and the stopped grant are intact.
