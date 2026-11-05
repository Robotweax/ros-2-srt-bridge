# M1 acceptance: wire errors and installed SDK — 2026-11-05

M1 is accepted for the documented ROS-independent static Linux amd64 profile.
Request-scoped ERROR diagnostics now make admission/reconciliation failures visible
without changing journal truth. The SDK installs, relocates and runs an external
consumer. The [acceptance matrix](ACCEPTANCE.md) maps M1 requirements to retained
checks. M2 ROS runtime integration is next; no physical device or WAN performance
qualification is implied.

## Reproduction and results

After M0, from the project directory:

```sh
python3 tools/run_m1.py --native
```

| Gate | Result | Evidence |
| --- | --- | --- |
| Linux amd64 Debug core | 15/15 pass | [JUnit](debug.xml), [log](debug.log) |
| Linux amd64 ASan + UBSan core | 15/15 pass | [JUnit](asan-ubsan.xml), [log](asan-ubsan.log) |
| Root with installed SRT | 67/67 pass | [JUnit](native.xml), [log](native.log) |
| Native ASan + UBSan | 10/10 pass | [JUnit](transport-sanitized.xml), [log](transport-sanitized.log) |
| Relocated full Linux SDK consumer | Pass | [Log](installed-consumer.log), [artifact manifest](installed-manifest.json) |
| Missing required SDK component | Expected configuration rejection | [Log](installed-consumer.log) |
| Consumer ROS/second-SRT runtime links | None | [Dependency inventory](installed-manifest.json) |
| macOS arm64 minimal core | 4/4 pass + relocated installed consumer | [Log](host-core-sdk.log) |

[Run manifest](run.json) includes commands, image/provider identities and tested
source hashes; `${PROJECT}` replaces the host path. Fingerprints were verified
against final code, and JUnit counts have no failures, errors or skips. The ERROR
contract passes 22,562 checks, including 20,000 seeded mutations. Each native wire
error family passes 89 checks. The installed manifest fingerprints the released
SDK files. Local runtime databases/binaries stay in ignored build/run directories.

Linux runs use the unchanged M0 image under Docker Desktop amd64 emulation with
network disabled. Bridge and spawned workers are instrumented in sanitizer builds;
the prebuilt SRT archive and system libraries are not. The full upstream SRT suite
was not rerun. No commit, push, dependency upgrade or Intrinsic change was made.

## Diagnostic contract

Kind 11 is now a concrete request-scoped CONTROL ERROR, Caller -> Listener only.
It requires an enabled command route, nonzero request ID, current session, epoch,
domain and connection generation, plus the normal monotonic route sequence.
Route-zero management errors remain unsupported; handshake/identity/replay failures
are dropped or close the channel. ERROR never causes an ERROR response.

`errors_v1.proto` is separate from commands_v1.proto. The existing rate descriptor
hash remains SHA256_5c6bd6e9a81dcc45aca4e17697441eceb280a454bfe72c784b2fcfca840cca98;
a golden contract checks it after generation. The body contains only code, original
COMMAND/QUERY kind and sequence, and a 1..5000 ms retry hint for BUSY/CAPACITY.
There is no free text, device result or journal state. Preflight rejects unknown or
duplicate fields, wrong wire types, malformed/nonminimal/overflowing varints, missing
required values and bodies over 64 bytes before generated parsing. Encoder failures
leave the destination unchanged.

The transport records the latest accepted COMMAND and QUERY sequence per ID/route
in a fixed 64-entry recent-send cache. Unknown, stale or repeated references are
not delivered as peer responses. Standalone users should bound distinct outstanding
IDs accordingly; the endpoint already bounds tracked IDs to 64. Clock expiry does
not block diagnostics, while execution still requires qualified freshness.
CONTROL receive pauses before its own outgoing FIFO is full, preserving bounded
space for selected body/freshness-gate diagnostics. Existing FIFO, reserve and
estimated bandwidth rules still apply.

The endpoint returns BUSY/CAPACITY/CONFLICT/NOT_FOUND for applicable admission/query
errors. The owner can diagnose malformed bodies, stale starts and unqualified clocks
before journal admission. Those pre-admission diagnostics do not reserve the
receiver ID or create a terminal journal tombstone. Actual storage failure remains
fail-closed and may disconnect before sending an error.

