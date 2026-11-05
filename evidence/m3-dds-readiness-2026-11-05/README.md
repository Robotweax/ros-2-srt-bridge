# DDS readiness and lifecycle follow-up

This is development evidence for the common-VM M3 DDS baseline. It does not
qualify M3 or demonstrate a transport performance advantage. Previous evidence
folders retain their original outcomes; this follow-up changes the DDS prototype.

The HELLO inspection anchors the recorded namespace digest and extracts fields
from the prior unencrypted fixed DDS frame layout; it is not a general RTPS decoder.

Lease expiry previously rotated each local link while retaining the old directed
HELLO target. A packet-level inspection of the prior N2 capture found both peers
still targeting retired links. Discovery now uses an empty target after local
expiry until a fresh peer HELLO arrives. That discovery frame cannot acknowledge
a session or authorize execution. Mutual current-nonce acknowledgement, retired
peer protection, the 1.5-second lease and packet freshness gates remain required.

HELLOs now use separate Best Effort/Volatile/KeepLast(1) topics with a dedicated
100-ms liveness thread. COMMAND/QUERY/STATUS/ERROR retain Reliable/Volatile/
KeepLast(64). Per-channel monotone cursors reject replay without allowing a newer
HELLO to suppress an older valid control. Actual local QoS is checked at startup.
The SDK CommandJournal, SRT implementation, wire v1 and private IPC v3 are unchanged.
Both DDS peers require rebuilding for the new owner_ready field. Readiness now
requires the journal and receiver's local ROS handler to be eligible, advertised
in HELLO and rechecked locally before a start claim. This is not authentication.

New diagnostics expose matched endpoints, HELLO counts, rejects, lease expirations,
peer/target epochs, eligibility and QoS verification. N5 simultaneous startup can
have no matched control endpoints and no delivered HELLOs: session code cannot
recover traffic that DDS discovery has not delivered. This limit remains visible.

Two optional experiments preserve the defaults:

- `--startup control-first` holds simulator publication until both command owners
  qualify, verifies zero produced samples, then starts warmup and the same fenced
  workload. Impairment and the N5 competitor are active throughout. It is not a
  demonstration of joining a system already streaming telemetry. Default remains
  `simultaneous` and retains its failed startup result.
- `--dds-profile udp1200` explicitly selects UDPv4 + SHM maxMessageSize 1200.
  The N5 development capture has maximum IPv4 length 1224 and no IP fragments,
  but startup still fails. This is a failed packetization-only remedy. Default
  remains `system`; buffer sizes, application QoS and lease gates are unchanged.

Repeated fault acceptance also exposed an intermittent shutdown timeout. Workers
are now joined by a pre-shutdown callback while their publisher context is valid.
The nested handler context is owned by the node, outliving the joined worker;
its destruction is deferred beyond that callback. The prior timeout is preserved
as observed evidence; no debugger stack established a specific middleware lock
cycle. Three consecutive final fault runs retain the five-second shutdown gate.
Each also verifies that a blocked handler reply causes UNKNOWN without expiring
an otherwise live lease, then exercises receiver and sender SIGKILL, QUERY without
old COMMAND replay, and a new intent after explicit device reconciliation.

The harness now waits for cumulative diagnostics before asserting command-send
counts. Phase files use atomic replacement and a read that tolerates a transient
missing file; malformed JSON still fails. Phase IDs advance in memory. These
files coordinate the lab and carry device diagnostics; command outcomes remain
DDS/journal results. The file race, premature handler readiness, diagnostic lag,
shutdown failures and failed packetization/startup attempts are preserved under
`development/`, alongside mixed N2 completion outcomes. Two M2 invocations failed
before any build at the unchanged image-ID gate; read-only rechecks match the pin,
and unchanged full-build retries pass. The cause is unestablished; the gate remains.

See [results](RESULTS.md), manifests, test logs, source verification and raw artifact
hashes. Captures and journals stay local and ignored. Full-duration impaired seeds,
clock/security equivalence, matched CPU/wire windows, N3 selection and N4 phase
barriers remain open. Intrinsic/M4 is untouched.

Transport configuration references: [Fast DDS 2.14 XML transport settings](https://fast-dds.docs.eprosima.com/en/2.14.x/fastdds/xml_configuration/transports.html)
and [Jazzy rmw_fastrtps configuration](https://github.com/ros2/rmw_fastrtps/blob/jazzy/README.md).
Lifecycle reasoning was checked against [Jazzy Context shutdown](https://github.com/ros2/rclcpp/blob/jazzy/rclcpp/src/rclcpp/context.cpp)
and [signal handling](https://github.com/ros2/rclcpp/blob/jazzy/rclcpp/src/rclcpp/signal_handler.cpp);
the installed API and runtime regressions determine the local acceptance result.
