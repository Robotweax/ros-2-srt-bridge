# Observer on/off study and longer paced N5 runs — 2026-11-06

This follow-up adds read-only cgroup accounting and a preregistered, sequential
study. It develops measurement scope and repetition, not isolated observer cost,
controlled hardware performance, transport parity or complete M3 acceptance.
Production C++/SDK/SRT/wire/IPC and Intrinsic/M4 remain unchanged.

## Accounting

The existing nominal 250-ms endpoint sampler now also reads its namespace-root
cgroup v2 CPU, memory and memory-event counters. It checks v2/domain membership,
that its PID belongs to the sampled root, stable namespace/device/inode identity
and unchanged limit strings. Missing counters, read errors, identity/limit changes,
regressions or excessive gaps make cgroup windows unqualified independently of
workload success, endpoint-process CPU and clock qualification.

`container_cgroup` is reported for both existing phases. Observed inner/outer
CPU deltas use the full read brackets without interpolation, with microsecond
counter units; these are not strict physical CPU bounds or confidence intervals.
CPU now includes capture, test observer and competitor processes in that cgroup.
Work accounted outside the cgroup remains excluded. The existing endpoint-process
CPU totals retain their narrower scope. Both on/off modes perform the same new
cgroup sampling, so this study does not measure the sampler's own incremental cost.

The [kernel cgroup v2 documentation](https://docs.kernel.org/admin-guide/cgroup-v2.html)
defines the CPU microsecond counters and charged memory bytes for the hierarchy.
Sampled `memory.current` includes charged cache/kernel memory and is not RSS/PSS
or a hard peak. Memory events and CPU throttling counters are retained; zero local
throttling does not establish that ancestors or VM scheduling were unconstrained.
No limits, memberships, host settings or unrelated workloads are changed.

## Preregistered design

`tools/m3_observer_study.py` writes `plan.json` before starting any child workload.
It freezes all source hashes, runs fresh containers sequentially, saves every
child manifest/log, and stops on failure or a source/configuration mismatch.
No retries, opportunistic seeds or host tuning are applied. It uses existing
installed M3 binaries as explicitly recorded development reuse.

- SRT N0: off/on/on/off, four 45-second runs, seed 1701.
- Default DDS N0: on/off/off/on, four 45-second runs, seed 1701.
- Paced DDS N5 with monotonic capture: 300 seconds each, seeds 1701/2903/4211.

Every workload offers absolute 200-Hz command intents every two seconds while
producing 200-Hz IMU and 50-Hz joint samples. Existing source fences, result drain,
leases, freshness, journal/start and no-replay gates remain unchanged. On/off pairs
compare the source-enabled cgroup phase only; command outcomes/effects and sensor
populations remain separate. Both modes retain the old tcpdump observer. The
optional BPF capability, native observer and its host effects are part of "on".
N5 also retains its shared shaping/queue and live UDP competitor gates. N5 has no
configured stochastic loss/jitter; different seeds here label fresh repetitions
and do not supply random impairment diversity.

The analyzer rejects incomplete blocks, mismatched images/durations/profiles/
seeds, cgroup limits and unqualified counters. It retains negative differences
rather than clipping them or claiming free observer cost. Command count/effect
mismatches are flagged. On/off differences remain descriptive: two pairs per
transport in a shared emulated VM cannot isolate causation or establish equivalence.

See [results](RESULTS.md), `study.json` and `plan.json` for outcomes and scope.
Projected cgroup samples retain the exact brackets and counter payloads used for
reanalysis; original full sampler/clock files, packet prefixes, PCAPs and journals
stay local with hashes. Historical evidence is not rewritten. Read-only closed-
journal audits check SQLite integrity, matching command/hash/result fields and
result generations; they do not add crash/durability fault testing.

## Validation

68 host Python tests and the demo package install pass. All 11 preregistered
runs pass, with 44 qualified cgroup windows exactly reproduced from projections.
All 44 narrower endpoint-process CPU windows also qualify. Seven opt-in runs
supply 28 qualified monotonic endpoint/phase windows without recorder loss.
The 22 closed journals agree on 634 successful revision-3 records per side;
450 commands/effects belong to the three five-minute paced N5 repetitions.
Local cgroup throttling and memory-event deltas are zero, without proving that
host/ancestor scheduling was unconstrained.

All eleven source inventories match 156 files and the installed Python scripts
match. The 56 compiled production source files and command/simulator/native-
capture binaries remain unchanged. No new ROS GTest/full M2 execution is claimed.
The initial cgroup smoke is development-only, before preregistered source freeze.

## Reproduction

After the existing M3 SDK/ROS/native builds, choose a fresh output directory:

```sh
python3 tools/m3_observer_study.py --out .local/m3-observer-study/new-run
```

Defaults are the design above. `--seconds` controls the 15..120-second on/off
runs and `--long-seconds` the 300..7200-second N5 runs; `--plan-only` writes the
frozen plan without executing it. Existing output directories are never reused.
Long durations/seeds for other profiles, observation-stage/offload qualification,
controlled hardware resources and SRT/DDS semantic/age/crypto alignment remain
separate gates.
