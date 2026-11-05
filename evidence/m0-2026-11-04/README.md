# M0 qualification and initial M1 codec — 2026-11-04

M0's selected local gates passed. This evidence concerns a Linux amd64 container
under Docker Desktop emulation on Darwin arm64. It does not include an impaired
network experiment, a ROS bridge node, an application command execution, or an
Intrinsic runtime. M1 is in progress; only the wire codec and initial schema exist.

## Qualified inputs

- SRT: clean source `52be7c86ee1f303cbb0c8718c364217e4dd97a36`, version 0.3.1.
- Installed static package: `RobotweaxSRT::srt`, namespaced headers and archive,
  OpenSSL backend, GCM preview enabled, experimental ACP1/controllers/filters off.
- Development image: local immutable repository digest in
  [dependencies.json](../../baselines/dependencies.json); built from the pinned
  Ubuntu 24.04 base using [m0.Dockerfile](../../containers/m0.Dockerfile).
- ROS image: `ros@sha256:8eed0a4669bbf43ee331878a4c39bd8ebddea8e3312a58b4fae8edb14526b617`,
  platform linux/amd64, Jazzy, `rmw_fastrtps_cpp`.
- Full installed package inventories are in [baselines](../../baselines/).
  The local image digest pins the tested build; rebuilding apt packages requires
  a new recorded baseline. No development image was pushed to a registry.

## Results

| Gate | Result | Artifact |
| --- | --- | --- |
| Installed-library profile matrix | 40/40 CTest cases pass | [JUnit](profile-probe.xml) |
| Upstream GCM profiles | Four CTest partitions pass | [JUnit](upstream-profile.xml) |
| Upstream SESSIONAUTH admission | One CTest partition passes | [JUnit](upstream-admission.xml) |
| Focused native SESSIONAUTH | 15/15, no skips | [Native log](session-auth-native.log) |
| ROS type hashes and CDR bounds | Pass | [Probe output](ros-type-output.json) |
| Initial M1 codec, GNU 13.3 Debug | Pass | [Final Linux log](core-final.log) |
| Initial M1 codec, ASan + UBSan | Pass | [Final Linux log](core-final.log) |
| Standalone core, macOS arm64 | Pass | [Host log](core-host.log) |

The 40-case matrix contains four normal exchanges, four close-under-backpressure
cases, and 32 negative cases. Both profiles use IPv4/MSS 1500 and IPv6/MSS 1280.
The probe checks every setter, both peers' GCM/session-auth/encryption options,
secured send/receive key states before DATA, finite buffers, and zero linger.
It transfers 16 exact bidirectional messages per positive/pressure case:
4,096 bytes for CONTROL and 1,024 bytes for SENSOR. SENSOR 1,025-byte sends and
CONTROL finite TTL are rejected. Empty reads return EASYNCRCV and epoll times out.
The pressure cases reach EASYNCSND before close; explicit socket closure must
complete within two seconds, with a 12-second CTest process limit.

Wrong profiles, wrong/missing secrets, missing GCM and missing SESSIONAUTH fail
without acceptance. Profile/GCM/SESSIONAUTH mismatches are tested with each end
as the incompatible party. Random per-process test credentials are never printed.
SESSIONAUTH v2 follows from the clean pinned implementation and ACP1 being off;
there is no public API claiming to report a negotiated SESSIONAUTH version.

Actual SRT buffer readback: 262,016 bytes at IPv4/MSS 1500 and 261,668 bytes at
IPv6/MSS 1280, for both send and receive; flow window 256 packets. UDP buffer
options read back 262,144 bytes. Kernel memory accounting may include additional
overhead. These are probe settings, not a future bridge's completed queue model.

ROS probe bounds are a 64-byte frame ID, six joints, 64-byte joint names, and
six entries in position/velocity/effort. CDR including encapsulation occupies
380 bytes for Imu and 684 bytes for JointState. With the 96-byte envelope the
messages occupy 476 and 780 bytes, below 1,024. Both type hashes are nonzero
RIHS01 values. Round trips preserve the messages; an intentionally large valid
JointState exceeds the budget. Runtime route/type/UTF-8/size gates remain M2 work.

## M1 codec scope and validation

The codec freezes the 96-byte offsets and kind IDs, uses network byte order,
returns a borrowed payload view without peer-sized allocation, and rejects
unknown versions/kinds/flags, nonzero reserved bits, length mismatches, wrong
channels/routes, invalid request IDs and oversized messages. Encode failures
leave the destination unchanged. SAMPLE and BIND require zero request IDs;
COMMAND/STATUS/QUERY require nonzero request IDs. These are structural checks;
session authorization, epochs, monotonic sequence/freshness and protobuf payload
validation are not implemented yet.

Tests include an independently packed [golden vector](../../tests/protocol/sample-v1.hex),
all truncated header lengths, boundary payloads, in-place encoding, every kind,
malformed fields, and 20,000 mutations with seed `0x52575342`. The final test run
reports 22,576 assertions. Sanitizer build flags were
`-fsanitize=address,undefined -fno-omit-frame-pointer` in Debug on Linux amd64.
The standalone root build command is documented in the [README](../../README.md).
The management schema also compiled successfully with Protobuf 3.21.12:

```sh
protoc --proto_path=proto --descriptor_set_out=.local/m0/management-v1.pb proto/management_v1.proto
```

The schema defines initial management payloads. Protobuf's byte/string fields
are not intrinsically bounded; runtime bounds and state validation are pending.

## Reproduction and evidence integrity

Run `python3 tools/run_m0.py --build-image --srt-source ..` after pulling the
pinned ROS image, as documented in the README. The runner rejects a dirty/wrong
SRT source, resolves images by immutable repository digest, inventories tests,
requires every selected native case to execute without skips, and saves each
attempt to a distinct ignored `.local/m0/` directory. Selected scope is deliberate;
the complete upstream suite was built but was not run.

[run.json](run.json) records the successful commands and image/library identities;
`${PROJECT}` replaces the local absolute project path in this portable copy.
Its input-baseline hash refers to the manifest before promotion of the successful
run. [source-sha256.json](source-sha256.json) fingerprints the implementation and
qualification tools associated with this evidence. The source has not been
committed or pushed, so there is no bridge commit ID yet.

Earlier attempts remain in `.local/m0/`. An initial dependency build was stopped
to raise parallelism from two to six jobs. One runner attempt failed before tests
because a Docker platform-manifest ID was not a runnable local image reference;
using the repository digest fixed it. The failed attempt's portable manifest is
[retained](initial-image-resolution-failure.json). Initial test results and raw
build logs were not overwritten.
