# CONTROL silence investigation and directional-loss regression

This is read-only reanalysis of the retained failed independent-lane N5 case
at `.local/m3/20261106T181823876229Z`, not another random reproduction or a
replacement verdict. Original plan/manifests, intent 15 UNKNOWN and all historical
failures remain unchanged. No production runtime, provider dependency, timeout,
wire, deadline, lease or replay policy changed.

## Flow-isolated observations

`tools/m3_control_liveness.py` validates closed native-v2 capture coverage for the IPv4/Ethernet fixture,
record/counter/interface consistency, before/after hashes and common VM/time
namespace proof. CONTROL headers are grouped by UDP addresses/ports and SRT
destination socket ID. Reconnection attempts are not merged merely because they
share port 10080. Destination ID zero is not established-flow identity; routing
IDs are not authenticated connection identity. The tool rejects selected CONTROL
offload/VLAN/over-MTU representations and short headers. It never decrypts payload.

| Local observation | Last pre-event incoming old-flow skb (s) | Session change (s) | Observed quiet interval (s) |
| --- | ---: | ---: | ---: |
| Robot: operator → robot CONTROL | 32.509061932 | 37.517303435 | 5.008241503 |
| Operator: robot → operator CONTROL | 37.468471351 | 42.469670811 | 5.001199460 |

Times are relative to the recorded measurement marker. Both values are consistent
with the pinned provider's 5000-ms peer-idle default. This is not a historical
per-socket option readback, authenticated receive/liveness measurement, physical
wire-time bound or unique proof of the provider's internal expiry branch.

The operator→robot old routing flow has a fully observed approximately 5.127-s
inter-observation gap at both endpoint hooks. Operator outgoing observations stop
at about 32.509 s, while robot→operator traffic continues through about 37.468 s.
Later handshakes and other destination socket IDs are kept separate. The native
hashes match the previously archived raw-artifact hashes; no lost record is
reconstructed. Kernel capture reserve/copy loss was zero for the original case.

Whole-run root-qdisc drop deltas are robot 1755730 / operator 331. Child counters
overlap and are not summed. These totals cannot attribute a drop to CONTROL, a
particular flow or this interval. The qualified tap stage in this fixture is
after the tested egress qdisc; quiet at the operator hook therefore leaves SDK
scheduling, socket/queue handling and pre-hook qdisc loss unresolved. It does not
identify a physical WAN loss or prove that the SDK never attempted a datagram.

## Controlled one-way silence

A test-owned, bounded loopback UDP gate forwards both CONTROL directions for
handshake, then drops only listener→caller replies. SENSOR connects directly and
does not pass through the gate. Both SRT transports remain running until the
caller reports a CONTROL provider-loss event followed by a session-close action.
The test rejects a local protocol/clock-close error for that action, verifies
actual forward-direction drops and continued reverse forwarding, and retains
zero diagnostic loss. No global network/qdisc changes or timeout relaxation.

| Native family | Observed time after gate closure (ms) | Dropped reply datagrams | Forwarded reverse datagrams |
| --- | ---: | ---: | ---: |
| IPv4 | 5004 | 631 | 213 |
| IPv6 | 5004 | 619 | 208 |

Both transport-owner CTests pass, including their existing lifecycle/cadence/
reconnect cases (observed 462 / 459 checks). All 98 host Python tests pass,
including reconnect identity separation, censored intervals, sorting/duplicate
observations, unsupported representation rejection and handshake ID handling.
No new full SDK, ROS or M2 acceptance rerun is claimed for these tool/test-only
changes. Installed runtime behavior is unchanged.

The native fault demonstrates the provider-loss response to known one-way silence.
Its IPv6 coverage does not qualify an IPv6 capture parser; the read-only analysis
remains scoped to the recorded IPv4 fixture.
It does not prove why the original operator path went quiet, or equate a loopback
proxy drop with a drop before the historical egress hook. The historical
initiator remains unproven; full N5/M3 and N3/N4/security/resource/clock gates remain
open. No safe replay, fabricated expiry, performance advantage or physical delivery
guarantee is inferred. Intrinsic/M4 is untouched; PR #2 stays draft.

## Reproduce the read-only analysis

```sh
python3 tools/m3_control_liveness.py .local/m3/20261106T181823876229Z --event-ns 1647464158667 --out .local/robot-control-gap.json
python3 tools/m3_control_liveness.py .local/m3/20261106T181823876229Z --event-ns 1652416526043 --out .local/operator-control-gap.json
```

The underlying raw files must be retained locally. Public outputs contain header
routing metadata, hashes, counts and times, not packet payloads, credentials or
full inspect/environment dumps. Provider-source references in findings.json match
52be7c86ee1f303cbb0c8718c364217e4dd97a36 byte-for-byte. They document the default
and idle check without changing or republishing the dependency.

Next: correlate per-socket provider transmission/ACK/queue observations with the
operator egress hook under a prospectively bounded diagnostic plan. Distinguish
provider scheduling from socket/qdisc withholding before changing behavior.
