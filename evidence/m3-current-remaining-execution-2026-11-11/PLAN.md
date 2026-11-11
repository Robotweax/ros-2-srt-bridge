# Seven remaining calibrated LONG cases — 7/7 PASS

**Seven passed, zero failed, zero unexecuted; driver exit0.** Exactly one ordered
invocation on freeze
`df3cfbabfe3bf4f3a1cc77a280454bdea021501cad410c5acdb320ec94b0a65e`.
Runtime quiescence, source/full matched build/native87, frozen inputs, calibration
prerequisites and retained indexes passed preflight and each required postflight.
No tuning, retry, build, concurrent test, watchdog escalation, extra readiness/
calibration or excluded campaign case was run. N1/2903's historical FAIL and the
original cohort snapshot remain immutable. Other campaign stages stayed disabled.
M3 remains open, PR2 draft, Intrinsic M4 untouched.

## Closed strict results

| Case | Source window (s) | Confirmed commands/effects | Skipped slots | Max IMU/joint age upper bound (ms) |
|---|---:|---:|---:|---:|
|N1/4211|600.114364|300/300|0|82/85|
|N2/1701|600.137076|300/300|0|144/164|
|N2/2903|600.166043|300/300|0|145/165|
|N2/4211|600.135985|300/300|0|227/222|
|N5/1701|300.112504|125/125|25|172/183|
|N5/2903|300.147483|116/116|34|211/201|
|N5/4211|300.132933|126/126|24|178/182|

All 1,567 admitted attempts have durable matching successful outcomes and effects;
zero UNKNOWN, unresolved or not-admitted attempts. N5's 83 skipped slots are
retained, not invented as attempted commands or replayed. Maximum adjacent-intent
gaps were 6,011.849253 / 6,022.526002 / 6,013.721337 ms for the three N5 seeds.
The original gate permits skipped scheduling slots; these results do not establish
continuous two-second command cadence or a universal command-latency bound.

Each case passes all six typed-ingress/mailbox/queue/publication/end-to-end SENSOR
conservation balances at zero and the original nonempty/source-cadence/freshness
checks. The largest observed publication-age upper bound is227ms, below the
unchanged250ms gate. Known admissions/replacements/expiry losses remain itemized
in `gate-report.json`; zero accounting imbalance does not mean loss-free delivery.
Actual command/capture/journal, N5 competitor, kernel profile/readback and owned
cleanup gates passed on the declared600s/300s windows, without settings changes.

## Calibrated task observations

All cases pass exact launch-bound startup, negative type-hash, robot warmup/
restart, final bridge identity, per-launch socket/stage and normal child shutdown
gates. The native ARM64 observer watches the exact operator PID namespace of the
pinned amd64 Linux SDK/ROS workload under emulation. The original five-second child
waits, role capabilities, default-deny observer filter, sampling/read/history
budgets, dynamic neighbors and N5 competing load remain unchanged. SDK-provider
visibility qualifies before normal shutdown release in every case.

Across the cohort:712 readable kernel stacks, one explicitly unavailable stack,
121 supported task-disappearance observations and zero confirmed-task-exit claims.
Registered worker-process absence after its SDK join is separate proof. Every
positive launch exits cleanly and unforced. Operator signal-end-to-reap times
range176.528251–225.823501ms; these observations do not establish observer-overhead
equivalence or a general shutdown latency bound.

N2/2903 captures the disappearance path that the new metadata distinguishes:
previously identified DDS watchdog TID116/start129398 (`dds.shm.wdog`) is listed
in a complete enumeration, then its initial stat, wchan, syscall, stack, children,
final stat and directory-presence operations return ENOENT. The root bridge
PID111/start129366 still matches. Verified prior raw identity and final absence
support `observed_absence_after_prior_identity`; its raw stack stays unavailable,
and it never contributes readable-stack coverage or a confirmed exit claim.

That observation's read/absence bracket is1,908,692,738,703–1,908,692,801,995ns,
after SIGINT completion1,908,642,148,911ns and before supervisor reap
1,908,818,677,162ns. Enumeration ends1,908,692,352,745ns, preceding initial stat.
`observer-summary.json` retains the complete raw evidence and all per-case absence
classifications. This is observed enumeration-to-first-read absence after a prior
DDS-task identity, not proof of no unseen TID reuse, an exact exit cause, or a
reconstruction of N1/2903's missing SRT-provider metadata. The older failed
capture and verdict are not upgraded or overwritten.

## Retention and exclusions

All823 raw files /2,359,812,816bytes remain at the frozen cohort output:
`.local/current-remaining-cohort-20261110T212827698078Z`.
`local-artifact-hashes.json` binds every file. Public `cases/` contains661
byte-identical selected raw exports /41,625,410bytes, including closed journals,
launch catalogs, SDK/observer metadata, strict assessments and profile/cleanup
proofs. `export-map.json` maps each export to its original bytes and lists local-only
artifacts. Large PCAP/monotonic captures, full run.json files and larger traces
remain local and indexed. The public two-MiB selection threshold is an export
choice only; it does not change raw retention, observation budgets or any gate.
Selected source fields are explicitly labeled in each `run-summary.json`.
Full strict replay requires the indexed local raw evidence, not only the subset.

The exact grant, unmodified driver cohort report, driver postflight, public index,
per-case proofs, gate/observer summaries and independent cleanup/integrity report
are retained. All seven credentials and owned endpoint containers, observers,
networks and observer volumes are absent. No unowned object was altered. No tests
were rerun or credited during this live cohort.

The new seven-case cohort passes separately from the original snapshot, which
still says1PASS/1FAIL/7NOT_EXECUTED. Together with the earlier N1/1701 pass, there
are passing current-build results for eight distinct LONG case IDs. N1/2903's
historical strict failure remains an explicit acceptance gap. Its original
assessment/cohort hashes are unchanged, and the seven originally unexecuted directories in that old cohort remain
absent. These results use the fresh output. All31 excluded IDs stayed
excluded; no N0/N3/N4 case was rerun. There is no automatic next case, retry, new
freeze/grant, M3 acceptance, merge or Intrinsic-core work authorized by this result.