## Sender behavior

An accepted diagnostic produces CommandEvent.peer_error and peer_context, with no
authoritative entry. The sender only reads its journal; it does not rewrite
LOCAL_QUEUED/ACCEPTED/UNKNOWN into FAILED, REJECTED or EXPIRED. Automatic queries for
that ID are suspended in the error's session. Explicit query or reconnect resumes
reconciliation, never COMMAND resend. Retry hints do not renew the stored budget.

Known terminal results win over late ERROR. Older command diagnostics also cannot
override a persisted peer admission. A peer STORAGE code remains a remote diagnostic
and does not poison the local journal. An unmatched reference cannot suspend a
campaign. The session token remains attached to events so a client can distinguish
historical diagnostics after reconnect.

## Native evidence

Both IPv4 and IPv6 exercise actual protected sockets and public asynchronous APIs:

- A successful command followed by missing-record and wrong-route queries, a full
  receiver journal and a conflicting payload. Responses identify the original
  request and leave the stored success/device effect unchanged.
- A deliberately independent sender DB generates the conflicting payload; normal
  endpoint ID protection prevents that send. It is a test fixture, not a recovery
  recommendation.
- BUSY suspends automatic querying; explicit query resumes it. Wrong sequence and
  wrong ID responses are rejected. NOT_FOUND ends the automatic query campaign
  observably without claiming nonexecution.
- Reconnect resumes query-first with a new peer epoch/session, retaining the original
  intent and sending no additional COMMAND. Repeating Execute with the same ID
  returns the stored UNKNOWN/reconcile-required state rather than minting a ticket.
- A peer STORAGE diagnostic leaves the local worker healthy.
- An injected well-formed late peer result resolves uncertainty, then a late matched
  error cannot downgrade it. This raw-peer fixture tests precedence and makes no
  physical-effect claim. The separate endpoint/handler tests still verify actual
  simulated effects and durable result commits.

Session/codec contracts also test wrong direction, old session/epoch/domain/socket
and replay, illegal execution TTL, invalid ERROR bodies and delivery after clock
qualification expires. Existing queue, crash, grant-race, lifecycle, profile and
reconnect regressions remain in the root suite.

## SDK acceptance

The package exports core, protocol/management, journal, worker, transport and
endpoint targets as built, plus public headers, protobuf sources and the worker
executable. SRT remains separately installed. The test installs the full static
Linux SDK, renames its prefix, and configures a clean external consumer with package
registries disabled. Installed metadata retains no workspace paths; compilation
uses installed headers rather than bridge source/build includes. The worker target
resolves inside the relocated prefix.

The consumer performs a protected command/result exchange and duplicate suppression.
Its dynamic dependencies contain neither ROS nor a second SRT implementation. A
fresh CMake project requiring an unavailable component is rejected. The manifest
records installed file hashes and runtime dependencies.

The independent macOS core package is configured with BUILD_MANAGEMENT_CODEC=OFF,
installed and relocated. A consumer finds only the core component and performs a
wire roundtrip without SRT/Protobuf/OpenSSL/SQLite/ROS. This does not qualify the full
Linux worker/SDK on macOS.

The successful host commands are recorded in host-core-sdk.log; they use
build/m1-host-errors-sdk, .local/m1/errors-host-prefix-original (renamed to
errors-host-prefix-relocated), and tests/installed/core-only. All artifacts remain
local and reproducible from the source/install instructions.

## Retained development checks and limits

[First complete build](attempts/errors-first-build.log),
[native error tests](attempts/errors-native-first.log) and
[first installed consumer](attempts/errors-install-first.log) passed and are retained.
The final run additionally checks remote storage-error isolation, wrong-ID correlation,
missing required components and runtime dependencies. Raw attempts remain local.

Qualification assumes cooperating authenticated peers, the pinned provider and the
stated clock drift/error bounds. Shared start fences, journal/SIGSTOP/kill tests and
VFS fault injection do not qualify a damaged disk, physical power loss or
uninterruptible kernel I/O. The simulated device resets with its worker; journal
results are historical, and UNKNOWN is never automatically replayed. Network wire
rate estimates are not physical caps. ROS nodes/CDR/QoS/services, WAN measurements
and Intrinsic remain M2, M3 and M4 respectively.
