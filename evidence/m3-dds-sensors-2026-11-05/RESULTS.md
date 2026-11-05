# DDS sensor window results

All rows are sensor-only, one-seed development evidence on the emulated Linux
amd64 M3 image. Source-enabled duration includes phase-control latency. Commands
were not exercised. These are not matched-workload SRT comparison results.

| Run | Enabled seconds | Route | Actual Hz | Produced | Received | Accepted | Missing before callback | Other rejections |
| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| n0-30s | 30.131 | imu | 199.891 | 6,023 | 6,023 | 3,502 | 0 | 2,521 |
| n0-30s | 30.131 | joints | 50.014 | 1,507 | 1,507 | 876 | 0 | 631 |
| n1-smoke | 15.113 | imu | 199.964 | 3,022 | 2,079 | 2,079 | 943 | 0 |
| n1-smoke | 15.113 | joints | 50.024 | 756 | 746 | 746 | 10 | 0 |

The N0 clock monitor observed a minimum offset step of 1,281,694 ns, disqualifying
its age estimates and producing 3,152 clock rejections. The cause is not established.
N1 passed the local shared-VM age-estimate checks; this does not establish SRT
clock-bound equivalence. Sensor count success does not imply age qualification.

Received counts partition exactly into accepted, stale, invalid and clock-rejected.
Accepted histogram populations match those counts. Pre-callback loss includes
middleware, kernel, network and receiver history; it is not isolated WAN loss.

All final source hashes match; raw capture hashes/sizes are preserved separately.
Both endpoint capture checks passed, including complete tcpdump counts and zero
kernel capture drops. Fragment frames are counted separately without payload
classification. The prior SRT full-N0 summaries are unchanged (156,443 frames per
endpoint). All 19 Python tests and the installed DDS driver import/help check passed.

The earlier multicast timeout, unbracketed-clock failure, fragment-accounting
failure and full-N0 hard clock-gate failure remain under `development/`.
The final clock check brackets reads and
distinguishes gradual drift from observed offset steps. QoS discovery verifies
Best Effort/Volatile; history/depth may be unknown in endpoint discovery.

Reliable commands with durable journals, equivalent command/security/age workload,
matched-window CPU/wire measurements and the full matrix remain pending. No DDS
or SRT performance advantage or M3 acceptance is claimed.
