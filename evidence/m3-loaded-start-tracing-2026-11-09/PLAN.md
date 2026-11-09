# Prospective loaded start-trace cohort, no tuning

Use exactly the matched isolated SDK/ROS binaries qualified in
m3-start-tracing-2026-11-09 (SDK75/ROS41/host364), plus unchanged calibrated ARP
tracer/native observers and pinned SRT archive/image. Explicit opt-in fixed runtime
layout selects those prefixes with --skip-build; hash-validate ALL matched build
binaries before/after. Preserve original installed baseline; no symlink replacement,
copy-over, runtime rebuild, source/provider/default/policy/rate/queue/neighbor/
budget/idle/timeout change. Python prefix-selection plumbing only before freeze.

Freeze/test harness source, match archives and resolved ROS setup/package paths
before live. Exactly once sequential N0/2903/15s, then N5/2903/300s if prior gates
pass. Stop on first harness/integrity/durable-command gate failure; no retries,
additional seed or fault after results. N5 fixed512kbit TBF/16 child/128Kbit
competitor; dynamic neighbors,200/50Hz sensor targets,2s offered commands,
original5s command budget/5000ms provider idle/8s result drain. No injected fault,
active ARP request, synthetic flood, ping, flush or permanent neighbor. Existing
command/both-provider/native-v2/UDP-PCAP/drain/neighbor/CONTROL-qdisc/reply/ARP
packet diagnostics plus explicit calibrated start diagnostics on both peers.

N0 requires positive matched start/grant/consume/gate/handler observations and
matching closed success entries, complete observer populations, positive ARP and
selected CONTROL controls, unchanged roots/features. Native/ARP tracer paths and
binaries unchanged. Capture readiness before producers, drain/detach before close.
No tests/builds/heavy analysis while either live capture runs. No performance or
mitigation claim: extra tracing and new matched binary baseline add observer work.

After closure/source verification, analyze ALL attempts and ALL start groups,
not only rejections or near-edge cases. Join request/session/owner/route/origin,
check/worker tokens, slot/generation and immutable command context to closed
sender/receiver journals. Actual grant deadline remains distinct from earlier
admission clock sample and original command deadline. Classify coordinator
refusal, failed execute submission, consume1/2/3/4 and second-gate/handler path;
retain unavailable stages, canceled owner observations, bounds and censoring.
Explicit branch observations never authorize replay/nonexecution/expiry. Report
all strict successes, qualified journal-only expiry, REJECTED/UNKNOWN/unresolved,
skips and effects. Preserve failed gate even if tracing succeeds; old command34
and UNKNOWN98/12 cannot be retrospectively reclassified or replayed.

For every start, retain exact consume/grant and second-gate/grant slack and
command/grant cap; sample old admission-clock margins only as separate context.
For every non-success report complete actual start history or why unavailable,
journal/effect proof and nearby context/clock events. Retain all >=1s CONTROL
gaps/active loss windows and all positive ARP reply-counter steps within source
publication with per-cookie packet lifecycles/carry-in/out as in prior cohort.
Never infer packet drops from counters or unique ARP/request causality from a
missing tap. Keep telemetry/conservation outcomes and qualified scope explicit.

Publish source/binary/raw manifests, exact omissions, removed owned namespaces/
rules/credentials. PR2 stays draft/M3 incomplete/Intrinsic-M4 untouched; all prior
FAILED/UNKNOWN outcomes and full N3/N5/default-loaded-DDS/clock/security/resource/
hardware/comparison gates remain open. No tuning follows this cohort.
