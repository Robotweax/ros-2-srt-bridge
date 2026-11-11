# Combined DDS workload results

All primary runs match the current source inventory. Smokes are 15-second,
single-seed development runs. N5 failed startup and has no measurement window.
A count/audit pass is separate from command completion and age qualification.

| Run | Source-enabled s | IMU / joint actual Hz | Produced / received | Confirmed / attempted | Non-admitted | Unresolved | Effects | Age estimate checks |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| n0-full | 300.127 | 199.978 / 50.002 | 75,026 / 75,025 | 150/150 | 0 | 0 | 150 | False |
| n1-smoke | 15.112 | 199.971 / 50.026 | 3,778 / 2,864 | 7/8 | 1 | 0 | 7 | True |
| n2-smoke | 15.131 | 199.990 / 50.030 | 3,783 / 1,752 | 1/2 | 0 | 1 | 1 | True |
| n4-smoke | 15.100 | 199.936 / 50.001 | 3,774 / 3,204 | 4/5 | 0 | 1 | 4 | True |
| n5-startup-failure | — | — | — | — | — | — | — | no window |

N0 confirms all 150 distinct intents with 150 device effects and zero SDK inbox
drops at both endpoints. Both closed journals pass quick_check and contain the
same 150 payload hashes, SUCCEEDED entries at revision 3, rate 200 and generations
1–150. One IMU sample is missing before the observer callback; joints have no
pre-callback gap. This boundary is not isolated WAN loss.

The final N0 age estimates are unqualified: 54,313 IMU and 13,580 joint callbacks are clock-rejected after an observed offset step. These are received callbacks, not missing network samples. Only 5,705/1,427 pass the estimate gate. The earlier post-fix run passed its local age checks; it is retained as historical development, not substituted for this final run.

N1 records one explicit non-admitted intent. N2 skipped six slots while its
second intent remained pending; N4 skipped three while its fifth remained pending.
N2 and N4 retain one unresolved
intent each; no further work is issued while an intent remains pending. N5
times out waiting for a qualified command sender under the configured cold-start
congestion profile. Its failed manifest and traceback are retained; no zero-latency
or zero-loss values are invented for the absent window. These are open gates.

Twenty-seven Python tests and nineteen actual ROS GTests passed (22 including
wrappers). Sensor-only and duplicate/conflict/lost-reply/SIGKILL command regressions
passed. Full-duration command completion is demonstrated for N0 only. The N0
run overlapped development smokes/regressions in the VM; no controlled CPU or
hardware comparison is claimed. CPU/wire windows remain unmatched.

The earlier long N0 produced only two confirmed commands and one unresolved
intent, with callback drops: ordinary try-lock contention could discard a
received Reliable frame. Incoming frames now serialize short validation/copy
critical sections; only a genuinely full 64-slot inbox causes a counted drop.
Local service admission retains try-lock/BUSY. A concurrent-producer regression
checks that all 64 received tasks fit without contention losses. No queue, lease,
clock, deadline or no-replay gate was relaxed.

A valid four-byte final IP fragment exposed an old capture-header assumption.
The parser now requires UDP headers only where present and validates fragment
length/alignment. Reanalysis preserves raw records and original manifests; the
prior SRT N0 summaries remain identical. Failed/intermediate runs are retained
under development. M3 remains incomplete; no performance advantage is claimed.
