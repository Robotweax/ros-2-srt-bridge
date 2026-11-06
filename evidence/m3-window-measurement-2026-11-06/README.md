# Shared SRT/DDS endpoint window accounting — 2026-11-06

Both runners now use the same Linux `/proc` sampler and phase definitions.
This develops measurement infrastructure; M3 and controlled SRT/DDS comparison
remain incomplete. Production C++ sources/binaries and all command gates are
unchanged. SDK wire 1, IPC 3, pinned SRT and Intrinsic/M4 remain unchanged.

## Definition and limits

- `source_enabled`: source resume fence to pause fence. Excludes the later drain.
- `fenced_observation`: operator just before resume request to command drain and
  stable sensor end checkpoint, before teardown. Includes coordination work.
- Nominal 250-ms process-tree samples include source, bridge/control workers and
  test observer/sampler. Capture and competitor CPU are excluded; their host load
  still influences results. Stable `(label,pid,start_ticks)` identities, successful
  reads, monotonic counters, unchanged reaped-child CPU and <=1-s gaps are required.
  Unobserved short-lived children are not covered. Own utime/stime are summed;
  waited-child CPU is a rejection guard, never added again.
- CPU reports observed inner/outer tick deltas without interpolation, divided by
  the exact phase duration for core percentages. They are not strict physical CPU
  bounds: Linux ticks are quantized (10 ms here). RSS is a sampled sum which may
  double-count shared pages, not PSS or a hard allocation peak.
- Per-sample realtime reads are bracketed by monotonic reads. Capture mapping is
  conditional on no hidden realtime step between observations, <=1000 ppm relative
  drift, <=1-ms read/observed-step width and <=1-s gaps. A common offset envelope
  across both endpoints plus drift padding defines timestamp uncertainty.
  Classic microsecond/nanosecond pcap quantization is retained conservatively.
  Inside/boundary/outside bins partition packets and frame classes; inside plus
  boundary supplies a conditional upper frame-byte bound only when qualified.
- Whole-capture integrity, kernel-drop and transport-isolation gates run first.
  Failed clock calibration suppresses windowed bytes. Ethernet lengths exclude
  physical overhead/FCS; egress is pre-qdisc. DDS RTPS/fragments include discovery,
  services and controls; no sensor/source-population or isolated transport cost is
  inferred. Existing whole-run SRT `resources` and capture totals keep their scope.

Linux documents [process stat fields](https://www.kernel.org/doc/html/latest/filesystems/proc.html).
The sampler uses process CPU ticks, start identity and resident pages; its saved
clock frequency/page size make units explicit. Process-read brackets and errors
remain in JSONL for audit.

## Validation

44 Python tests pass, including CPU churn/counter/child-work rejection, clock
failure, drift padding, fragment accounting and micro/nanosecond boundary bins.
The demo package installs successfully. Installed scripts are byte-identical;
five final run manifests each match all 146 recorded source files. Compiled
production inputs and command/simulator binary hashes match historical evidence.
No new ROS GTest/full M2 execution is claimed; those remain historical.

Five sequential live development runs pass: SRT N0 (30 s), default DDS N0 (30 s),
paced DDS N0 (30 s), paced DDS N5 (60 s) and sensor-only default DDS N0 (15 s).
Paced N5 confirms 30/30 commands with valid competition. Every phase at both
endpoints qualifies CPU. **Every live wire mapping is rejected for observed
offset drift beyond the 1000 ppm model**, so `window_captures` stays empty.
See [observations](RESULTS.md) and `clock-rejections.json` for the measured clock
violations. Functional success is separate from resource/clock qualification.
This does not diagnose the underlying emulation/clock cause or justify relaxing
the model. Next work is clock mapping qualification and controlled comparison.

Reprocessing four historical whole-run captures (SRT and DDS, both endpoints)
reproduces every original summary field exactly; fragment opt-in remains DDS-only.
Synthetic tests exercise qualified wire partitioning. No live qualified wire-cost
result is claimed. Two earlier development smoke runs preceded the final stricter
clock checks and are excluded from final results; their references are retained.

Raw PCAPs and journals stay local with sizes/hashes in `raw-artifacts.json`.
Committed manifests/results and endpoint JSONL contain counters/clocks/process
names, no command lines, environment dumps or transport passphrase. Existing
historical evidence is not rewritten.
