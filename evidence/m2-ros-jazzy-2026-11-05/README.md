# M2 ROS Jazzy acceptance — 2026-11-05

Accepted for the recorded Linux amd64 simulator profile. See
[the acceptance matrix](ACCEPTANCE.md), [baseline](../../baselines/m2-acceptance.json),
[run manifest](run.json), [scenario result](operator-result.json) and
[SDK regression](sdk-regression/run.json).

The final run was `.local/m2/20261105T102439657240Z`, using
`python3 tools/run_m2.py` against the accepted image. The preceding
`--build-image` run is retained in `image-build-qualification/`; it built the image
from the pinned ROS base and passed the same scenario. The final run installed
the standalone SDK, rebuilt all three ROS packages cleanly,
ran the codec tests, and started isolated robot/operator containers. Every runtime
container used a temporary internal Docker network, separate ROS domains and
localhost-only DDS discovery. SRT used their non-loopback IP addresses. Host
network settings and unrelated Docker networks were not changed.

Results: 626 remote Imu and 350 remote JointState samples, zero direct DDS samples
and no invalid/old/duplicate payloads observed. Four distinct command frames caused
three device effects. The successful command returned a matching rate/generation;
a generation conflict failed without effect; a lost reply and a killed worker
after an effect both returned durable UNKNOWN. Restart used a new session,
queried status and did not replay either uncertain command. The bridge outage
lasted 2.0011 seconds. The longest measured clean shutdown was 0.3198 seconds;
workers were reaped. These counts and times describe this run, not a performance
or statistical reliability guarantee.

Six ROS codec cases passed (colcon counts the CTest wrapper as a seventh result).
The changed ROS-independent SDK separately passed 15 Debug, 15 ASan/UBSan, 67 native,
10 native ASan/UBSan tests, and its relocated installed consumer. ROS adapter code
was tested in Release; the sanitizer results apply to the SDK tests.

`attempts/` retains prior manifests and relevant failure logs. Development exposed
CMake link-signature issues, an unsupported image identifier form, empty-vector
CDR sizing/alignment behavior, an incremental object compiled during a header edit,
and unavailable QoS history depth in discovery. The accepted runner rebuilds ROS
packages cleanly; the codec tracks writer and reported-size cursors and zeroes its
buffer; actual local publisher/subscription QoS is checked by the node. Discovery
independently verifies Best Effort/Volatile, while local checks verify KeepLast(1).
Earlier failed attempts are not acceptance evidence. Earlier passed runs remain
as development records; this directory's top-level manifest is authoritative.

The M1 acceptance record is historical and unchanged. M2 adds an external handler
backend and publication authorization to the SDK, with private worker IPC version
3. Parent/worker must be rebuilt together. Wire version 1 is unchanged.

The simulator remains alive across bridge/worker restarts. Its bounded device
request history is in memory, not durable across a simulator restart. Local DDS
participants are trusted in this laboratory configuration. No physical device,
power-cut, WAN impairment, DDS comparison or Intrinsic qualification is claimed.
Temporary passphrases were not retained. Raw command journals remain ignored in
the local run directory. No Git commit or external publication was performed.
