# M3 sender cadence follow-up — 2026-11-05

The major N0 source-gap cause is identified and fixed. M3 itself remains in
progress. See [results and limitations](RESULTS.md), the original
[network harness evidence](../m3-network-harness-2026-11-05/README.md), and
[the current plan](../../baselines/m3-plan.json).

A 200 Hz producer offers a new sample about every 5 ms, but the transport owner
could wait 10 ms before draining its latest-only mailbox. The 30-second
attribution run found near-complete typed ROS ingress with 2,633 mailbox
replacements, alongside 2,650 missing IMU samples. A native 200 Hz regression
failed against the old wait (48 of 100 delivered). This isolates an avoidable
local transport cadence limit rather than attributing it to WAN loss.

Active caller owners now request a 1 ms epoll timeout. Disconnected/listener
owners retain 10 ms timeouts; these are configured waits, not scheduler guarantees; every send still checks per-route pacing, estimated bandwidth,
session, clock and deadline gates. Mailbox/queue sizes remain bounded and the
sample budget remains 250 ms. This does not turn latest-only transfer into a
lossless or hard real-time channel. The pinned provider's system-socket epoll
poll interval is also 10 ms and its unified wait rejects system sockets, so
adding a wake descriptor alone would not remove that limit without dependency
work. The SRT source/archive remain unchanged.

Added diagnostics count typed ingress by route plus BUSY/obsolete submissions.
The M3 test observer retains sender/receiver/device snapshots before shutdown,
and the result helper exposes stage observations without forcing differently
timed snapshots to balance. These test artifact writes occur in the observer,
not the production bridge's sensor callbacks.

`after-5min/` records a fresh build and 300-second N0 run at the current source
hashes: 150 confirmed commands/150 effects; IMU gaps 741/53,534 (1.38%) versus
26,742/54,311 (49.24%) in the original five-minute run. The before/after short
runs, native failing/passing proof, CPU tradeoff and remaining losses are retained.
Capture completeness and absence of direct RTPS/DDS traffic were checked.

`sdk-regression/` passed 15 Debug, 15 core ASan/UBSan, 67 native, 10 native
ASan/UBSan and the relocated installed consumer. The native suite includes the
200 Hz delivery regression with an 80% relative gate for scheduling slack.
`m2-regression/` passed the original rate-change/duplicate/lost-reply/crash demo.
Seven ROS cases and seven Python helper cases passed.

The first full sanitizer attempt failed an older reconnect-test assumption: a
try-lock submission can legitimately return BUSY, especially at the faster owner
cadence. The test now retries only BUSY and requires the first non-BUSY result to
be OBSOLETE. QUEUED stale work still fails immediately. That failed attempt is
retained in `attempts/`; the subsequent full sanitizer run passed. No sanitizer
memory error was reported in the failed attempt.

Raw pcaps/resources remain ignored locally with hashes/sizes in
`raw-artifacts.json`. Original evidence is preserved with original hashes; the
new complete N0/SDK/M2 manifests match the current implementation. Wire version
1 and private worker IPC version 3 are unchanged. Rebuild the ROS message package
and nodes together for the additional local diagnostics fields.

Remaining work includes residual drop attribution, exact measurement windows and
achieved source-rate accounting, the fully journaled DDS baseline, deterministic
N3 DATA/FEC loss, N4 command-phase barriers and the complete duration/seed matrix.
The N5 smoke has a censored last result and is not full qualification. There is
no M3 acceptance, physical-device qualification, or SRT/DDS superiority claim.
