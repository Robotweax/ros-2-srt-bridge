# Broader N5 seeds and closed telemetry localization

Freeze plan/source before new live runs. Complete the remaining base-seed coverage
on the unchanged a866505 runtime, using the previous4211 cohort as separate prior
evidence, never as a new slot or historical reclassification. PR2 draft, M3 open,
Intrinsic/M4 untouched. No production/SDK/provider/clock/budget/replay/profile change.

New slots exactly once, ordered: N0/1701/15s, N5/1701/300s, N5/2903/300s. Stop on
first selected durable-outcome/integrity failure and mark later slots NOT_EXECUTED.
No repeat of4211, additional seed, retry or tuned configuration after results.
Require preflight8 runtime hashes equal the preceding durable-expiry cohort and
fixed across live, same pinned image/provider, dynamic neighbors,200/50Hz targets,
2s offered commands,5s original budgets,8s result drain, command/provider diagnostics,
tcpdump startup/drain/population gates. No builds/tests/heavy analysis overlap live.
Both unchanged all-success and prospective success-or-qualified-durable-expiry
completion remain explicit. No fullN5/all-offered-slot/deadline guarantee implied.

Telemetry diagnosis first uses closed prior N0/4211 and N5/4211 originals, then the
new closed rows, with identical analysis and original artifact hashes. Separate
application conservation counters from whole-capture UDP/SRT outer-header evidence:
- Reconcile every capture rotation/file/footer/filter/kernel population. Parse
  only bounded classic Ethernet/IPv4/UDP, fail on truncation/fragments/invalid
  lengths, never decrypt payloads. Compare full UDP payload identity MULTISETS
  from robot egress and operator ingress, plus reverse feedback direction.
- Classify pinned-provider SENSOR DATA versus parity(message0), CONTROL types,
  retransmission bit and message/packet/receiver-socket identities. Distinguish
  repeats, unique messages, fragmentation boundaries and packet data from decoded
  application SAMPLE counts; do not assume1:1 or bind encrypted messages to typed
  source counters. Report whole closed capture scope (setup/teardown included),
  no PCAP realtime/measurement-window arrival or age authority.
- Report separate hierarchical root/child qdisc deltas (never sum duplicate drops),
  TBF512kbit and16-packet netem backlog, actual configured UDP competitor128Kbit/s,
  source/receiver clocks/rejections and existing stage gaps. Qdisc snapshots have
  different tails from capture/app windows; no exact per-flow drop inference.
- Use immutable pinned SDK source read-only to interpret outer headers and
  provider semantics. No edits/builds in dependency. API acceptance != emission
  or delivery; shared captured identities do not establish pre-tap passage.
  Control packet counts/byte shares alone do not prove an internal cause or justify
  retuning; state what remains unobserved (SENSOR provider internals/typed mapping).

Add packet-parser/identity/rotation/corruption guard tests, host/syntax checks
before live. No new SDK/ROS rebuild; prior SDK72/ROS41 remain prior validations.
Run closed analysis before and after, never during live. Preserve all verdicts,
raw PCAP/journals/resources/provider streams locally with hashes and selected
metadata publicly with explicit omissions/derived hashes. Cleanup owned namespaces.
If localization suggests a mitigation, freeze a separate controlled future plan;
do not change this cohort or infer transport superiority/hardware/clock/resource/
security qualification. Old UNKNOWNs stay unresolved.
