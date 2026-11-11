# Integrated native SDK/ROS calibration — PASS

**Readiness PASS and real SDK/ROS fixture PASS; driver exit 0.** Exactly one
invocation on freeze
`4d64d753f6ebe398a28cf447cbcc1632170facd0f3b6b0726a86c7c55aa5222a`,
base source `3047c86bb2d0e70fe905f782d072af426e5a938e`.
Quiescent runtime and frozen source/build/input/index checks passed before the
one-shot exact grant and again before fixture startup. No tuning, retries,
watchdog escalation, tests or builds. N1/2903 was not rerun; its original FAIL
and cohort 1 PASS / 1 FAIL / 7 NOT EXECUTED remain unchanged. All 38 campaign
IDs/stages stay disabled. M3 open, PR2 draft and Intrinsic M4 untouched.

## Native SDK/ROS result

| Gate | Observation |
|---|---|
| One native observer readiness self-check | PASS; exact collector/activation, filter, permissions and target-free bootstrap |
| One N0/1701/10s SDK/ROS diagnostic | PASS using unchanged pinned amd64 Linux SDK/ROS builds under emulation and independent native ARM64 observer |
| Startup/warmup/restart/launch/socket stages | Real negative type-hash startup and all three positive bridge launches validated; operator measurement and robot warmup/measurement each retain 51 shutdown records |
| SDK-provider visibility | Two qualifying observations before host shutdown release; four matching pre-signal observations in final capture; all three declared provider names present |
| Per-thread lifecycle and exec/clock binding | PASS; 100 readable task/stack records, 19 supported post-SIGINT enumeration absences, no missing-stack substitutions |
| Combined SENSOR/command/capture gates | PASS on real short-window evidence; five confirmed commands/effects, no unresolved attempts; six conservation balances all zero |
| Original N0 kernel profile and cleanup | Exact original commands/readback pass; credentials deleted and all owned endpoints, observers, readiness resources and network removed |

The observed provider names are `rwx-shard-0`, `rwx-shard-1` and `rwx-readiness`.
Parent bridge PID111/start_ticks1537; registered journal worker PID127/
start_ticks1600. Both observed with matching identities before SIGINT. Same
recorded boot and zero time-namespace offsets; exact calibrated collector
6deab3c5e83e, metadata409a8812042b and lifecycle4fafc85e3d4d. No runtime setting,
policy, helper, install or observer limit changed.

The two-sample host visibility proof ends at 38,872,545,017 ns. Final capture has
four pre-signal SDK-provider samples spanning 38,615,584,141–39,389,862,017 ns.
SIGINT: 39,482,225,892–39,482,340,725 ns. The original SDK worker-join stage ends
at 39,501,931,309 ns. A later sample while the root still matches observes the
registered worker absent after join and 19 earlier task identities omitted from
complete enumeration, including all three named provider threads. Their common
absence bracket is 39,648,475,850–39,648,541,475 ns, wholly after SIGINT completion
and before supervisor reap at 39,718,305,100 ns. Root disappearance is observed
only in the sixth sample after reap. Root exit0/unforced; signal-end-to-reap
235.964375 ms, within the unchanged five-second wait. This is diagnostic fixture
timing, not observer-overhead equivalence or a bridge latency guarantee.

## Raw counters and scope

Observer footer: six total samples, `all_owned_processes_gone`, no budget
exhaustion, 100 stack reads OK / 0 unavailable, no userspace debugger. Five samples
finish before supervisor reap, including one post-signal sample. There are 600
successful content reads and 100 present-directory checks. The 19 omitted tasks
have stack status `not_attempted`, not invented readable samples. Confirmed task
exits remain zero. The registered worker-process absence/join proof is reported
separately and does not assert its exit code or internal cause.

Real source-enabled window: 10.156861921 s; IMU 199.963337 Hz, joints 50.015448 Hz.
2,539 produced / 2,449 observed samples, with all 90 differences accounted as
5 admission losses plus 85 outbound replacements. No SRT accept-to-receiver gap
is attributed; this is not a loss-free delivery claim. Six typed-ingress/mailbox/
queue/publication/end-to-end balances are zero. Observed publication-age upper
histogram maxima are 15 ms IMU / 29 ms joint, within the original 250 ms gate.
Five attempts, five durable confirmed successes/effects, zero UNKNOWN/unresolved,
zero skipped slots and matching closed journals pass the real command gate.

This qualifies one bounded integration of the calibrated assessor with actual
SDK/ROS startup, warmup/restart, provider visibility, post-signal enumeration
absence, worker join, socket disposition and normal shutdown. It is not the
300-second N0 campaign case, broader N1/N2/N5 coverage or M3 acceptance. No task
read returned mid-read ENOENT: the exact N1/2903 missing-read race remains outside
this capture, as do unseen reuse and observer-overhead equivalence. No historical
capture or verdict is retrofitted or reclassified. Campaign cases remain disabled;
no next calibration or campaign run is queued.

Readiness and endpoint/observer isolation match the prepared policies. The SDK
workload also performs its existing target-free version inventory in an automatic
`--rm` container. The real fixture contains one operator endpoint, one robot
endpoint and one independent observer; the separate native readiness container
and its volume are removed before fixture startup. One normal observer-readiness
file-copy miss is retained; no failed driver/network command or gate, restarted
observer, repeated fixture or watchdog signal occurred. The planned warmup launch
is not a failed-case retry.

`run/` byte-copies all 114 raw files / 11,799,641 bytes, including captures,
journals, traces, catalogs, command records and assessments. The original raw
index and public index bind all bytes. `schema-summary.json` retains the complete
absence identities and timing; `gate-report.json` and `postflight.json` record
qualification, workload/accounting, integrity, cleanup and unchanged exclusions.
Preparation public index and original N1/2903 assessment SHA verify unchanged;
seven later case directories remain absent. No tests were rerun or credited during
this calibration. No further execution is authorized by this result.
