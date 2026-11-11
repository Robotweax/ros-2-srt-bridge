# ROS 2 SRT Bridge

A C++20 bridge SDK and ROS 2 Jazzy packages for typed IMU/joint-state telemetry and durable measurement-rate commands over Robotweax SRT.

SENSOR uses bounded, latest-sample queues with freshness checks. CONTROL uses a durable command journal, generation checks and query-first recovery. The included simulator applies measurement-rate changes; physical-device effects are outside the accepted scope.

## Current status

- **M3 accepted within its documented simulator/build scope:** 38 distinct planned case IDs have passing evidence across separate freezes and harness revisions. Historical failures and intent 118 UNKNOWN remain preserved.
- [PR2](https://github.com/Robotweax/ros-2-srt-bridge/pull/2), [MIT licensing PR4](https://github.com/Robotweax/ros-2-srt-bridge/pull/4) and [disclosure-review PR5](https://github.com/Robotweax/ros-2-srt-bridge/pull/5) are merged.
- The repository remains private. The owner chose to [retain the reviewed history and evidence](PUBLICATION_RETENTION_DECISION.md). The [wiki review](PUBLICATION_WIKI_REVIEW.md) confirmed no existing pages. The [final source-publication readiness review](PUBLICATION_READINESS_REVIEW.md) found no blockers within its documented scope; publication still requires an explicit owner decision and a current hosted-surface check.
- **Intrinsic integration is paused.** Its separate repository and draft PR1 do not provide runtime qualification or an active M4 implementation.

Start with the [formal M3 decision](M3_ACCEPTANCE_DECISION.md), [scoped acceptance](M3_SCOPED_ACCEPTANCE.md) and [disclosure review](PUBLICATION_DISCLOSURE_REVIEW.md). Acceptance applies to the exact retained simulator/build artifacts. New builds have their own provenance and do not inherit that qualification.

## Packages and components

| Component | Purpose |
|---|---|
| Standalone CMake SDK | Wire/clock/budget/reconnect core; management protocol, journal, supervised Linux worker, transport and command endpoint |
| `robotweax_srt_bridge_msgs` | Bounded command/status messages and services |
| `robotweax_srt_bridge` | ROS telemetry adapters and rate worker; also contains the separate DDS comparison executable |
| `robotweax_srt_bridge_demo` | Synthetic sensor/rate simulator and retained scenario tooling |

The full SDK/ROS path targets Linux amd64 with Ubuntu 24.04 and ROS 2 Jazzy. The dependency-free core can also be built separately, including on macOS arm64. The installed transport dependency is [Robotweax SRT](https://github.com/Robotweax/srt) at commit `52be7c86ee1f303cbb0c8718c364217e4dd97a36`, with the namespaced package and GCM API enabled.

See [ARCHITECTURE.md](ARCHITECTURE.md) for route/type/QoS, freshness, command and lifecycle contracts.

## Fresh-clone build

The [build guide](docs/BUILDING.md) covers:

1. A portable core build and its offline contract tests.
2. A clean build/install of the pinned SRT dependency and full bridge SDK.
3. A ROS Jazzy package build using those fresh install prefixes.

These steps do not depend on a sibling SDK checkout or locally qualified image tags. The guide distinguishes build verification from execution and M3 qualification; it does not start a simulator or campaign.

## Using the installed SDK

Require the components your application uses:

```cmake
find_package(RobotweaxBridge 0.1 CONFIG REQUIRED COMPONENTS endpoint worker_runtime)
target_link_libraries(my_bridge_node PRIVATE RobotweaxBridge::endpoint)
```

Available components depend on build options: `core`, `protocol` (`management` alias), `journal`, `worker`, `worker_runtime`, `transport` and `endpoint`. The installed `RobotweaxBridge::journal_worker` target identifies the supervised worker executable. Missing required components fail configuration.

Keep the SDK install prefix available to the ROS executables: their SDK worker path is bound when they are built. Configure peer identities, routes, credentials and worker paths for the intended deployment before execution. Credentials are external inputs; do not commit passphrases or private keys.

## Evidence and limitations

The accepted tests demonstrate the documented simulator contracts, including conservative UNKNOWN outcomes. They do not establish physical-robot safety, production-WAN behavior, cross-host clock guarantees, hard real-time execution, continuous availability, general security certification or SRT superiority over DDS. N5 cadence/skipped-slot and comparison limits remain attached to acceptance.

`tools/run_m0.py` through `tools/run_m3.py` are retained qualification/development harnesses with historical environment assumptions. Some start containers, scenarios and network impairments. Ordinary fresh-clone build instructions are in [docs/BUILDING.md](docs/BUILDING.md); new qualification campaigns require their own reviewed inputs and authorization.

Historical implementation chronology remains available in the [pre-publication README](https://github.com/Robotweax/ros-2-srt-bridge/blob/a29f8564494e3433315fb1638d069df8b1e32fe4/README.md), [HANDOFF.md](HANDOFF.md) and [acceptance consolidation](evidence/m3-acceptance-consolidation-2026-11-11/README.md). Treat their dated status statements as historical records.

## Maintainer and support

Maintained by **Robotweax GmbH** — [info@robotweax.ai](mailto:info@robotweax.ai), the same public contact used by the [Robotweax SRT repository](https://github.com/Robotweax/srt/blob/532fd6fe7648546c50a5f49b50f791718ec08fb9/SECURITY.md).

Use [GitHub Issues](https://github.com/Robotweax/ros-2-srt-bridge/issues) for general questions and reproducible bugs. Email suspected security issues privately with the subject `ROS 2 SRT Bridge security report`; include the affected commit and a minimal reproducer, with secrets and confidential payloads removed. Do not put sensitive reports or credentials in public issues.

See [CONTRIBUTING.md](CONTRIBUTING.md) for changes, verification and evidence preservation, and [THIRD_PARTY.md](THIRD_PARTY.md) for dependency licenses and distribution boundaries.

## License

[MIT](LICENSE), copyright 2026 Robotweax GmbH and contributors. [Third-party dependencies](THIRD_PARTY.md) retain their respective licenses.
