# Contributing

Report reproducible bugs and discuss proposed changes through [GitHub Issues](https://github.com/Robotweax/ros-2-srt-bridge/issues). The source repository is public under the MIT license. Maintainer contact: [info@robotweax.ai](mailto:info@robotweax.ai).

## Scope and preparation

Read the [README](README.md), [architecture](ARCHITECTURE.md), [fresh-clone build guide](docs/BUILDING.md) and [scoped M3 acceptance](M3_SCOPED_ACCEPTANCE.md) before changing contracts. M3 qualifies the exact retained simulator/build artifacts only. Physical-robot safety, production networks, hard real-time behavior and general security certification are outside that acceptance. Intrinsic integration is paused; its draft plan is not an active implementation task.

Use a focused branch, normally named `dev/<topic>`, from current main. Open a PR from a fork, or use a same-repository branch if you already have write access. Do not put access tokens in Git URLs or commit credentials.

Submit work you have the right to contribute under the [MIT license](LICENSE). Identify third-party origins and retain their applicable notices. Do not copy dependency implementation code into bridge files without a specific provenance/license review. Update [dependency notices](THIRD_PARTY.md) when a dependency or its distribution boundary changes.

## Changes and verification

Keep wire/type/version, freshness, bounded queue, clock, generation, journal and lifecycle contracts explicit. Explain compatibility changes, failure handling and conservative UNKNOWN outcomes. Preserve the distinction between a durable result and a physical-device effect.

Use the build guide for separate empty build/install prefixes and the pinned SRT dependency. Run the existing offline tests relevant to the change and add a regression for changed behavior when useful. For core changes, the guide's portable configuration runs five contract tests. For SDK or ROS changes, select the matching installed-dependency build and relevant tests; the guide's full build disables tests and package discovery alone does not verify behavior. Inspect selected test commands before execution: some native tests spawn workers or exercise crash handling.

Python regression tests live under tests/; many use unittest and some require installed ROS packages. Select tests appropriate to the changed module instead of assuming every test is dependency-free. Documentation-only changes normally need link, command-syntax, scope and whitespace checks rather than a runtime campaign. Report commands, source/dependency versions, results and any checks not run.

Qualification harnesses such as tools/run_m0.py through tools/run_m3.py can create containers, launch scenarios, alter network namespaces and impair traffic. A normal build or PR is not permission to run a campaign. Agree the inputs, execution scope, stop gates and evidence destination with the maintainer before any live qualification. No automatic retries, host/network tuning or M4 work are implied by this guide.

## Evidence and disclosure

Treat accepted baselines and existing evidence packages as historical records. Do not overwrite old captures, journals, hashes, failure verdicts or acceptance statements to describe a new run. Keep historical failures and intent 118 UNKNOWN intact. New validation belongs in a separate dated evidence package with exact source/build identity and explicit limitations; it does not inherit M3 acceptance automatically.

Review new logs, captures and PR attachments for secrets, personal data and deployment metadata before committing or uploading them. Keep raw credentials, keys and operational journals in ignored local storage. The owner's [retention decision](PUBLICATION_RETENTION_DECISION.md) covers the previously reviewed history/evidence, not future uploads. [Disclosure review](PUBLICATION_DISCLOSURE_REVIEW.md) and [wiki review](PUBLICATION_WIKI_REVIEW.md) retain their point-in-time scope.

## Pull requests

Describe the concrete problem, resulting behavior, compatibility impact and validation. Include the relevant source/dependency identity and any remaining limitations. Keep unrelated generated files, build/install trees, raw run output and local settings out of the diff. Run `git diff --check` and review the complete staged diff before submitting.

Open the PR as a draft while work or validation is incomplete. Maintainer review governs merge and release decisions. Public source availability does not authorize publishing binary SDKs, ROS bundles or container images; those require a separate release decision and the applicable dependency notices.

## Security reports

Email suspected vulnerabilities privately to [info@robotweax.ai](mailto:info@robotweax.ai) with subject `ROS 2 SRT Bridge security report`. Include the affected commit, relevant versions, impact and a minimal reproducer with secrets/confidential payloads removed. Do not post sensitive reports, keys or credentials in public issues. No response-time or supported-version guarantee is implied.
