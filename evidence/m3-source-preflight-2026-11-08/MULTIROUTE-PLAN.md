# Two-peer sustained N0 accounting preflight (2026-11-08)

Separate from the completed isolated source run: execute exactly once with
`python3 tools/m3_ros_multiroute.py --output .local/m3-ros-multiroute/1`.
Commit this plan and source first, after206 host tests pass. No retries or
replacement of a failed verdict. Pinned Linux amd64 Docker image, existing
provider/runtime, one ten-second source window, source/sample diagnostics enabled.
The isolated source fixture has passed; the extra bridge/observer work can still
change actual cadence, which must be measured again.

Owned internal Docker network, separate ROS domains41/42, LOCALHOST discovery,
N0 kernel qdisc readback with seeds1701/1702 and explicit permanent-neighbor
fixture. Shared boot/time-namespace proof. Source starts disabled. Both endpoints
must be ready/clock-qualified with stable empty pipelines before arming. Source
resumes once, pauses once, then both sides drain and obtain stable empty metrics.
No COMMAND workload, injected loss, capture or packet-level identity claim.

Require source trace complete, zero drops/hash/encoding failures, exact fenced
counts, contiguous source counters and phase progression including skipped slots.
Actual counts divided by measured resume-to-pause duration must individually be
within1% of200Hz IMU /50Hz joints. Every remote typed hash/stamp must match its
source and preserve per-route order without duplicates. Keep absent IDs explicit.

Require complete sender and receiver sample traces with no drops/exhaustion;
source route/stamp -> actual admission -> SDK-assigned message/context -> receiver
Session decision joins. Exactly one initial binding, consecutive SDK message
numbers and one ISN; these are SDK metadata, not independently captured wire
identities. BUSY/obsolete admissions consume no SDK index. No SDK send errors.
Match all admission/rejection/SDK/receiver populations to metrics. Source inputs
without callbacks, queued inputs without SDK handoff, SDK messages without decoded
receiver decisions and accepted sources without typed observation remain explicit.
Only aggregate counters establish loss stages; no fabricated individual stage
attribution or lossless assumption. All six conservation balances must be zero,
all loss terms nonnegative, pending queues empty. Both route histograms must
reconcile publications and accepted-publication upper ages remain<=250ms.
Sessions/owner/generations/readiness/clock/QoS/isolation must remain qualified.

Record source commit and five runtime hashes before/after; preserve original
results/logs/trace/cadence and tests, excluding credentials, inspect/environment
dumps, journals and raw resource samples. Cleanup only owned containers/network,
remove the passphrase. This is a short N0 source/admission accounting preflight,
not sustained seeded N3/FEC, independent packet capture, M3 completion, physical
sensor age, resource comparison or Intrinsic/M4 development.
