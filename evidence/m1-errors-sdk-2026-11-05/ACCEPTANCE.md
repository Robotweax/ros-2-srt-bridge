# M1 acceptance matrix — 2026-11-05

**Accepted:** ROS-independent core on the pinned static Linux amd64 development
profile. The [machine-readable baseline](../../baselines/m1-acceptance.json) binds
this decision to the final tested source inventory, provider archive and image.
This is a local qualification, not a published release or hardware certification.

| M1 requirement | Passing evidence |
| --- | --- |
| Separate installed provider, no enclosing SRT edits | Unchanged M0 image/archive guard in [run manifest](run.json); clean `.deps/srt` check |
| Fixed 96-byte envelope, limits, unknown fields/flags/routes | wire_contract golden + 20,000 mutations, [Debug JUnit](debug.xml) |
| Canonical shared route manifest and hash | routes_contract golden and validation, [Debug JUnit](debug.xml) |
| Protected CONTROL handshake and peer/manifest/security gates | session_contract + 40 installed-provider profile cases, [root JUnit](native.xml) |
| SENSOR binding, nonce/generation/epoch handling and rebind | session_contract and session_sockets_ipv4/ipv6, [root JUnit](native.xml) |
| Conservative clock mapping and qualification expiry | clock_contract + 5,000 drift scenarios, integer boundaries and absolute qualification limit, [sanitizer JUnit](asan-ubsan.xml) |
| Latest-only SENSOR and bounded FIFO CONTROL with reserve | queues_contract, seeded overload traces, source sequence/expiry native checks, [root JUnit](native.xml) |
| Shared estimated bandwidth admission and bounded reconnect | bandwidth_contract, reconnect_contract and transport_owner cases, [root JUnit](native.xml) |
| Durable sender/receiver admission, dispatch and results | journal_contract, worker_contract, command_endpoint cases, [root JUnit](native.xml) |
| Crash/uncertain-result recovery, no blind resend | journal_crash_contract and worker commit barriers; endpoint restart/query-first tests, [root JUnit](native.xml) |
| Bounded journal and disk-error behavior | journal_quota_contract, capacity/preallocated completion and injected write/sync errors, [Debug JUnit](debug.xml) |
| Handler starts fenced against revocation/expiry | execution_contract (5,000 races), execution_start_ipv4/ipv6, [native sanitizer JUnit](transport-sanitized.xml) |
| Lifecycle separate from network, bounded stop | transport_owner, worker_contract, command_endpoint timeout/SIGSTOP/concurrent-producer/full-mailbox cases, [root JUnit](native.xml) |
| ERROR observable without fabricated execution truth | error_contract + wire_errors_ipv4/ipv6, [native sanitizer JUnit](transport-sanitized.xml) |
| No ROS required for core; consumable installed SDK | [relocated external consumer](installed-consumer.log), [manifest](installed-manifest.json), [portable-core installed consumer](host-core-sdk.log) |

Final gates: Debug **15/15**, core ASan+UBSan **15/15**, root **67/67**, native
ASan+UBSan **10/10**, installed Linux SDK/negative component/link checks **pass**,
macOS minimal core **4/4** plus relocated consumer **pass**. JUnit contains no failed,
errored or skipped cases. Source fingerprints match the final code.

The SRT counterparts run over real protected loopback sockets in one harness process;
journal/rate-handler workers are separate exec processes. This proves the stated
core contracts and stop/recovery cases, not cross-host WAN behavior. The full
upstream SRT suite was not rerun. Sanitizer instrumentation covers bridge/worker
code, not the prebuilt provider/system libraries. Static Linux amd64 is the qualified
full SDK profile; only minimal core is qualified on macOS arm64.

M2 must now add actual ROS Jazzy nodes in separate domains, CDR/type/hash/size/QoS
gates, ExecuteCommand/GetCommandStatus and an external simulator effect/result
flow. M3 owns WAN impairment/performance comparison; M4 owns Intrinsic integration.
