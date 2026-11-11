# Clock offset diagnosis and sampling correction — 2026-11-06

This step identifies a measurement gap and tightens calibration. It does not make
this VM suitable for controlled wire-cost comparisons. Command execution gates,
production C++ sources/binaries, SDK wire 1, IPC 3 and Intrinsic/M4 are unchanged.

## Observation and correction

Earlier rejected endpoint samples showed approximately 30-second-spaced offset
changes. A 95-second read-only diagnostic reproduced two excessive changes through
both libc and direct `clock_gettime` syscalls, and one through Python. All 910 raw
and boottime offset samples stayed within the tested model. Native minimum offset
changes were about 108 and 137 microseconds across roughly 107 and 100 ms brackets.
The diagnostic exits 2, meaning observed realtime-model failure, not tool failure.

This localizes the observation beyond the Python endpoint sampler. It does not
identify a VM synchronization agent or prove an underlying kernel implementation
fault: all calls run through the emulated amd64 Linux environment. Read-only
`adjtimex(modes=0)` reported state 5/status 64 (TIME_ERROR/STA_UNSYNC), zero reported
frequency/offset and no status changes. This alone neither identifies the clock
setter nor proves constant offsets.

Linux documents that [realtime can jump while monotonic resists such jumps](https://www.man7.org/linux/man-pages/man2/clock_gettime.2.html).
The [adjtimex interface](https://man7.org/linux/man-pages/man2/adjtimex.2.html)
explains the read-only query and synchronization status. No clocks or time-sync
settings were changed; the native probe ran without network or capabilities.

The old 250-ms process scan cadence could miss a short offset change. A synthetic
150-us step passes the coarse model but fails the same 1000-ppm model at 50 ms.
Clock reads now run independently at scenario polls with minimum 25-ms spacing;
process scans remain at 250 ms. Current runners require dedicated clock JSONL and
reject gaps over 100 ms, with no fallback to sparse process-clock samples. The
analysis helper preserves explicitly labelled legacy reanalysis for historical
artifacts. The drift/step/read-width model is not relaxed.

**Faster finite sampling still cannot guarantee no hidden steps.** A passing
probe does not qualify later workloads. Production sensor age/command clocks and
all safety gates are unchanged. Future qualified comparison needs a supported
stable clock environment or a verified monotonic packet-timestamp path.

## Reproduction

From this repository root with the already pinned lab image:

```sh
mkdir -p .local/clock-diagnosis
docker run --rm --pull=never --platform linux/amd64 --network none --cap-drop ALL \
  -v "$PWD:/workspace" -w /workspace ros2-srt-m3:20261105 bash -c \
  'g++ -std=c++20 -O2 -Wall -Wextra -Wpedantic -Werror tools/clock_probe/main.cpp -o .local/clock-diagnosis/clock_probe && python3 tools/m3_clock_probe.py --native .local/clock-diagnosis/clock_probe --seconds 95 --out .local/clock-diagnosis/idle'
```

Choose a fresh output directory; existing directories are never overwritten.
Exit 0 means no violation was observed in this finite diagnostic, 2 means a
realtime-model violation was observed; other failures retain partial samples and
an error. Probe binary/source hashes, compiler/environment and image identity
are recorded. It is a lab tool, never linked into bridge/simulator.

## Validation and evidence

51 Python tests pass, including correlated/isolated clock failures, malformed
brackets, independent clock/process sampling, aliasing, strict gaps and missing
clock-file rejection. The demo package installs successfully. See [live results](RESULTS.md)
for final SRT/DDS development checks, strict-versus-legacy evaluations and source
verification. No new ROS GTest/full M2 execution is claimed. Historical evidence
remains unchanged. Raw PCAPs/journals remain local with recorded hashes/sizes.

The first three development reruns used the older cadence and are excluded from
final results. Their references and qualifications are retained separately.
The native rejection precedes the first development SRT source-enabled interval;
it is not presented as a counterexample inside that interval. The final live
SRT series provides a direct coarse-versus-dedicated comparison in one phase.
