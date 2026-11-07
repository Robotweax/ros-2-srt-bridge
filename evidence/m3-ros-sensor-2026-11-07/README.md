# Finite ROS SENSOR qualification attempts

Both attempted cohorts remain failed at their baseline. No ROS one-loss or two-loss
case ran. M3 and full N3 remain open; PR #2 stays draft. The existing SDK, bridge
and ROS binaries were reused unchanged. Six selected provider/transport/endpoint/
bridge/observer hashes match before and after measurement. No full SDK/ROS/M2
regression run is claimed; 170 host tests and Python syntax checks pass.

The new finite driver publishes 19 typed IMU messages at requested 20 Hz, then
fences the source and drains the pipeline. This is a focused development fixture,
not the full 200-Hz IMU/50-Hz joints workload. It checks complete canonical typed
payload hashes, exact IDs and publication order, actual Best Effort/Volatile/
KeepLast(1) QoS, configured conservative clock qualification, upper publication-age
histograms and the existing six sensor conservation equations. No sample payload
travels through coordination files. Shared artifacts contain hashes and metrics.

The source remains disabled while an identity capture is closed. A fresh bridge
session must have exactly one outgoing source DATA message, SENSOR_BIND/message1,
observed at both endpoints; the same owned flow's outgoing handshake must agree
on its initial sequence. The selector would then target row1/message8 or messages
7/8. This accounts for the binding before samples. Outer headers are routing
observations, not independent cryptographic identity proof. A separately started
measurement capture must be ready before arming. The deliberate interval between
closed identity and measurement phases has no continuous-capture claim.

## Original plan (`2f13689`)

Exactly one baseline was attempted under the original plan. The five-second
unchanged-counter drain guard failed before arming: ongoing CONTROL probe/clock
traffic kept all-UDP capture counts increasing, although each fresh captured/filter
snapshot was equal and zero kernel drops were reported. The original manifest,
failed drain and cleanup diagnostics remain unchanged. No source was armed and
loss cases were not executed. Final footer equality does not retroactively pass
the failed bounded guard. This guard observes quiet population stability; it does
not cause active CONTROL traffic to stop.

## Separately planned revision (`f048464`)

The revised finite fixture explicitly limits PCAP to SENSOR DATA/parity and
handshake traffic:

```
udp port 10081 and (udp[8] & 128 = 0 or udp[8:2] = 32768)
```

Native observation remains all-frame. PCAP totals are therefore a different
population. Filter compilation was checked in the pinned image. Stable drain,
standalone footer/file/filter reconciliation, zero loss and exact DATA/parity
identity checks remain mandatory for the declared populations. Default runners
and their all-UDP capture are unchanged. Cooperative abort also breaks a pre-arm
scenario wait, and cleanup does not overwrite a failed drain artifact.

Exactly one baseline ran and failed its strict19-payload population gate:

| Stage | Count |
| --- | --- |
| ROS publication calls / typed sender ingress | 19 / 19 |
| Sender BUSY / obsolete results | 1 / 0 |
| Sensor admitted / SDK sends | 18 / 18 |
| Receiver decoded / published / observer | 18 / 18 / 18 |
| Missing original source ID | 7 |

`TransportOwner::Impl::submit` returns BUSY for a sample only when its
`std::try_to_lock` cannot acquire the shared mutex. Metrics establish one such
rejection, but do not identify the competing holder or lock duration. This is
explicit nonblocking admission behavior, not evidence of network loss. No SDK
retry or source republish was introduced. The production policy was not changed
to satisfy a finite test.

The failed case is diagnostic evidence only. Post-hoc analysis of closed outputs
shows all six conservation balances zero and only `admission=1` nonzero; all18
observed typed payload hashes match. Their publication age-upper maximum is
9,643,682 ns (ceil-ms histogram maximum10). These are bridge callback-ingress-based
upper ages under the configured clock assumptions, not physical sensor age or
PCAP realtime latency. No other missing population is assigned to the network.

Closed identity capture passes the handshake/binding checks. Measurement native
and PCAP identities match the actual18 sends plus4 parity packets, with complete
native counters, zero reported capture loss, reconciled final footers and stable
drain. This post-hoc actual-admissions expectation is separate from the original
planned19-source gate and does not change its failed status. The normal success
path's final feature comparison was not reached and is not claimed. No injected
classifier was installed in either attempted baseline.

Both original manifests, prospective plans, selected logs, metrics, hashes,
provenance and post-hoc analysis are retained. Raw captures, journals, detailed
resource/clock traces and process/environment inspect data remain local under
`.local/m3-ros-sensor/` and `.local/m3-ros-sensor-r2/`; credentials are removed and
not published. Installed artifacts and source commits are separately recorded.

Next: add bounded correlation of sample admission and SDK handoff identities so a
selected row is tied to actual admitted samples while retaining BUSY losses. Do
not repeat until a favourable baseline or assume every ROS publication consumed a
SRT source/message index. ROS one/two-loss publication recovery, deliberately late
repair rejection, the full multiroute/rate/seed matrix and N4 command phases remain
open. Prior provider-level FEC cases remain separate; Intrinsic/M4 is untouched.
