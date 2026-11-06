# V2/immediate observer study and short impairment probes — 2026-11-06

This follow-up repeats the descriptive observer on/off experiment for capture
artifact v2 and immediate PCAP mode, then adds short N1/N2 development probes.
It does not establish isolated observer cost, controlled hardware performance,
physical wire delivery, transport parity or complete M3 acceptance.

## Failed initial configuration and bounded buffer change

The initial v2/immediate study stopped on its eighth N0 run. Commands/effects
passed (23 each) and the independent native recorder reported zero loss, but
PCAP reported 315/322 kernel drops at robot/operator. The failed plan, child
manifests and logs are retained; that incomplete block is not compared as a
successful observer-cost study. Its appended impairment probes did not run.

Read-only setsockopt tracing on owned diagnostic containers measured the pinned
libpcap immediate-mode ring. With offload support and full snapshots, a 4,096-KiB
request provided only 64 packet slots (65,632 bytes per slot, 8 MiB allocated).
A 32,768-KiB request provided 512 slots (64 MiB allocated). The request is not the
same as the actual allocation. The [pinned libpcap implementation](https://github.com/the-tcpdump-group/libpcap/blob/libpcap-1.10.4/pcap-linux.c)
selects TPACKET_V2 for immediate mode and sizes fixed slots to accommodate offloads.
The trace supports this mechanism; it does not attribute every spontaneous drop
to one specific scheduling pause.

A separate controlled experiment pauses only tcpdump readers, verifies their
Linux stopped/running states, and emits 400 datagrams while native observers and
the application continue. The old ring stores 64 and drops 336 per endpoint;
the larger ring stores all 400 without kernel drops. Both then capture a recovery
control, and native/application observations remain complete. The preload shim
logs setup only, changes no socket options and is absent from normal study runs.
A development pause attempt used host signal numbers across OS boundaries and
is excluded; the verified experiment resolves signal names inside Linux.

Normal runners and the tap fixture now share the bounded 32,768-KiB request,
retaining immediate mode, full snapshots and enabled offloads. Memory/CPU costs
therefore belong to this new configuration. The zero-drop gate remains strict;
larger buffers are not an unlimited scheduling/traffic guarantee. The study
comparison additionally freezes buffer/snapshot configuration. A new frozen plan
uses a fresh directory and this changed configuration; it is not a hidden retry
or replacement of the failed original.

## Comparison guard and preregistration

The study helper now requires immediate PCAP mode and v2/168-byte native records
on opted-in runs. It retains the common VM boot ID and rejects mixed boots,
images, durations, profiles, seeds, cgroup limits or capture modes/versions in
on/off blocks. Selected installed application/worker/capture binaries and the
pinned SRT archive are hashed before execution and checked before/after each
workload, alongside the existing frozen source inventory. This guard prevents
accidentally comparing old v1/buffered results with new v2/immediate results.
It does not freeze the host scheduler, CPU frequency, cache state or other work.

The fresh output directory contains the plan written before the first workload:

- SRT N0 off/on/on/off, four 45-second runs, seed 1701.
- Default DDS N0 on/off/off/on, four 45-second runs, seed 1701.
- SRT and default DDS N1, 60 seconds each, seed 1701, native observer on.
- SRT and default DDS N2, 60 seconds each, seed 1701, native observer on.

`--skip-long-n5` explicitly excludes the three long N5 repetitions from this
plan. Earlier v1 N5 results remain historical; this step does not pretend to
repeat them for v2. N1/N2 normally require 600 seconds and all three seeds;
these 60-second runs are development coverage, not that full-duration matrix.
Existing impairment, command admission/deadline/lease/journal, no-replay,
source-fence and recorder gates are unchanged. Fresh labs execute sequentially,
with no retries or post hoc removal of noisy runs.

The new optional study flags preserve the original default plan while allowing
explicit smaller coverage sets. `--impairment-seconds` appends the four N1/N2
probes. `--skip-long-n5` omits only long N5 cases, not requested impairment cases.
The parent reuses the already installed development binaries; no rebuild occurs
during the frozen run. Normal M3 setup/build remains a prerequisite.

## Measurement interpretation

Source-enabled cgroup CPU differences retain inner/outer observations without
interpolation; they are not strict physical bounds or confidence intervals.
Charged-memory maxima include cache/kernel allocations and are not RSS/PSS or
isolated observer memory. Both modes include the existing endpoint sampler and
immediate tcpdump; "on" adds the BPF observer, its setup state and capability.
Counter units/work outside the container and VM scheduling remain limitations.
Command count/effect comparisons and source/callback populations remain separate.
Negative CPU differences are retained rather than interpreted as free overhead.

Opted-in observations carry GSO/VLAN/MTU metadata. Their frame-interpretation
eligibility does not establish physical transmission/delivery. PCAP written-
record integrity and filter population reconciliation remain independent;
unreconciled populations withhold realtime PCAP windows, while native counters
have separate loss/coverage gates. The previous tap-scope correction still
applies. No existing historical evidence is rewritten.

All twelve changed-configuration runs passed: 299 confirmed commands/effects,
zero unresolved intents, zero PCAP kernel drops and native reserve/copy losses.
DDS N2 skipped five scheduling slots and observed 10.87 s maximum terminal-status
latency; receiver execution latency is a different measure. All 24 closed
journals passed integrity/terminal agreement checks; 48 projected cgroup windows
replay exactly. Host Python tests: 75 passed.

See [results](RESULTS.md), the frozen plan, per-run manifests and source/binary
verification. Raw PCAPs, packet prefixes, clocks and journals stay local with
hashes. Projected cgroup samples preserve exact reanalysis inputs. No new ROS
GTest/full M2 execution is claimed; production C++/SDK/wire/IPC and Intrinsic/M4
remain unchanged.

## Reproduction

After the existing M3 setup, use a fresh directory:

```sh
python3 tools/m3_observer_study.py --out .local/m3-observer-study/v2-new \
  --seconds 45 --skip-long-n5 --impairment-seconds 60
```

Omit the optional flags to retain the original eight N0 plus three long N5 plan.
`--plan-only` writes the selected plan without executing it. Mixed old capture
modes are deliberately rejected by the updated analyzer; historical archived
results remain available under their original measurement definitions.
