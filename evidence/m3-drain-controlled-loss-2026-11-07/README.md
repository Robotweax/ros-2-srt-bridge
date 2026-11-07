# Bounded capture drain and controlled child loss — 7 November 2026

The known unread-buffer capture class was reproduced, an opt-in shutdown check
was validated on finite traffic, and the stage observer distinguished a known
root-loss interval in live SRT. The live 60-second case has **22 successful
commands/effects, eight skipped slots, no unresolved intent and reconciled final
PCAP counts**. This does not fix or reclassify the historical two-record failure,
localize the old spontaneous gap, or complete N4/N5/M3 qualification.

## Known capture class

The committed [plan](diagnostic-plan.json), source `23ffa00`, specifies two fresh
owned N0 fixtures. Each sends 16 tagged UDP datagrams while both tcpdump processes
are deliberately paused; native observers and the receiver remain active.
PID/start identities and VM signal brackets are retained.

| Case | File/captured | Kernel-filter accepted | Kernel drops | Native / receiver |
| --- | ---: | ---: | ---: | ---: |
| Stop while paused, then resume | 0 | 16 | 0 | 16 / 16 |
| Resume, drain check, then stop | 16 | 16 | 0 | 16 / 16 |

The abort case deliberately fails the capture-population gate while successfully
reproducing the intended class. It is not qualified capture. In the positive
case, resuming allows normal dispatch; the subsequent check observes two stable
equal live-counter snapshots. This does not prove that the extra check alone
caused completion, nor that the historical mismatch had this cause.

Upstream [libpcap 1.10.4 Linux statistics](https://github.com/the-tcpdump-group/libpcap/blob/libpcap-1.10.4/pcap-linux.c)
include accepted packets not yet read by the application.
[tcpdump 4.99.4](https://github.com/the-tcpdump-group/tcpdump/blob/tcpdump-4.99.4/tcpdump.c)
uses breakloop on interrupt and reports application callbacks separately from
library statistics. Installed distro package versions and upstream/distro
limits are recorded in [source notes](source-notes.json); byte-identical source
patching is not assumed. The installed behavior above is directly measured.

## Opt-in shutdown guard

`--capture-drain-check` retains the existing load stop and 1.25-second quiet
period, then requests fresh SIGUSR1 statistics from the one tcpdump in each owned
container. It allows up to five controller seconds for two unchanged snapshots
with captured==filter, zero kernel drops and stable PID/start identity. Signal
brackets are VM monotonic; controller-read timing is host monotonic and is never
subtracted from VM timestamps. A timeout/failure is retained, and captures are
still stopped. No restart or reconstruction occurs.

This is a bounded observation guard, not active packet draining or proof that
no later packet can arrive. The final file/footer/population gate remains
required and unchanged in meaning. Default shutdown does not enable this guard.

A post-measurement parser hardening requires **standalone final footer lines**;
inline SIGUSR1 snapshots cannot substitute for missing shutdown completion.
The new regression rejects a live-stats-only log. All original probe/live
footers were rechecked with identical outcomes. This tightens failure handling;
it does not rescue the old failed population count or alter recorded data.

## Deterministic live interval

One N5/seed1701 60-second case uses permanent-neighbor and TC PASS diagnostic
candidates, plus all existing observers. At one third of the source duration
from host observation of its marker, robot's existing child netem changes to
100% loss. Only the child is changed; the TBF root, classifier and neighbors
remain configured. Loss is explicitly restored to 0% and read back. Final-read
failure paths attempt restoration in `finally` and have regression coverage.

The requested two host seconds become a guaranteed VM active interval of
**2.370079501 s**. The predeclared settled interval excludes the first 500 ms
and final 100 ms, leaving **1.770079501 s**; no margin was adjusted afterward.

| Settled interval observation | Result |
| --- | ---: |
| Adjacent TC observer pairs wholly inside | 8 |
| Selected robot PASS execution increase | 217 |
| Whole-interface root drops increase | 15563 |
| Robot outgoing CONTROL tap observations | 0 |
| Operator outgoing CONTROL tap observations | 167 |
| Outgoing CONTROL in 3 s after restore, robot / operator | 106 / 114 |

The known configured-loss signature is observed. Root drop counts include all
interface traffic and are not assigned to individual CONTROL packets. Selector
counters are aggregate UDP executions, not exact authenticated packet pairs.
A fully observed robot source gap of **2.578343668 s** includes this interval;
its leading/trailing edges extend beyond the known configuration and are not
uniquely attributed. Permanent state/MAC remains verified; no active CONTROL
loss/close occurred. This is a mid-window whole-endpoint fault, **not** admission,
dispatch or result-commit phase-barrier acceptance for N4.

## Final capture and safety checks

The live drain guard records two stable equal snapshots at **32118** per role.
Final file/captured/filter counts all agree at **32118 per endpoint**, zero kernel
drops. Native counts are **32144 per endpoint**, zero reservation/copy failures;
these populations are not equated. Realtime PCAP windows remain withheld by
clock qualification. The earlier 110673-filter/110671-file failure remains failed.

TC logs **404/404**, provider logs **700/20/675** and command traces **78/5/5** are
complete without loss/exhaustion. Maximum observed TC read span is 60.275959 ms
and sample-start gap 210.175292 ms, not bounds or negligible overhead. The
classifier, polling and shutdown statistics requests remain interventions.

Closed immutable journals match all 22 successful results/context fields; every
intent has one SDK handoff and receiver dispatch precedes its conservative start
deadline. No old UNKNOWN, nonexecution, expiry or replay conclusion is changed.
Source/published/observer sensors are **15033/1941/1941**, conservation balances
zero, with the large deficit retained. No lossless delivery, physical realtime,
security parity or performance claim is made.

155 host tests passed before execution, 157 after the settled-window analyzer,
and **158** after the inline-footer guard; syntax checks pass. Source hashes match
the measured frozen commit, eight runtime hashes match before/after. The later
read-only analysis/footer-parser changes are distinguished in provenance. No
fresh full SDK/ROS/M2 execution is claimed; runtime/protocol/timeout/dependency
and default fixture settings are unchanged.

[Findings](findings.json), [known settled signature](live/root-loss-analysis.json),
original probe/live manifests, pause/signal/readback/drain logs, state/counter
samples, gap analyses and journal audits retain their scopes. Raw packet
payloads/prefixes, journals, clocks and resources stay local with hashes. No
credentials or inspect/environment dumps are published.

Next: use the validated measurement guards for deterministic N3 DATA/FEC selection
and N4 command-phase barriers. The spontaneous residual gap and exact historical
capture/reset causes remain open; do not substitute this known-fault diagnostic
for the failed baseline cohorts. PR #2 stays draft; Intrinsic/M4 untouched.
