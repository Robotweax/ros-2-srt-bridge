# Aligned sample-window results

All three final runs fence source publishing, exclude warmup SAMPLE/FEC history
using a fresh session, and have stable empty-pipeline checkpoints with unchanged
owner epochs. All six conservation residuals are zero. N4/N5 are short one-seed
development runs; only N0 has the full five-minute duration. Rates use actual
publication deltas and resume/pause timestamps from the same simulator clock.

| Run | Source-enabled s | Actual IMU / joint Hz | Produced | Observer received | Missing | Confirmed / attempted commands | Unresolved |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| n0-full | 300.097 | 199.959 / 49.997 | 75,011 | 72,372 | 2,639 | 150/150 | 0 |
| n5-smoke | 15.128 | 199.964 / 50.041 | 3,782 | 1,117 | 2,665 | 2/3 | 1 |
| n4-smoke | 15.122 | 199.971 / 50.059 | 3,781 | 3,072 | 709 | 7/7 | 0 |

N0's missing samples comprise **2,542 outbound pacing replacements, 91 admission
failures, three local DDS ingress losses, one ingress replacement, one receive
replacement and one observer DDS loss**. There is zero gap from SRT send acceptance
to decoded receiver SAMPLE. This does not prove zero physical packet loss: FEC
and library behavior sit inside that boundary. The complete ledger is in each
`run.json` under `measurement_window`.

Window-only IMU age-upper p50/p95/p99/max buckets are 9/11/12/56 ms; joints
17/26/27/60 ms. Buckets round up to 1 ms. Histogram populations equal window
publications (57,538 IMU and 14,835 joints); one publication was not observed over
local DDS. Startup and diagnostic tails are excluded. Exact nanosecond lifetime
maxima are not window maxima. All 150 N0 commands were confirmed with 150 effects.

The older 1.38% marker-span IMU gap figure used an approximately 178–180 Hz source
and different population boundaries; it is not directly comparable. The earlier
30-second development pair at that lower rate isolates poll quantization: 304
outbound replacements before deadline-aware waits became zero after them, with
six admission failures. Correcting source phase increases offered load to 200/50
Hz. Jitter at the strict pacing boundary still causes latest-only replacements.
No rate gate, age budget, queue bound or crypto requirement was relaxed.

N5 has two confirmed commands/two effects and one explicitly unresolved command;
new intents pause after UNKNOWN. A balanced sample ledger is not command success.
N4 confirms seven commands/seven effects; its outage is mid-window, not a command
admission/dispatch/result-commit barrier. N5 classifies 2,089 samples in the SRT-
acceptance-to-receiver gap and 234 receiver rejections, plus 211 ingress flushes,
121 outbound replacements, five admission and five input rejections. N4 classifies
584 at that SRT boundary, 122 outbound replacements, two admission and one DDS
ingress loss. These gaps are not labeled as physical WAN packet loss.

Command results have a bounded eight-second post-cutoff drain; command rows mark
`observed_after_data_cutoff`. Summary latency pools results observed during load
and drain and includes status polling (up to 200 ms). It is not solely in-load
latency. Unresolved commands are counted separately and excluded from percentiles.

CPU and capture bytes retain whole-observation/capture scope, including quiescent
phases. N0 average source/sink CPU observations are 24.66%/12.33% of one VM core;
part of this run overlapped an M2 regression in the same VM. This is not controlled
CPU benchmarking. RSS sums can double-count shared pages and startup/exit CPU
tails are unobserved. Matched-window CPU/wire measurements and DDS comparison
remain open; no M3 performance advantage or acceptance is claimed.
