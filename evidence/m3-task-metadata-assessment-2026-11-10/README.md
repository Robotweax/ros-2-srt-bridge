# Offline per-thread metadata assessment candidate

**42 new regressions, 28 collector regressions, 23 calibration-preparation tests
and 511 existing tests PASS.** This package adds offline rules for the calibrated
schema1 collector and a prospective lifecycle adapter. It does not replace any
frozen assessor, change any campaign driver, create a freeze/grant, or execute a
case. No tuning, retries, builds, Docker calls or live procfs collection occurred.
N1/2903 remains FAIL; the stopped cohort remains 1 PASS / 1 FAIL / 7 NOT EXECUTED.
All 38 campaign IDs remain disabled, M3 open, PR2 draft and Intrinsic M4 untouched.

## Rules

`task_assessment.assess_metadata(rows, expected_root=None)` checks the capture
structure and reconstructs each observation from its raw results. It privately
loads the exact SHA-bound calibrated collector's pure stat/lifetime parsers,
without invoking collection or trusting a generic cached `shutdown_observer`.
Use the surrounding launch/boot/policy attestation for capture provenance; this
parser alone cannot attest capture origin or establish campaign acceptance.

| Observation | Required evidence | Meaning |
|---|---|---|
| Readable task | Matching parent, valid matching initial/final task identity, present directory, all reads readable and untruncated | Counts as a readable task; only nonempty stack text contributes stack coverage |
| Disappearance after identified read | Initial task identity, later ENOENT suffix through final stat, directory ENOENT, matching parent | Bounded observed disappearance; raw stack success/error retained |
| Absence after prior identity | All current task reads and directory ENOENT, exact prior-sample identity rebuilt from earlier raw records | Observed absence after that prior observation, without a current incarnation claim |
| Not enumerated after prior identity | Complete bounded enumeration omits a previously observed task; hint exactly matches the reconstructed prior cache | Observed enumeration absence, without claiming an individual task exit |

Reads, final stat and directory checks must be ordered inside the sample and
between enumeration and final matching parent check. Selected task read brackets
must not overlap. Every known process remains represented; duplicate processes,
observed PID/TID reuse, forged/stale/dropped hints, clock-origin differences,
truncated scans/reads, permission/I/O errors, unsupported schema, incomplete
footer, inconsistent raw counters and budget exhaustion fail closed. Once a
read returns ENOENT, later readable files within that observation are ambiguous
and rejected. A missing first identity without a verified preceding observation
is also rejected. History remains one preceding sample, at most 8 processes,
64 tasks each / 512 identities, and 48 samples / 16 KiB reads; no new grace period
or transport/runtime parameter is introduced.

Absence never increments readable-stack coverage or confirmed-task exits, and
raw missing-stack counters remain visible. Matching start ticks do not rule out
unobserved reuse between observations, including reuse within clock-tick
resolution; no exact exit cause/time, join, or no-reuse claim is made.

The separate `lifecycle.coverage` candidate retains the old process identity,
registered journal-worker identity and join, root/supervisor-reap, minimum
nonempty stack and forced-kill post-signal coverage gates. It permits supported
*task observations* only when their entire absence bracket lies after SIGINT
completion and before supervisor reap. Missing worker processes still require
registered identity plus the original join evidence. Tasks and worker processes
have separate proof fields. No task absence substitutes for a real stack,
including the forced-kill post-signal requirement. This adapter is not wired
into a runnable campaign or granted acceptance authority.

## Retained evidence and limits

`verification.json` records filesystem-only checks of frozen source, the full
matched build chain/native87 inputs, prior public/raw archives, and calibration
preparation/execution indexes. The retained calibration's 77 raw files / 600,527
bytes are unchanged. Its capture parses as 3 samples, 5 readable task records,
5 raw stack successes, 0 raw stack failures, 1 complete-enumeration absence and
0 confirmed task exits. The absence was **before SIGINT**: it calibrates native
metadata consistency, not the prospective post-signal lifecycle exception.
There is no native exact mid-read race, reuse, SDK/ROS shutdown coverage or
observer-overhead qualification here. Those limits remain open.

The original N1/2903 capture has no schema1 records. The candidate refuses it;
the original frozen assessor still reproduces `live target kernel stack
unavailable`. No metadata is synthesized into that capture, and no historical
failure is reclassified. Seven later case directories remain absent.

Tests use retained JSON and temporary procfs files, with deterministic mutations
during reads. They cover observed disappearance at several read boundaries,
prior-cache expiration, identity ambiguity/reuse, denied/truncated/partial reads,
clock and population failures, import collisions, immutable legacy refusal,
post-signal eligibility, worker registration/join and forced-kill gates. Initial
model failures are retained in validation logs: empty SDK stage lists, an aliasing
mutation in the forged-hint test, and a worker fixture with the wrong parent PID.
These were offline test-model errors, corrected before the final passing runs.

Reproduce offline:

```sh
python3 -m unittest discover -s evidence/m3-task-metadata-assessment-2026-11-10/validation -p 'test_*.py' -v
python3 evidence/m3-task-metadata-assessment-2026-11-10/verify.py
```

Next work requires separately scoped preparation to bind any reviewed candidate
to a prospective freeze and validate its remaining native limitations. Nothing
in this package authorizes a live run, N1/2903 retry, later case or campaign stage.
