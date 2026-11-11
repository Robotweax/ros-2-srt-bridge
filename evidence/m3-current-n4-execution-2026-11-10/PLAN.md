# Current-build N4 execution — stopped at first failed gate

**16 PASS / 1 FAIL / 2 NOT EXECUTED.** Driver exit1; no retry, tuning or automatic
advancement. Exactly one invocation of the unchanged prepared19-case driver on
freeze513f13066b304490c89a36a288ec4839a08ec780d8ede21269885eeb4b665b10,
source commit12ec0195404ab0edc3b8c03a5880779bf422b414. The user authorized the
ordered19-case N4 scope only. Nine other unexecuted N1/N2/N5 cases remain disabled;
ten completed N0/N3 cases are excluded. M3 open, PR2 draft, Intrinsic/M4 untouched.

## Outcome

| Cases | Strict result |
|---|---|
|13 native admission/dispatch/started/committed/query cases|13 PASS|
|3 ROS freshness directions|3 PASS|
|ROS crash before admission, ordinal27|FAIL: `ROS crash audit differs`|
|ROS crash after effect, ordinal28|NOT EXECUTED|
|ROS crash after committed result, ordinal29|NOT EXECUTED|

All13 native results retain original durable success, valid proof, one effect
and one COMMAND handoff, matching sender/receiver journals and conservative5s
command deadlines. The QUERY case has positive QUERY retrieval of the original
committed result. Each case proves the selected2s outage and original phase
barrier, then completes strict phase/outcome/shutdown, recorded cleanup and
independent owned-object absence/integrity checks before advancement. This is
controlled native handler evidence, not physical-device or ROS crash acceptance.

The three15s ROS freshness cases pass typed payload/order, restored freshness,
source cadence, trace completeness and six zero conservation balances each.

| Direction | Produced | Observed | Accounted missing | Modeled IMU/joint age upper maxima |
|---|---:|---:|---:|---|
|both|3765|2881|884|18/29ms|
|to-robot|3764|3626|138|18/29ms|
|to-operator|3764|2968|796|18/29ms|

Expected context changes and counted losses remain explicit, not lossless or
continuous availability. Age bounds are from instrumented shared-VM callback/
publication semantics, not physical sensor timestamps. These original N4
fixtures do not include the N0 independent packet capture/native stack observer
or equivalent capability/diagnostic-cost qualification.

## First failure: strict crash proof representation mismatch

The crash-before-admission inner runner returned passed and normal shutdown
succeeded. The unchanged strict assessor recomputed `check_crash` successfully
but its direct Python equality with the saved JSON proof failed. The case stays
FAIL; the other two crash cases were not started and have no output directories.

A read-only comparison of retained evidence (`failure-comparison.json`) identifies
only `/sender_trace/point_names` and `/sender_trace/reason_names` key types:
recomputed maps have integer keys, while JSON persistence turns them into string
keys. JSON-round-tripping the recomputed proof yields exact equality with the
recorded proof. This is an observed assessor representation mismatch; no gate
was changed, waived or relabelled, and no new experiment or replay was run.
Raw hashes were checked unchanged across the comparison. The original failure
and all other earlier failures remain retained.

Retained inner observations show UNKNOWN/reconcile_required (state8/reason2),
invalid success proof,0 device effects, empty receiver journal, positive NOT_FOUND
observation beyond the original deadline and one original handoff. The deliberate
SIGKILL is recorded separately from final normal shutdown. These observations
are not strict crash-case acceptance, nor does NOT_FOUND authorize nonexecution,
forced expiry or replay. No SRT protocol defect is demonstrated by this failure.

## Integrity and retained artifacts

All17 started cases have successful independent cleanup/integrity postflights;
all owned lab containers/networks are removed and credentials deleted. Final
read-only verification passes frozen source/inputs/current14/preserved13/full
SDK/ROS/provider chain/native87/new fixture37 and all retained archives, plus
the preparation public index. No rebuild, policy/queue/clock/rate/wait/filter/
trace/budget changes or test overlap with live measurement occurred.

`authorization.json` and `preflight.json` bind the exact grant/freeze. `cohort.json`
and `execution.log` retain the unchanged driver stop decision; `gate-report.json`
summarizes all19 rows without changing their status. `cases/` contains byte-exact
selected result/provenance/network/strict/postflight/phase/shutdown proofs and
failed-case logs. Complete raw output remains at
`.local/current-n4-cohort-20261110T141000377424Z`, with the host log at
`.local/current-n4-execution-20261110.log`;1018 files/28,981,196 bytes are SHA-bound
in `local-artifact-hashes.json`. Public copies are not substitutes for omitted
raw traces/journals. The public index binds all files in this execution package.

Next engineering work is an offline assessor serialization fix and regression
coverage. No fix, new freeze, retry, remaining crash run or N1/N2/N5 execution is
included here. The preparation's20+511 offline test results keep their prior
scope; no new tests are credited for this execution. M3 acceptance remains open.
