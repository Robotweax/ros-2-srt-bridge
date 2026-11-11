# ROS source loss correlated by actual SDK identity

The one-loss finite ROS case passes. The cohort stops at the second fixture's
pre-arm capture gate; no two-packet ROS fault was armed. Both original manifests
are retained, no retry ran, and full N3/M3 acceptance remains open. PR #2 stays
draft. This does not replace earlier failed baselines or establish a BUSY fix.

The plan/code was frozen in `38afa06` after 179 host tests and syntax checks. This
turn changes only the host harness and tests. Six selected runtime hashes agree
with the prior sample-trace runtime and remain unchanged before/after measurement.
The previous 70 SDK /36 ROS reported tests apply to those unchanged artifacts;
no new full SDK/ROS/M2 test run is claimed.

## One-loss case

Exactly 19 typed IMU messages at requested 20 Hz traverse the existing authenticated
SENSOR bridge profile in a disposable permanent-neighbor fixture. Closed pre-arm
handshake/binding captures establish the source origin and flow. The binding
occupies message 1/source index0. A separate measurement capture starts before
arming. There is an explicit gap between these capture phases and no continuous
coverage claim across it.

The selector drops message 8, position 3 of row 1. It is a single-packet source
identity, not an assumed ROS publication index. Source header timestamp joins
actual ROS admission to original ingress/owner/session/generations/route, then to
assigned SDK message number. In this run, message 8 maps to source ID 6 and envelope
sequence 7. All 19 source publications were admitted, so no BUSY occurred.

| Gate | Recorded result |
| --- | --- |
| Source calls / SDK-admitted samples / typed publications / observations | 19 / 19 / 19 / 19 |
| Selected SDK message / ROS source ID | 8 / 6 |
| Selected classifier drops | 1 |
| Measurement source / parity records per endpoint | 18 / 5 |
| Measurement PCAP file / captured / filter per endpoint | 23 / 23 / 23 |
| Sender trace records / drops / exhaustion | 39 / 0 / false |
| Receiver trace records / drops / exhaustion | 0 / 0 / false |
| Publication age-upper maximum | 9,398,555 ns |

The selected source packet is absent from both declared native and PCAP source
populations. All parity survives, including the parity packet sharing that
source sequence. The selected complete typed payload nevertheless reaches the
ROS observer in the correct order with its expected hash. No extra/duplicate/
retransmitted source records or replayed SDK acceptance are present in the
verified populations. This establishes recovery through this finite bridge case;
SENSOR filter-supply counters were not added or measured in this ROS fixture.

All six conservation balances are zero with no stage loss. Actual QoS and
configured clock qualification remain valid in the same session. Publication
age-upper histogram population matches 19 publications and remains below 250 ms.
These are callback-ingress-based bounds under configured assumptions, not physical
sensor age or realtime-PCAP latency. Both phases have complete native counters,
zero reserve/copy and kernel loss, strict standalone final footer equality and
stable bounded drain. Interface features match before/after.

Post-hoc closed-output timing (`one-loss-recovery-timing.json`) places the selected
SDK handoff, parity observation and typed observation inside the guaranteed filter
installation/removal interval. The source callback-ingress-to-observer elapsed
time is 2,587,625 ns on the common VM monotonic clock, separate from the conservative
publication-age upper bound. Observation occurs while the selector is still
installed, not after removal. No new run or qualification claim is added by this
analysis.

The harness also covers the independent-BUSY case in controlled host fixtures:
rejecting an earlier source callback shifts which sourceID owns SDK message8,
without consuming a SRT message number. Such losses remain in the admission term,
separate from the expected two-packet transport gap. The original strict19-source
`outcomes()` gate and prior failed cases are unchanged.

## Second fixture: failed before arming

The second fixture reaches its paused-source identity phase but fails the existing
five-second drain guard. Every fresh robot snapshot reports captured 8/filter 10,
zero kernel drops; the operator reports 8/8. The counts remain unequal through the
budget. No `armed` marker, measurement phase or loss selector is created, and no
sample is published. The intended two-loss ROS test therefore has no result.

The robot's final footer also remains 8 captured/10 filtered and fails population
reconciliation. Zero kernel drops do not pass this gate. Neither a longer wait,
retry, subtraction, altered original record nor native-based rescue is used.

A separate post-hoc fixed-IHL IPv4 header comparison finds 8 matching SENSOR
DATA/handshake prefixes in the native observer and 8 PCAP records at each endpoint,
with identical prefix+length populations. Native total observations are 155 robot /
154 operator (different scope), with complete counters and zero reserve/copy loss.
This does not identify which packets contributed to the extra filter statistic,
prove absence before native attachment, or establish a startup/root cause. The
failed capture stays failed. The exact historical two-record discrepancy is not
assigned this cause either.

Original results, prospective plan, typed hashes/metrics, trace/counter/readback/
capture logs, selected inventories, source provenance and raw hashes are retained.
Payload captures, journals and detailed resource/clock traces remain local in
`.local/m3-ros-traced-loss/`. Credentials are removed; full container inspect and
environment dumps are excluded.

Next: qualify recorder startup/filter-statistics population scope before a
separately planned two-loss ROS attempt. Deliberate late repair ordering, full
200/50 Hz IMU/joints and multiseed workload, N4 command phases and all other M3 gates
remain open. Intrinsic/M4 is untouched.
