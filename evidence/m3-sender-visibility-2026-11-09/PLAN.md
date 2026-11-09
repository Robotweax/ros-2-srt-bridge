# Sender clock and reconciliation visibility

Add default-off sender_diagnostics requiring CommandTrace. Preserve all decisions,
budgets, timeouts, proof claims, queue capacities and worker/wire formats. The
owner records first clock deferral and recovery before envelope admission, using
the actual existing check's state, probe anchor/offset interval and original
command identity/deadline. No second check or invented qualification deadline.
Record pending input releases with their branch, including flush, separately from
outbound/SDK handoff. Coordinator records worker journal completions and emitted
local events, including explicit absent entries and peer errors. No new receipt
channel, callback or journal mutation; trace observations cannot reconcile state.

Build SDK/ROS in new sender-visibility prefixes. Preserve both installed baseline
and matched start-trace binaries, provider checkout/archive and historical raw
evidence. No loaded run, retry of stopped seed4211, intent118 submission, forced
expiry or policy change. PR2 draft, M3 open, Intrinsic unchanged.

Validation: fixed snapshot/serialization/parser contracts, lossy/drop handling,
enabled/disabled guards, and one fresh successful loopback command per IPv4/IPv6
with enabled and disabled diagnostics. Fresh random IDs and journals only; no
network fault, pause, short lease or expiry case is added. Existing SDK/ROS suites
may include their established synthetic failure tests; these are not runs of118.
Use a deterministic ClockMapper-only fixture to distinguish unqualified versus
expired snapshots; it submits no command and changes no production parameters.
Preserve failed build/test logs and report limits. No heavy test/build overlaps
any live capture. Archive build/test outputs, calibration traces and source/binary
hashes; reject malformed or absent new observations when explicitly enabled.
