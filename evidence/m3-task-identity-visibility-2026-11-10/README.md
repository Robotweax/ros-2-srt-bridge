# Bounded per-task identity and absence visibility — offline candidate

**28 new regressions and511 existing tests PASS offline.** A separate observer
candidate adds optional task identity/read/absence records. It is off by default
and not bound into any live observer bundle, entry wrapper or campaign driver.
No live procfs target, Docker call, build, tuning, retry or new live experiment.
The frozen observer, filter, entry, driver and assessor stay unchanged.
N1/2903 remains FAIL; the cohort remains1PASS/1FAIL/7NOT EXECUTED. All seven
remaining cases and other stages stay disabled;29 completed cases excluded.
M3 open/PR2 draft/Intrinsic M4 untouched.

## Activation and scope

Candidate shutdown_observer.py accepts **--task-visibility**, only in procfs mode.
Default operation still calls the byte/AST-equivalent original collect() path;
it does not run the new task collection. The parent Observer class/GDB path are
unchanged and do not opt in. Existing sidecar/observer_entry files and frozen
bundles cannot silently select the new candidate or flag. No new freeze/grant or
calibration package is created here. Future native use needs separate exact
bundle/entry activation and bounded calibration before qualification.

This adds diagnostic work, not a transport setting change. No sampling rate,
process/thread/read/sample/time budget, permission, filter, queue, clock, command
deadline or child wait is tuned. Offline success does not establish native
syscall compatibility, observer overhead or loaded-case qualification.

## Recorded evidence

The opt-in collector preserves the old top-level stat/wchan/syscall/kernel_stack
results and raw OK/unavailable/truncated status. Each task adds task_evidence
schema1 containing:

- Parent PID/start_ticks, task enumeration bracket and selected TID.
- Individual begin/end times and raw results for stat, wchan, syscall, stack and
  children. Each stack is attempted exactly once; there is no retry/backoff loop.
- A fixed final stat read and final task-directory presence check, each timed.
- Parsed before/after task identity: TID/start_ticks/name/state. Invalid, mismatched,
  malformed or truncated stat cannot supply identity.
- A bounded previous-sample identity hint and explicit changed-since-prior flag.
  That hint never fills a missing current identity or proves uninterrupted TID use.
- The final parent identity check and a descriptive task lifetime status.

Descriptive statuses distinguish matching identity, TID reuse within the bracket,
appearance after initial absence, absence after a known initial identity, absence
without a current identity, ambiguous stat/presence failures and parent identity
change/unavailability. Every record has **confirmed_exit=false**. Directory
inode/device are observations, not TID incarnation or exit authority.

The statuses are orthogonal to stack readability. A matching task can still have
EPERM/EACCES/I/O/truncated/unavailable stack data; it is never rewritten to an
empty successful stack. Conversely a task can disappear after a successful stack
read. ENOENT is retained as absence evidence, not blanket acceptance, an exit
code, a no-reuse guarantee or authority to replay/expire a command.

For earlier known tasks missing from the next listing, a bounded hint says
not_in_complete_enumeration or not_in_bounded_scan. Neither is confirmed exit;
a truncated scan cannot prove absence. Histories are pruned each sample and
invalidated when the parent identity no longer matches.

## Fixed bounds and compatibility

| Bound | Value |
|---|---:|
|Owned process/descendant limit|8, unchanged|
|Sampled tasks per process|64, unchanged|
|Directory entries examined per process|At most65; overflow explicit|
|Bytes per content read|16384, unchanged|
|Task identity history|At most8×64=512; one previous sample only|
|Task file operations per selected task|7: five original files, final stat, final directory check|
|Stack attempts per selected task|1|
|Sample count/period/time limit|48/0.25s/12s, unchanged|

Existing child-process discovery is unchanged; the seven-operation bound above
covers the task's own files, not child-process identity reads. Enumeration uses
a bounded scandir scan and sorts selected entries. If overflow occurs, these
are not claimed to be the globally lowest64 TIDs; threads_truncated remains
true and original gates still reject it. This limits record/work counts, not a
hard latency guarantee for a procfs syscall. Additional identity/presence work
needs future overhead/native validation, with no assumed equivalence to old
observer timing. Prior-sample hints cannot recover identities absent for longer.

Begin/sample records mark the opt-in schema. The original footer still counts
actual kernel-stack read outcomes: missing stacks remain unavailable even when
new absence metadata explains their context. No assessor or gate acceptance
change is included, and no old capture receives invented new schema fields.

## Offline regressions

28 tests use temporary procfs-shaped directories and deterministic mutations
between enumeration, stat, stack and final checks. They cover live readable
identity/timing, exit before first stat, exit during/after stack access, TID reuse,
reappearance after absence, previous-sample identity changes, malformed/wrong/
truncated stat, stack truncation, permission/I/O/ENOTDIR, parent reuse/disappearance,
scan overflow/error, child scope/process caps, bounded/pruned history, default-off
loop/CLI behavior and explicit opt-in/GDB refusal. A scan sentinel fails if the
collector examines more than65 directory entries. Constant/AST comparisons
preserve old helpers, ordinary collector, parent Observer and GDB behavior.

Tests run the actual candidate observe/collect path only against temporary
modeled procfs, never a live process or kernel-stack target. Loop sleep/stop is
controlled by the model; no real process is terminated or permission changed.
511 existing tests independently retain their unchanged-source scope. These
checks do not validate real Linux task teardown, seccomp/native permissions,
12s timing under load or any campaign acceptance.

The unchanged pure frozen lifecycle assessor still reproduces the retained
N1/2903 failure. It does not consume these new records or waive unavailable
stacks. Original cohort/strict decisions and all seven absent run directories
are unchanged; no retroactive requalification.

candidate-binding.json binds exact original/candidate SHAs, defaults and limits.
input-hashes.json and postflight.json record unchanged frozen source/inputs/
current14/preserved13/full SDK/ROS/provider chain/native87/old observer bundle and
all prior public/raw archives, including238 stopped-run files/927,231,952bytes,
plus the preceding diagnosis inputs. public-artifact-hashes.json binds the
complete candidate/test/log package. No later case or live calibration is queued.
