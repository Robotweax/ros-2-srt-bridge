# M2 acceptance matrix

Scope: ROS 2 Jazzy / Fast-RTPS, Ubuntu 24.04 Linux amd64 under Docker Desktop
emulation, the exact image and package versions in `run.json` and `versions.log`.
The base SRT library remains the M0-qualified static dependency. M2 does not
replace the M1 acceptance record; `sdk-regression/` qualifies the SDK changes.

| Gate | Evidence | Result |
| --- | --- | --- |
| Installed SDK boundary | `build.log`, SDK relocated-consumer manifest | colcon builds only `ros2/`; external runtime links the exported SDK |
| Real SRT between isolated endpoints | `run.json` isolation/IPs, scenario driver | Private internal Docker network, ROS domains 41/42, localhost DDS discovery, no host port mapping |
| No DDS bypass | `robot-ready.json`, `operator-result.json` | Source active before robot bridge starts; zero direct/remote samples then, zero direct DDS samples throughout |
| Typed Imu and JointState | `operator-result.json`, `ros-codec.xml` | Headers and typed fields preserved; monotonic simulator payload markers across reconnect |
| Type identity | wrong-hash startup log, SDK manifest tests | Wrong configured ROS type hash fails startup before journal/transport; negotiated manifest must match |
| Payload bounds and preflight | Six codec cases in `ros-codec.xml` | Imu 380 bytes, six-joint worst case 684, payload cap 928; UTF-8/string/count/dimension and truncated/invalid CDR checks before peer allocation |
| Empty-vector CDR behavior | Codec alignment/padding cases | Writer offsets and reported lengths checked separately; serialization buffer initialized so unused bytes are zero |
| Local QoS | Bridge actual-QoS checks, saved states, scenario graph inspection | Best Effort, Volatile, KeepLast(1) on both sensor endpoints; discovery omits history depth, so local RMW QoS provides that assertion |
| Invalid local input | `operator-result.json` invalid-ingress counters | Oversize and inconsistent samples rejected; none reached remote typed observer |
| Publication authorization | SDK transport tests, ROS stop/restart scenario | Generation/publication epoch, session, clock/deadline and stop gates; no publication in the settled outage interval |
| Real rate change and proof | SUCCEEDED result plus simulator/remote Imu observations | Device transitions 200→100 Hz, generation 0→1; result matches original request/hash |
| Duplicate suppression | Four command frames, three effects | Repeated successful and UNKNOWN intents do not cause another COMMAND/effect |
| Generation mismatch | Generation-conflict result | FAILED/generation_conflict, no effect |
| Lost result after effect | Delayed device reply fault | Device moves to 75 Hz/generation 2; durable UNKNOWN/effect_uncertain, no valid success result |
| Crash after effect | `crashed.json`, recovery result | SIGKILL of worker after 50 Hz/generation 3 effect; bridge restart recovers UNKNOWN/context_lost and queries it |
| Two-second interruption | Outage and marker assertions | 2.0011 s bridge outage, new session after restart, no old/duplicate payload or extra effect |
| Clean lifecycle | `robot-final.json`, operator shutdown, SDK lifecycle tests | All clean exits 0, measured maximum 0.3198 s, supervised children reaped |
| SDK regression | `sdk-regression/` | 15 Debug + 15 ASan/UBSan + 67 native + 10 native ASan/UBSan; installed consumer passes |
| Reproducible commands/provenance | `run.json`, build/test/version logs, source/driver hashes | Full default and `--build-image` paths passed; every attempt retained separately |

Freshness uses explicit configured assumptions: 1000 ppm drift bound, 1 ms timing
uncertainty, at most 5 s probe age and 50 ms clock-interval width. SENSOR budget is
250 ms; command start budget is 5 s. These are pilot assumptions, not measured
host guarantees. The ROS header timestamp is preserved and is not used as the
bridge monotonic ingress timestamp.

The final boundary check authorizes a publication immediately before calling ROS.
A publication already authorized when revocation occurs may finish. ROS execution
and storage/network owners are separate; ROS callbacks do not perform SRT/SQLite
I/O. The demo's delayed device callback runs outside sensor locks/callback groups.

Open scope: M3 N0–N5 impairment/comparison, full route/connection performance
instrumentation, local DDS authentication, durable production device history,
physical hardware, actual power-cut durability and M4 Intrinsic. No WAN advantage
or physical safety conclusion follows from this local simulator run.
