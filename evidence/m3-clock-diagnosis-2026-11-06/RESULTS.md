# Final live development checks

SRT N0 30 s, default DDS N0 30 s and paced DDS N5 60 s pass their workload,
whole-capture and source-boundary gates. Paced N5 confirms 30/30 commands.
Every CPU phase qualifies. No wire windows qualify, so none are reported.
The SRT series directly demonstrates the faster calibration rejecting an offset
change accepted by sparse sampling. Legacy evaluations below are diagnostic only, excluded from
wire-cost claims. The legacy model allows 1-s gaps; dedicated calibration allows
100 ms. Both retain the same 1000-ppm drift limit.

| Run | Phase | Endpoint | CPU qualifies | Legacy process clock | Dedicated clock |
| --- | --- | --- | --- | --- | --- |
| srt-n0 | source_enabled | robot | yes | pass | reject: observed offset drift exceeds 1000ppm model |
| srt-n0 | source_enabled | operator | yes | pass | reject: observed offset drift exceeds 1000ppm model |
| srt-n0 | fenced_observation | robot | yes | pass | reject: observed offset drift exceeds 1000ppm model |
| srt-n0 | fenced_observation | operator | yes | pass | reject: observed offset drift exceeds 1000ppm model |
| dds-n0 | source_enabled | robot | yes | reject | reject: observed offset drift exceeds 1000ppm model |
| dds-n0 | source_enabled | operator | yes | reject | reject: observed offset drift exceeds 1000ppm model |
| dds-n0 | fenced_observation | robot | yes | reject | reject: observed offset drift exceeds 1000ppm model |
| dds-n0 | fenced_observation | operator | yes | reject | reject: observed offset drift exceeds 1000ppm model |
| paced-n5 | source_enabled | robot | yes | pass | reject: observed offset drift exceeds 1000ppm model |
| paced-n5 | source_enabled | operator | yes | pass | reject: observed offset drift exceeds 1000ppm model |
| paced-n5 | fenced_observation | robot | yes | pass | reject: observed offset drift exceeds 1000ppm model |
| paced-n5 | fenced_observation | operator | yes | pass | reject: observed offset drift exceeds 1000ppm model |

Raw clock intervals, computed violations and both evaluations are in `calibration-comparison.json`.
