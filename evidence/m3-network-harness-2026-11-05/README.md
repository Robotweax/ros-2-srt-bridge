# M3 network harness — development evidence, 2026-11-05

PR #1 was merged as `32c53b27839182ec45c448694c60fe1691466118` before this work.
M3 is **in progress**, not accepted. The current contribution is the SRT-side
kernel network harness, bounded diagnostics, capture/resource accounting and
reproducible development workload. See [results](RESULTS.md) and
[the remaining plan](../../baselines/m3-plan.json).

`N0-full/` records a clean SDK/ROS build, tests and a 300-second measurement
window. `N1-smoke/`, `N2-smoke/`, `N4-smoke/` and `N5-smoke/` retain short
functional runs, not full impairment qualification. The full N0 manifest's source
hashes match the current implementation. Earlier runs retain their original
source hashes and configurations; they are not relabeled as runs of later code.

N0 confirmed 150 distinct commands with exactly 150 device effects. The observer
received 27,569 IMU and 13,709 joint samples, zero direct DDS samples and no invalid
or duplicate payloads. Both endpoint captures were complete and contained no
RTPS traffic or parser-unaccounted frames. Gaps before the WAN boundary remain
substantial and must be investigated; see the explicit populations in RESULTS.
Freshness is an upper-bound measurement on published samples, not a claim that
all source samples arrived or that their acquisition age is known.

N4 initially failed when changing a root qdisc from pfifo to netem with the same
handle. Neutral netem for N0 makes the loss/restore transition valid; the rerun
passed. N4 currently uses a two-second wait after both loss rules are installed;
Docker command overhead makes the measured host outage longer (2.278 seconds in
this run). This is not exact VM-clock barrier timing or the required three
command-phase cases. Random loss is explicitly rejected as a substitute for N3.

The first image build could not resolve an unpublished local M2 image through
BuildKit's digest resolver. The M3 Dockerfile now starts from the pinned public
ROS image and repeats the exact M0 development package versions. It builds
iproute2 6.17.0 from the upstream hash-checked archive. The seed probe confirms
that kernel 7.0.14-linuxkit retains netem seed 1701. No host qdisc was modified;
only new internal-network containers received NET_ADMIN. Temporary containers,
network and passphrase files were removed after every run.

Regression: `sdk-regression/` contains 15 Debug, 15 core ASan/UBSan, 67 native,
10 native ASan/UBSan and relocated installed-consumer checks, all passed.
`m2-regression/` reruns the original rate-change/lost-reply/crash/reconnect demo
successfully against these changes. The ROS tests contain the six existing codec
cases plus publication histogram boundaries/population (seven cases; colcon also
counts the wrapper). Six Python profile/parser/resource/censoring tests pass.

Raw capture/resource files remain in the ignored local run directories, described
by `raw-artifacts.json` hashes/sizes. Summaries and logs are retained here. Packet
accounting uses the pinned provider's reserved message-number-zero parity format;
it does not decrypt data. Egress capture is before qdisc, so ingress capture and
qdisc readbacks must be considered when attributing wire loss. CPU excludes the
observer and capture; RSS sums may double-count shared pages. Histograms stop at
the last diagnostic snapshot and explicitly disclose the unobserved tail.
Admission rejection counters do not provide a complete per-route attribution of
all local ingress, latest-only, poll-expiry and publication losses yet.

Next: attribute the N0 source-to-wire gaps, tighten exact window/tail and achieved
rate accounting, implement the fully journaled DDS command baseline and the
N3 deterministic DATA/FEC fault selector, add N4 command-phase barriers and run
the remaining full-duration three-seed matrix. The comparison must disclose
security/overhead differences; no SRT superiority, physical-device, power-cut or
Intrinsic conclusion follows from these development results.
