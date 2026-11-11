# Corrected CONTROL egress-fault validation — 2026-11-06

The corrected harness and analyzer observed the expected **known injected-fault
signature** in one prospectively planned 45-second N0 execution, seed 1701.
The earlier [failed attempt](../m3-control-egress-fault-2026-11-06/README.md)
remains failed and unchanged. This is diagnostic validation, not full N4/M3
acceptance or a diagnosis of the historical N5 initiating cause.

Source commit `cd54446` freezes the fresh [plan](diagnostic-plan.json). The 115
host tests and syntax checks pass. All measured source hashes match the frozen
source; eight runtime hashes match the previously tested SDK/ROS build both
before and after. No runtime, dependency, protocol or timeout change was made,
and no fresh full SDK/ROS/M2 test execution is claimed.

## Observed signature

Operator→robot CONTROL was selected by owned eth0, IPv4 UDP, exact peer /32 and
source port 10080. The filter installed, validated, and was deleted; the final
pre-removal action snapshot counted **303 packets/drops, 39356 bytes**. This is
not a guaranteed lifetime count. The empty post-delete readback verifies removal.
VM brackets bound the guaranteed active interval to **6.410313587 seconds**;
the requested six host seconds is not an exact VM-duration assertion.

| Observation inside the guaranteed fault interval | Result |
| --- | --- |
| Operator same-socket provider DATA-sent delta | 137, including 135 retransmissions |
| Operator provider ACK-sent delta | 159 |
| Operator post-filter outgoing CONTROL observations | 0 |
| Robot observations of the old incoming CONTROL flow | 0 |
| Reverse old CONTROL observations at operator | 159 |
| SENSOR source observations at each hook | 1046 |
| SENSOR parity observations at each hook | 262 |
| Outgoing CONTROL in the three-second restoration window | 92 per endpoint |

Provider totals use 43 adjacent available same-identity read pairs per endpoint,
with both read brackets wholly inside the fault interval. Retransmissions are
already included in DATA-sent; do not add them again. Selected counters omit
keepalive/handshake/ACKACK and have different temporal/type coverage from the
action counter. No exact equality is expected. The pinned archive is checked
before associating SDK handles with protocol routing socket IDs; reconnects
are not merged into the old flow. Provider mutex/bookkeeping observer work and
read-span/cadence uncertainty remain explicit.

The robot provider-loss trace occurred **5.001006502 seconds after the last
observed old incoming CONTROL packet**, followed by a session close with
SessionError none. Operator loss followed robot loss by about **1.195 ms**.
This differs from the roughly five-second endpoint-close separation in the
historical N5 case. The injected filter identifies this experiment's cause;
it does not retroactively identify the historical initiator or its full chain.

## Command uncertainty and capture completeness

There were **eight confirmed successes/effects, one unresolved intent (9), and
14 skipped slots**. Closed immutable journals have nine sender entries and eight
receiver entries. Results, revisions, command/context hashes and result generation
agree for the eight successes. Receiver deadlines are conservatively mapped and
slightly earlier than sender deadlines, not assumed equal.

Intent 9 has sender UNKNOWN/reconcile-required, revision 0, no valid result and
no receiver entry. The complete trace records **one SDK handoff**, with later
NOT_FOUND/query observations and uncertainty retained after the original budget.
No resend, nonexecution, expiry or fabricated result is inferred from absence.
The harness's original `passed` development verdict permits this uncertainty;
it is not qualification acceptance.

Provider logs retain **643/22/604** records across operator/first robot/replacement
robot; command traces retain **371/5/10**. All are complete, with zero diagnostic
drops or budget exhaustion. Maximum observed provider read span was 2.519750 ms
and sample-start gap 114.167500 ms; neither is a bound.

PCAP records/filter counts agree at **23862 per endpoint**, kernel drops zero.
Native counts are **23879 operator / 23882 robot**, with zero reservation/copy
failures; populations/intervals differ and totals are not equated. Realtime PCAP
windows remain withheld by clock qualification. Source/published/observer
populations are **11291/10258/10248**; all conservation balances are zero. This
is not lossless sensor delivery, physical-link evidence or a performance result.

## Retained evidence and next step

[Findings](findings.json), [provider-versus-egress analysis](provider-versus-egress.json),
[flow-isolated robot loss](robot-loss-flow.json), and [selected journal audit](journal-audit.json)
retain the independent observations. `run/run.json`, the result, diagnostic,
filter, restoration and cleanup logs are original unmodified copies. Raw PCAP
payloads, native prefixes, journals, clocks and resource samples stay local with
SHA-256 identities. No credentials or inspect/environment dumps are included.

Next: apply the validated distinction to a separately planned N5 diagnostic
with provider observations and complete flow-isolated capture. This fixture
establishes that selected successful provider sends can coexist with no post-
filter CONTROL observation; it does not show that the old N5 incident had that
cause. Historical UNKNOWNs/failures, full N5/M3, N3/N4, default DDS N5, clock/age,
security and resource-parity gates remain open. PR #2 stays draft; M4 untouched.
