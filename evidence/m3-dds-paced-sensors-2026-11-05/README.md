# Explicit paced DDS sensor experiment

`--dds-profile paced-sensors` tests simultaneous N5 startup with streaming
telemetry, without changing the system default or holding source publication.
It preserves the original 200/50 Hz producer, sensor Best Effort/Volatile/
KeepLast(1), Reliable/Volatile/KeepLast(64) controls, command protocol v2 and all
session, freshness, deadline, journal/start, no-replay and cutoff/drain gates.

The profile combines the previously tested UDPv4 + SHM 1200-byte packetization
with an asynchronous flow controller selected only by `/robot/imu` and
`/robot/joint_states`. The two simulator writers share 1600 controller bytes per
50 ms within their participant (32,000 bytes/s). This is not an Ethernet-rate
limit, global multi-producer cap or network priority reservation. Other publishers
use the default synchronous/default-controller configuration; no discovery
priority override is configured. The 512-kbit/s shared endpoint shaping,
16-packet netem queues and offered 128-kbit/s competitor remain active from
before application startup. No separate discovery network/server is introduced.

Fast DDS documents per-writer asynchronous flow-controller configuration in its
[2.14 data-rate guide](https://fast-dds.docs.eprosima.com/en/2.14.x/fastdds/use_cases/large_data/large_data.html).
The [Jazzy RMW configuration contract](https://github.com/ros2/rmw_fastrtps/blob/jazzy/README.md)
requires opting into XML for publish-mode/memory-policy settings, while explicit
ROS endpoint QoS remains authoritative. This experiment sets that opt-in and
explicitly retains PREALLOCATED_WITH_REALLOC and DataSharing OFF for default
publishers/readers and both sensor publishers. SHM transport remains enabled.

The standalone native probe uses the pinned provider's public RMW/native handles
to inspect the participant controller and actual sensor/control writer settings.
It verifies both topic names, the budget/period, publication modes, controller
names, reliability/durability/history, memory policy and data sharing. It fails
before lab creation if settings are ignored. A negative run without XML opt-in
fails publisher creation; the positive native check passes. The probe runs in a
separate `--network none` container, creates no measured peers or data, and cannot
warm the measured discovery network. It is never linked into bridge/simulator.

After the existing pinned M3 SDK/ROS setup, the normal runner builds the bridge
and the standalone probe and runs the preflight:

```sh
python3 tools/run_m3_dds.py --commands --profile N5 --dds-profile paced-sensors --smoke
```

For recorded development reuse, `--skip-build` requires the existing probe binary;
preflight still runs every time. The same option is available for the N0 command
fault acceptance:

```sh
python3 tools/run_m3_dds_commands.py --dds-profile paced-sensors --skip-build
```

The N5 runner now also requires the competitor process to remain alive during
scenario polling and validates its final UDP configuration and actual whole-run
client offered rate. Controlled cleanup interruption is accepted; missing load,
wrong settings and other errors fail the run. This is not a per-window delivery
or packet-loss measurement. The unchanged source fences freeze publish calls;
async queues can drain afterward. Existing quiescence and source-sequence boundary
checks remain enforced rather than treating the fence as a physical wire flush.

See [results](RESULTS.md): the full five-minute paced N5 confirms 150/150 commands
and 150 effects, and all three smoke seeds confirm 8/8. System and UDP-1200 still
fail cold readiness. The producer stays at 200/50 Hz, but only 19,128 of 75,025
samples reach callbacks in the long run. Fewer delivered updates are the material
tradeoff. Missing before callback includes middleware pacing/replacement as well
as other stages; it is not isolated WAN loss. Received callbacks pass the local
shared-VM age checks. This does not establish SRT clock-bound equivalence.

35 Python tests, positive/negative native checks, the build/preflight recipe,
paced-profile N0 fault acceptance, both N0 combined regressions and sensor-only
paced regression pass. Production compiled sources/binaries are unchanged since
02d40e6; the 32 ROS GTests/full M2 from that step are retained historical results,
not reported as rerun here. Ten final inventories and installed Python bytes match.
The first smoke before competitor validation is preserved as development.
Raw PCAPs/journals remain local; hashes/sizes and native probe provenance are kept.

This remains an explicit DDS baseline candidate. Defaults, SDK/SRT, wire v1,
worker IPC v3 and Intrinsic/M4 are unchanged. Default N5 discovery, cross-session
uncertainty, full matrices, DDS emission-stage accounting, security/age equivalence,
command-phase barriers and matched CPU/wire/SRT pacing/reconciliation costs remain
open. No lossless-delivery, controlled hardware/CPU or performance-superiority
claim is made; runs overlap fixtures in an emulated amd64 VM.
