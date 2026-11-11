# Combined steady DDS sensor and journaled command workload

`tools/run_m3_dds.py --commands` combines the direct typed Best Effort/Volatile/
KeepLast(1) sensor path with the journaled Reliable DDS coordinator at each
endpoint. The source stays at 200 Hz IMU / 50 Hz six-joint state. Absolute 200 Hz
intents run on a fixed two-second cadence, each with a new ID and next generation.
The simulator preserves source phase when the requested rate stays unchanged.
No SDK, journal, handler, wire or worker IPC implementation changed in this step.
A long run exposed a DDS callback contention bug: delivered frames could be
discarded on a failed try-lock. Received frames now serialize the short session-
validation and task-copy sections, with no disk/handler/network work under those
locks. The queue remains 64 slots; real capacity drops stay counted and local
service admission still returns BUSY on contention. A concurrent-producer test
checks all 64 incoming tasks without contention loss.
Sensor-only invocation remains available without `--commands`.

Both coordinators qualify their common-VM session before the begin fence, and
warmup must contain zero command sends/effects/start claims. The sensor source
is fenced and drained as before. At command cutoff, no new intent is submitted;
already-pending results are observed until at most eight seconds after cutoff.
The command observer freezes then, including while the sensor/final device
snapshot is being collected. Rows identify results observed after cutoff; summary
latencies pool in-load and drain observations. Unresolved attempts are counted
separately, excluded from percentiles, and never treated as failures or successes.
UNKNOWN pauses new work. Missed/busy command slots are counted, with no catch-up
burst and no replay of an old intent.

Runtime offers each free slot through Execute even when coordinator diagnostics
say NOT_READY, recording non-admission explicitly. A pending/UNKNOWN intent still
blocks later work. The source takes a final device fence after result observation. Sensor counts
must still equal the cutoff fence; command effects/generation may have advanced
during drain. Command owner process epochs must be unchanged. The effect audit
checks distinct IDs, matching confirmed results, generation progression and
observed effects between confirmed-success count and potentially admitted intent
count. UNKNOWN/unresolved can have effects; a final snapshot is not a proof of
nonexecution for them. SDK diagnostics retain cumulative 100 ms observation scope
and can lag; they are not an exact command-stage conservation ledger.

The N4 option now uses the same mid-window kernel outage placement as the SRT
harness: initialize/discover under N0, apply 100% loss on owned endpoint egress,
wait a requested two seconds, restore N0 and preserve readbacks. Direction can be
both, robot or operator. Host-observed transition duration is reported; this is
not a precise VM-clock admission/dispatch/result-commit barrier. N0/N1/N2/N5 retain
the same profile, seed, shared-bottleneck and competitor settings as before.

See [results](RESULTS.md), manifests, source verification and test logs. The corrected C++ build and ROS tests are retained; final runs reuse that
recorded binary and match the current 136-file source inventory. Python drivers
were installed and compared byte-for-byte after their final edits. N0 ran with
other development fixtures in the VM, so it is not controlled CPU benchmarking. The new pure workload tests cover
cadence/skip behavior, the 150-slot five-minute schedule, ambiguous effects,
non-admission bounds, duplicate IDs, inconsistent results/generations and cutoff/
drain censoring. Raw captures and journals stay ignored locally, with hashes in
`raw-artifacts.json`; shared files carry laboratory phases and diagnostic source
snapshots, never command execution or journal-result transport.

Sensor age remains a shared-VM realtime-header estimate, with clock steps reported
separately from sensor count validation. It has a different origin/bound from
SRT conservative bridge-ingress age. The DDS coordinator still requires a common
Linux boot/time namespace and has no qualified encryption or peer authentication.
Captures cover the whole UDP Ethernet capture, including discovery/control and
UDP competitor traffic; TCP/ARP and physical-link overhead are excluded. CPU and
wire bytes are not yet aligned to the exact sample window. Reliable middleware
can still encounter counted application callback drops. No lossless admission,
clock/security equivalence, hardware performance advantage or M3 acceptance is
claimed. Full multi-seed impairment durations, N3 selection and N4 command-phase
barriers remain open.
