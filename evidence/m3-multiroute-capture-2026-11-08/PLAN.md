# Sustained mixed-route capture and one-source FEC fault plan

Freeze source and this plan after210 host tests pass. Exactly two conditional
single executions, using the pinned existing Linux amd64 image/runtime:

1. `python3 tools/m3_ros_multiroute.py --output .local/m3-multiroute-capture/baseline --capture`
2. Only if1 passes every gate, run once:
   `python3 tools/m3_ros_multiroute.py --output .local/m3-multiroute-capture/one-loss --capture --losses 1`

Stop on the first failed fixture. Preserve its original verdict; no automatic
retries, replacement baselines, selector changes or retrospective gate relaxation.
The previous no-capture N0 preflight remains separate evidence.

Each run uses existing phase-preserving C++ IMU200Hz /joints50Hz source for one
nominal ten-second window, source/sample diagnostics enabled, source disabled
before arming and fenced/paused before draining. Owned internal Docker network,
separate ROS domains/LOCALHOST, explicit permanent neighbors, N0 qdisc readback
seeds1701/1702. No COMMAND workload, SDK/provider or production policy changes.
All prior source/cadence/typed-hash/session/QoS/accounting gates remain: actual
counts / measured fence duration within1% for both rates; complete source traces,
no diagnostic drops/exhaustion, skipped slots explicit; all six conservation
balances0, nonnegative loss terms, stable empty checkpoints, publication ages
under250ms and no direct DDS leakage. BUSY and mailbox replacements are allowed
only when explicitly balanced; passing never means lossless source delivery.

New independent capture gates use the already qualified opt-in packet-socket
recorder, final BPF attached before bind and initial kernel count0. Native observers
start first and close last. Close the identity phase before source arming: one
binding source message1 at both endpoints, consistent handshake ISN, exact strict
native/PCAP populations, complete native metadata and reconciled packet recorder
file/dispatch/kernel counts, zero drops/truncation/exhaustion, stable drain, size
and hash. Measurement is a separate phase covering the whole source window.

Join source route/stamp -> admission -> actual SDK message/ISN to native and full
PCAP headers, not nominal ROS publish indices. For M SDK-accepted messages including
binding1, measurement must contain exactly the SAMPLE source messages2..M and
floor(M/4) parity packets (sequence ISN+3,+7,...); partial final rows have no
invented parity. Exclude precisely message8 only for the fault run. Both endpoints
must agree exactly on source/parity key multisets, and all packet recorder
populations must reconcile strictly. No capture subtraction, prefix rescue or
historical-failure diagnosis. Interface feature snapshots must stay unchanged.
Realtime PCAP timing is not used as a qualified measurement clock; native kernel
monotonic timestamps are skb observations, not physical-wire times.

The fault is selected before publishing: four-source row1, position3, SDK message8,
exact SENSOR UDP tuple/socket/ISN, excluding message-zero parity. Require exactly
one classifier drop and removal/readback of only the owned hook. Require all four
SDK messages5..8 and both route IDs in that row; if actual admitted population
differs, the fixture fails rather than moving the target. Require message8 absent
at both native/PCAP taps, its row parity present, exact original typed hash/stamp
observed once and an explicit accepted receiver Session decision. Native incoming
parity <= receiver decision end <= typed observation, all while the original
classifier is installed. This verifies reconstructed selected-source observation;
no generic irrecoverable-loss counter, cryptographic-FEC identity or physical
sensor-age claim. Aggregate replacement counters do not assign individual loss
stages to other unmatched IDs.

Record source commit and seven runtime hashes before/after. Preserve plans,
original results, selected lifecycle/capture status/clock/qdisc/fault logs, hashes,
source/sample traces, typed hashes/metrics and tests. Raw PCAP/native prefixes,
resource/endpoint details and journals remain local with hashes; no credentials or
full inspect/environment dumps archived. Remove owned fixtures and passphrase.
No SDK/ROS code changed: previous SDK70 /ROS41 remain last full validation, not
rerun in this Python-only extension. These two short cases do not qualify the full
N3 seed matrix, N4, M3 completion, resource parity, hardware or Intrinsic/M4.
