# Shared endpoint window observations

CPU entries are observed inner–outer tick deltas and maximum sampled summed RSS,
not exact physical CPU bounds or PSS. Includes test observers. amd64 emulation;
short sequential development runs, not controlled performance comparisons.

| Run | Window | Seconds | CPU seconds / sampled summed RSS | Wire mapping |
| --- | --- | ---: | --- | --- |
| srt-n0 | source_enabled | 30.142 | robot: 18.34–18.59 s / 282.4 MiB; operator: 13.23–13.38 s / 186.7 MiB | rejected |
| srt-n0 | fenced_observation | 33.005 | robot: 19.11–19.31 s / 282.6 MiB; operator: 13.64–13.70 s / 186.7 MiB | rejected |
| dds-n0 | source_enabled | 30.121 | robot: 5.86–5.98 s / 219.9 MiB; operator: 6.14–6.27 s / 162.0 MiB | rejected |
| dds-n0 | fenced_observation | 33.151 | robot: 6.40–6.50 s / 219.9 MiB; operator: 6.37–6.45 s / 162.0 MiB | rejected |
| paced-n0 | source_enabled | 30.151 | robot: 6.31–6.41 s / 213.9 MiB; operator: 2.86–2.91 s / 163.2 MiB | rejected |
| paced-n0 | fenced_observation | 33.132 | robot: 6.65–6.72 s / 213.9 MiB; operator: 3.03–3.08 s / 163.2 MiB | rejected |
| paced-n5 | source_enabled | 60.097 | robot: 9.42–9.48 s / 216.0 MiB; operator: 5.26–5.31 s / 162.2 MiB | rejected |
| paced-n5 | fenced_observation | 63.155 | robot: 9.74–9.82 s / 216.0 MiB; operator: 5.39–5.44 s / 162.2 MiB | rejected |
| sensor-n0 | source_enabled | 15.140 | robot: 1.96–2.02 s / 152.9 MiB; operator: 2.31–2.36 s / 101.4 MiB | rejected |
| sensor-n0 | fenced_observation | 17.513 | robot: 2.16–2.22 s / 152.9 MiB; operator: 2.39–2.42 s / 101.4 MiB | rejected |
