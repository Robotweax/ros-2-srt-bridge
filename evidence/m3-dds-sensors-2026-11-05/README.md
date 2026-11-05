# M3 direct DDS sensor development baseline

The new runner exercises typed Best Effort/Volatile/KeepLast(1) Imu and six-joint
JointState DDS across the owned internal Docker bridge, using the same phase-
preserving 200/50 Hz simulator, pinned M3 image and seeded netem profiles. It is
sensor-only and does not qualify M3 or the Reliable command contract. No command
is sent and no direct service call is substituted for journaled commands.

Both endpoints use ROS domain 60 and explicit static peers. A first multicast-
only run observed outgoing discovery traffic but received no typed stream and
timed out; peer addresses fixed that observed failure. Static-peer behavior is
documented in the official [ROS Jazzy discovery source](https://github.com/ros2/ros2_documentation/blob/jazzy/source/Tutorials/Advanced/Improved-Dynamic-Discovery.rst).
The endpoints have separate container IPC/network namespaces, no published ports,
and no host qdisc changes. The capture must contain eth0 RTPS, complete tcpdump
counts, no snaplen loss or kernel drops and no SRT traffic. Discovery can create
IPv4 fragments; opt-in DDS accounting records each fragment's frame bytes and IP
fragment payload bytes without assigning it an RTPS/UDP payload classification.
SRT capture handling retains strict fragment rejection by default. Fragmented
traffic on known SRT ports still fails DDS capture validation.

The source is paused in the sensor timer callback group. After a drained/stable
begin snapshot, source publication resumes; at cutoff it pauses again and the
observer drains. Source fence timestamps share one simulator monotonic clock.
Per-route received counts partition into accepted, stale, invalid and clock-
rejected; the remaining produced population is missing before the callback.
That boundary includes source middleware, kernel, network and receiver history,
and is not physical WAN packet loss. Cumulative histogram subtraction must match
the accepted population exactly. Pre-begin markers and markers beyond the end
source fence fail the run. Shared files coordinate phases and convey source
counts/timestamps, never sample payloads.

Age is a callback realtime-minus-ROS-header estimate on the common Linux VM,
rounded up to 1 ms for accepted samples. Boot IDs and time-namespace offsets must
match. Realtime reads are bracketed by monotonic reads: scheduling width is
uncertainty, not clock drift. Read brackets wider than 1 ms reject that sample;
observed offset steps exceeding 1 ms between callbacks disqualify age estimates
and reject subsequent samples at the clock gate while preserving count accounting.
A sensor-count pass does not qualify those age estimates. Bounded step evidence
is retained in the result. Gradual
realtime/monotonic offset drift remains diagnostic. This is not SRT's conservative
clock-interval age guarantee and does not establish cross-host clock accuracy.
Its origin is the simulator header timestamp; SRT starts age at bridge ingress.
The 250 ms estimate gate therefore also has a different origin and cannot be
used as an equivalent end-to-end freshness comparison.
Discovered publisher endpoints verify Best Effort/Volatile; their history/depth
can be reported unknown, so requested subscriber depth one and the simulator's
source QoS configuration are retained rather than claiming discovery proves depth.

Final runs: `n0-30s` is `.local/m3-dds/20261105T161851009485Z`;
`n1-smoke` is `.local/m3-dds/20261105T161943936259Z`. Both retain source hashes
matching all 124 current source inventory files. They explicitly reuse the built
simulator (`skip_build=true`), with its binary hash recorded. The initial full
attempt rebuilt all three ROS packages; the final installed scripts/helper were
subsequently installed and compared byte-for-byte before the import/help check.

See [results](RESULTS.md), run manifests and the Python test log. Historical
failures are retained under `development/`: multicast discovery timeout, the
unbracketed-clock false jump, and a capture rejection of legitimate discovery
fragments. A five-minute attempt also failed the original hard clock-step gate;
its failure path discarded final count snapshots and did not record step size,
so neither its sample results nor the clock-step cause are inferred. The final
runner separates count validation and age qualification and retains step evidence.
Each historical manifest preserves the source hashes recorded at invocation.

This path is direct DDS rather than SRT bridge ingress/egress hops. There is no
command load or DDS encryption here, no matched-window CPU measurement, and frame
totals cover the entire capture including discovery and observed local services.
It cannot support a head-to-head performance/security claim. Reliable commands
must reuse the durable admission/dispatch/result and conservative UNKNOWN/no-
replay contract; command transport integration remains the next work item.
N3, N4 command barriers and the complete duration/seed matrix remain open.
