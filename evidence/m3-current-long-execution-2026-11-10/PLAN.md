# Nine-case N1/N2/N5 execution — first-failure stop

**1 PASS /1 FAIL /7 NOT EXECUTED.** Driver exit1 after one invocation of the
unchanged dispatcher on freeze868a21578a61a3d5e67d047fa76c95c24ea70c1965c5b71d6f9f5902d292d12e,
source71fd47c1f3cc529369dba459b1ea2cb73cde673c. No tuning, build, test overlap,
automatic retry or later-stage dispatch. The exact user authorization preserves
first-failure stopping and all29 completed N0/N3/N4 exclusions. M3 open/PR2 draft,
Intrinsic/M4 untouched; all historical failures remain unchanged.

| Case | Strict result |
|---|---|
|N1/1701,600s|PASS|
|N1/2903,600s|FAIL: live target kernel stack unavailable|
|N1/4211,600s|NOT EXECUTED|
|N2/1701,2903,4211,600s each|NOT EXECUTED, all3|
|N5/1701,2903,4211,300s each|NOT EXECUTED, all3|

## Passed case: N1 seed1701

All original measurement/capture/frame/clock/cadence/age/accounting/journal/
progress/lifecycle/observer/cleanup and closed kernel profile gates pass.
300 attempts/300 confirmed successes/300 simulator effects, zero unresolved,
not-admitted or skipped slots, one original SDK handoff each and matching durable
sender/receiver results. Original5s deadlines and conservative receiver mapping
remain required; no replay or forced expiry.

600.108476067s source window,150,027 produced/110,725 observed,39,302 missing
samples explicitly accounted, six zero balances. Source cadence199.998841520Hz
IMU/50.000960154Hzjoints. Modeled publication upper-age histogram maxima156/165ms
meet250ms; publication population110,857 differs from observer population.
No lossless availability, physical sensor timestamps or hard memory peak claim.
Native observer completes with76 kernel stack readsOK/0unavailable, no budget
exhaustion. Original5s child waits and all launch/identity/stage/socket proofs pass.

## First failed gate: N1 seed2903 observer stack coverage

The inner600s workload returned passed. Strict assessment validated launch records
but failed in lifecycle.coverage at `live target kernel stack unavailable`.
It did not reach the later strict combined measurement/progress/profile gates;
inner observations are not promoted to strict acceptance.

The independent native observer completed5 bounded samples,88 kernel stack reads
OK and3 unavailable, with no budget exhaustion. In sample row4, operator PID111
still has matching process identity, but task stack reads for TIDs128/129/130
return FileNotFoundError/errno2 (ENOENT). The sample bracket
1262083806197–1262085394281ns follows SIGINT end1262055193239ns and precedes
supervisor reap1262292549697ns. The operator child exits0/unforced in roughly
237ms. Normal child shutdown does not replace missing observer evidence.

These facts distinguish missing per-thread procfs files from a blanket permission
denial. They are compatible with thread exit during shutdown, but no confirmed
thread-exit identity/lifecycle proof is supplied here and the root cause remains
unresolved. No assessor/filter/budget change, waiver, new experiment or retry.
The stopped case remains FAIL; this observation demonstrates no SRT protocol defect.
`cases/N1-combined-2903/observer-summary.json` preserves exact failing reads,
process identity checks and the supervised child bracket, with the complete
raw observer JSONL copied beside it.

The inner report observes300 terminal state4/reason0 command outcomes, no
unresolved/not-admitted attempts;150,032 produced/110,908 observed,39,124 accounted
missing samples, six zero balances and modeled upper-age maxima126/104ms. These
are retained workload observations only: strict combined revalidation was not
reached and no current-build N1/2903 acceptance is credited. No unique transport,
clock or original historical hang cause is inferred.

## Stop, cleanup and integrity

Both started cases have passed independent cleanup/integrity postflights, with
owned lab containers/networks/observer containers/output volumes absent and case
credentials deleted. Final read-only source/input/current14/preserved13/full
SDK/ROS/provider chain/native87/observer bundle/identity/lifecycle/retained-archive
verification and preparation public index pass. The seven later case directories
do not exist; no completed N0/N3/N4 rerun or later stage was started.

`authorization.json`, `preflight.json`, unchanged driver `execution.log` and
`cohort.json` retain the exact grant and stop decision. `gate-report.json` separates
strict status from inner observations; `postflight.json` records independent
integrity/absence checks. `cases/` includes byte-exact strict, phase/launch/
readiness/identity/shutdown/observer/capture-footer/kernel-readback/operator-result
proofs. `run-summary.json` contains selected unchanged fields and a raw-run hash,
explicitly listing omitted top-level fields; it is not an exact copy of run.json.

Complete raw output remains at
`.local/current-long-cohort-20261110T152312809927Z`, host log at
`.local/current-long-execution-20261110.log`;238 files/927,231,952bytes are SHA-bound
in local-artifact-hashes.json. Large raw PCAP/monotonic captures/endpoint samples/
full run.json and journals remain local/hash-bound; selected public copies are
not substitutes. public-artifact-hashes.json binds this execution package.
No new tests are credited; the preparation21/39/4/511 test results keep their
recorded offline scope.

Next work is retained-evidence diagnosis of missing per-thread stack reads and
lifecycle evidence. No fix, new freeze/grant, retry or later case is included.
Current-build N0, fresh N3 and bounded N4 passes remain intact; N1/1701 now passes,
N1/2903 remains failed, seven cases stay disabled. M3 acceptance remains open.
