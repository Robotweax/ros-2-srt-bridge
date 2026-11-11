# Isolated sustained-source preflight (2026-11-08)

Before any live run: exactly one ten-second window, output
`.local/m3-source-preflight/1`, via `python3 tools/m3_source_preflight.py
--output .local/m3-source-preflight/1`. No fault, no retry, no bridge, no SDK/FEC
or network capture. Docker Linux amd64 emulation, pinned existing image; network
none, ROS domain90 / localhost. Source starts disabled, waits for local discovery,
resumes once, pauses once, then drains typed observation for two seconds.

Source: existing phase-preserving C++ timer, IMU200Hz and joints50Hz. New default-off
source_diagnostics buffers at most10000 logical payloads and timing records;
SHA256 and JSON output happen after the serialized pause fence. Payload encoding
matches independent Python goldens. Enabling diagnostics adds bounded source
work/storage; this is an instrumented source preflight, no resource comparison.

Required: complete one-window source status, zero diagnostic drops/encoding/hash
failures, unique route/stamp, contiguous per-route counters, exact pause counts,
phase-preserving due sequence including explicit skipped slots, all publication
brackets within resume/pause. No source rate/effect change. Measured full-window
counts/duration must be within1% of200/50Hz individually; requested periods or
short-interval medians do not qualify cadence. Report every skipped slot.
Typed observer rows must match source stamp/hash, order and uniqueness. Retain
all unobserved source IDs as explicit local observation gaps; do not call them
transport successes or assign unmeasured per-ID loss stages. Observer completeness
is reported separately from the cadence gate. A failed run stays failed and
requires a separate plan before another live measurement.

Run only after host/ROS tests pass and this source/plan is committed. Record
source commit, pinned image, simulator hash before/after. Preserve logs, typed
hashes, trace and original verdict. No credentials are involved. This does not
qualify bridge admission accounting, sustained multiroute N3, packet capture,
FEC/loss, physical source age, N4 or M3; those remain subsequent work.
