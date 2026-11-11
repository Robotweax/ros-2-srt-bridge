# Native post-SIGINT per-thread calibration — PASS

**Readiness PASS and controlled post-SIGINT fixture PASS; driver exit 0.** One
invocation on freeze
`8acc653d87ad0da691cd992b059e566d0a3c2550d93efe310202a283f7fa245e`,
base source `cf603b9f6451bd80da0148e8f491309d68ad20db`. Runtime quiescence and
frozen inputs were verified before creating the exact one-shot grant. No tuning,
retries, tests/build overlap, N1/2903 rerun or campaign case. Its original failure
and cohort 1 PASS / 1 FAIL / 7 NOT EXECUTED are unchanged. All 38 campaign IDs
remain disabled. M3 open, PR2 draft and Intrinsic M4 untouched.

## Observed sequence

| Gate | Result |
|---|---|
| One native readiness self-check | PASS; exact collector/activation, interpreter and role policy, no target in this stage |
| Pre-signal worker visibility | Two readable, matching worker observations |
| Signal and wait witness | SIGINT completion recorded before supervisor wait-entry witness; child separately records handler observation |
| Post-signal worker visibility | Two readable, matching worker observations wholly after both signal witnesses |
| Controlled release/join/absence | Worker released and joined; subsequent complete enumeration omits that prior identity while matching parent remains alive |
| Normal exit and final assessment | Exit acknowledged only after absence; child exit 0/unforced within original five-second wait; exact candidate metadata and lifecycle gates PASS |
| Cleanup and integrity | Three containers and two volumes removed; frozen source/build/input/retained-evidence checks PASS |

The native ARM64 observer watched the controlled Python target on the pinned
amd64 image in that target's exact owned PID namespace. Parent PID7/start_ticks769,
worker TID8/start_ticks785. Same recorded boot and zero time-namespace offsets.
Collector SHA `6deab3c5e83e48b7c33dbbb4613c361469d9b62aa1bea86db0c1a8012cfae72e`;
exact metadata candidate SHA
`409a8812042b496354e28e7b0d940c81d9624f833d3bb1fb49ecbbd850b7c6ae` and
lifecycle SHA `4fafc85e3d4d8626b5e85db88ac8c704e5ff3c226570232febb8268446cf2068`.
No candidate, native bundle, permission, filter, budget or runtime setting changed.

Monotonic timestamps from the shared recorded clock:

- Pre-signal worker samples span 8,260,212,753–8,511,473,462 ns.
- SIGINT bracket: 8,632,200,837–8,632,290,170 ns.
- Supervisor wait entry: 8,632,295,462 ns; handler observation: 8,632,702,878 ns.
- Two post-signal live samples span 8,763,077,170–9,017,513,712 ns.
- Worker release: 9,105,082,587 ns; return: 9,105,331,879 ns;
  controlled join: 9,106,451,629 ns.
- Complete-enumeration absence bracket: 9,269,246,545–9,269,270,045 ns,
  matching the reconstructed prior worker identity; raw stack status for that
  omitted task is `not_attempted`, not a substituted readable stack.
- Absence acknowledgement: 9,324,531,629 ns; fixture exit stage: 9,324,679,212 ns;
  supervisor reap: 9,379,624,670 ns. SIGINT completion to reap: 747.334500 ms,
  below the original five-second bound; this is fixture timing, not bridge latency.

## Capture and limits

Footer: five samples, nine raw kernel stack reads OK, zero unavailable,
`parent_stop`, no exhaustion, no userspace debugger. Nine sampled task records
have 54 successful content reads and nine present-directory checks. The exact
candidate reconstructs nine readable task records and one observed disappearance;
lifecycle proof has three post-signal samples, zero confirmed task exits and no
worker-process exit claim. Absence remains separate from readable-stack coverage.
The fixture's worker join is controlled ground truth, not SDK journal-worker
process/join evidence or an exact per-task exit-cause claim.

This calibrates the native post-SIGINT **complete-enumeration absence** path and
candidate lifecycle handling for one controlled fixture. It did not produce a
missing-stack read between enumeration and first stat, force task reuse, qualify
unseen reuse away, exercise SDK/ROS/SRT workload or qualify observer overhead.
Those limits remain explicit. No historical N1/2903 reclassification, campaign
integration or M3 acceptance follows. The earlier preparation's unrelated CI
container was absent at execution preflight; no unrelated object was stopped.

One readiness check plus one fixture created three containers/two volumes once,
then removed them. Native observer remained SYS_ADMIN-only/NNP/default-deny
seccomp/read-only/network-none/exact owned PID namespace; target/supervisor cap0/
NNP/default-seccomp/read-only/network-none. Unchanged observer 48 samples/.25s/
12s/8 processes/64 tasks/16 KiB/512-history limits and original child five-second
wait. Five ordinary predeclared readiness file-copy misses are retained in the
command log; no gate failed and no stage, target or stack attempt was retried.

`run/` byte-copies all 89 raw files / 779,775 bytes. `local-artifact-hashes.json`
indexes original raw paths; the public index binds the complete export and
reports. `gate-report.json`, `schema-summary.json` and `postflight.json` record
results, timelines, raw populations and independent owned-object absence checks.
Preparation public index, exact grant and original failed N1 assessment hashes
verify unchanged; seven later case directories remain absent. No tests were
rerun or credited during this live calibration. No further execution is queued.
