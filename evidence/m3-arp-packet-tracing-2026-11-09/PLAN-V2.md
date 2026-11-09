# V2 unsigned scope comparison correction

V1 source88ba3f1 N0 FAILED:30 real replies present in both recorders, zero tracer
lifetimes. N5 NOT_EXECUTED. Source and all11 binaries remained frozen; preserve
V1 raw hashes/results and cleanup. This is a failed instrument calibration, not
ARP loss or a product outcome. No retries of V1 or historical cohorts.

Diagnosis after closure: BPF JMP64 sign-extends its32-bit immediate; namespace
inode4026532697 and several Ethernet header words have bit31 set, while LDXW
zero-extends the loaded32-bit field. Equality therefore fails. Use JMP32 only
for comparisons of namespace/ifindex/header words; pointer and64-bit tests remain
JMP64. Add a real kernel BPF regression check showing JMP64 rejects and JMP32
accepts the same high-bit unsigned value. Keep failed verifier preparation too.

Freeze revised source/binary/test evidence before a fresh V2 N0 then N5, once each,
using exactly the PLAN.md stimuli/settings. No product/runtime/default changes,
no tuning. Stop on first failure, retain all captures/censoring. Readiness schema
version2 identifies the correction; record format remains1. All original scope,
classification, population, cleanup and source-verification requirements apply.
