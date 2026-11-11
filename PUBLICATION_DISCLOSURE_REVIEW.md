# Publication disclosure review — 2026-11-11

**PR4 is reviewed and merged; the repository remains private. This disclosure review found no confirmed service credentials in the inspected surfaces. Public release is not authorized or cleared by this report.** Owner decisions on metadata/history disclosure and a wiki check remain open. Intrinsic integration is paused and its PR1 remains draft/unmerged.

Reviewed bridge source: `00d01e1cdb146e268bdd529dea251744f9f04735`, the merge of [MIT licensing PR4](https://github.com/Robotweax/ros-2-srt-bridge/pull/4). The PR changed 12 license/metadata/install files. Review found no blocking issues; package-local licenses and XML declarations match the public SDK license. Prior SDK license-component installation validation applies. No hosted checks were reported and no full ROS build was claimed.

## Scope and method

The [evidence package](evidence/publication-disclosure-2026-11-11/README.md) records the scanned refs, scanner identity, findings/triage, binary analysis and preservation checks. This is disclosure analysis, not a runtime security audit, new build qualification or an M3 campaign.

- Fetch/prune of published branches/tags and explicit read-only fetches of all four PR heads established the local review population. The ref union contains 264 reachable commits; Gitleaks reports 259 commits processed by its Git-diff scan. The difference is three merges identical to a reviewed parent tree, one empty root commit and one binary-only journal commit covered by the binary audit. [Coverage proof](evidence/publication-disclosure-2026-11-11/patch-scan-coverage.json).
- Gitleaks v8.30.1 ran offline against history, an exact Git archive of the reviewed tree, commit messages/author metadata, repository/PR text, extracted SQLite values, and printable strings from identified historical binary blobs. Its official Darwin ARM64 archive and checksum manifest matched their GitHub release SHA-256 values before use. The scanner stayed in ignored .local storage.
- Scans used bundled default rules, no finding baseline, an empty external ignore location, disabled inline allow-comment suppression and 100% output redaction. No service credential validation, login attempt, journal recovery, traffic, container launch or experiment occurred. Scanner default allowlists/decoders and the limitations below still apply.

## Credential findings and triage

| Surface | Scanner result | Reviewed disposition |
|---|---:|---|
| Reachable Git history | 418 generic-api-key candidates; scanner exit 1 retained | 406 ephemeral launch-correlation IDs; 12 source-file SHA-256 digests |
| Exact reviewed tree | 418 generic-api-key candidates; scanner exit 1 retained | Same category counts, independently matched to file/line/JSON context |
| Reachable commit messages and author/committer metadata | 0 candidates | Identity metadata still needs a privacy decision |
| Repository metadata and all four PR titles/bodies | 0 candidates | No credential identified in these recorded texts |
| SQLite logical values, including BLOB representations | 0 candidates | No credential identified; binary format reviewed separately |
| Printable ASCII strings from identified historical binaries | 0 candidates | No credential identified within this extraction scope |

Every candidate is retained in [candidate-triage.json](evidence/publication-disclosure-2026-11-11/candidate-triage.json) without candidate values. Nothing was suppressed through a committed allowlist or re-labelled as a zero-finding scanner run.

The 32-hex token/launch_token values occur in launch-registration, capability-attestation and shutdown-identity records. [new_launch](evidence/m3-current-n0-lifecycle-stabilization-2026-11-10/launch_readiness.py) generates a fresh correlation value; its consumers bind local PID/start-time/readiness evidence. These are historical local launch identifiers, not service API credentials. The other matches are 64-hex source digests under the srt_api.cpp artifact keys. Structural checks covered all reported occurrences in their original historical blobs and the current tree; a keyword or length alone was not used to dismiss them.

"No confirmed credential" is not proof that unknown secrets, encrypted content or an unrecognized credential format are absent. No credentials were rotated because none was confirmed. The ledger omits Secret/Match values but retains source-relative finding filenames, including historical correlation IDs in some names. Private author-email values and workstation usernames are not copied into this report.

## Retained binary evidence

All 22 binary blobs identified by the review's NUL-byte heuristic were inspected as 18 SQLite journals and four calibration capture files. The [binary summary](evidence/publication-disclosure-2026-11-11/binary-review.json) records their object identities and hashes.

The 18 journal versions passed read-only integrity checks. Their only tables are entries and identity, with 3,744 entries plus 18 identity rows. Identities are the simulator roles operator/robot. Entries match the existing fixed 512-byte RWJ1 rate-command format: route 100, stored state succeeded and command rate 200 Hz, with expected reserved bytes zero. There is no variable text/payload column in this format. These are the selected committed simulator proofs, not every historical journal or evidence of physical effects. Historical intent 118 UNKNOWN remains unchanged elsewhere in the record.

Logical row extraction and raw binary printable-string scanning are complementary; they do not provide exhaustive deleted-page, encrypted-content, UTF-16 or arbitrary-format forensics. Original journals were not opened through the application's recovery/write APIs. All analysis used immutable/read-only copies.

The four files belong to the retained N0/1701/10s SDK/ROS calibration. Each PCAP has 5,658 IPv4 UDP packets on the SRT ports, entirely between the two recorded lab peers. The monotonic files have 5,673/5,674 prefix records and also contain ARP and IPv6 headers. Their timestamps, addresses, MACs, protocol metadata and packet bytes/prefixes are part of the disclosure surface. No application-payload decryption or blanket payload-confidentiality claim was made. See [capture summary](evidence/publication-disclosure-2026-11-11/capture-review.json).

## Metadata and privacy decisions

The reviewed tree contains 14,121 files, about 534 MB uncompressed; 13,746 evidence files account for about 531 MB. Size alone is not a confidentiality finding.

| Disclosure class | Observed population | Decision before public visibility |
|---|---|---|
| Workstation paths | 451 files contain /Users/... paths | Decide whether the existing machine/user/workspace metadata may be public |
| Private test-network addresses | 949 files contain private IPv4 addresses; 14 distinct values | Mostly Docker/test topology, not credentials; retain deliberately rather than claiming all network details were removed |
| Git identity metadata | Three distinct author/committer email values across reachable history, including a personal email domain | Confirm publication of the existing identity metadata; fixing a package contact would not remove Git history |
| Journals and captures | 18 journal versions and four small capture files | Confirm retention of these reviewed synthetic test proofs and their metadata |
| Historical M4 proposal | Closed/unmerged PR3 and its reachable head include Intrinsic planning and integration-repository references | Pausing Intrinsic work does not hide its historical proposal if the bridge repository becomes public |

The exact private inventory is saved **locally only** at `.local/disclosure-review-2026-11-11/owner-private-inventory.json`, excluded from Git. It contains the concrete author-email, workstation-root and private-address values for the owner's review, not live credentials.

**Preservation rule:** do not redact or overwrite hash-bound M3 evidence to make these decisions disappear. The owner can approve disclosure of the existing reviewed metadata/history. If some material must remain confidential, keep the original private and prepare a separate, explicitly scoped public export with provenance and approved evidence. Any history rewrite, export or publication requires a separate concrete decision; none occurred here.

## GitHub-hosted surfaces

At review time: two published branches, no tags, four PRs and no standalone issues; no issue comments, inline review comments or submitted reviews; no Actions runs/artifacts or release assets. Discussions are disabled. Both API inventories and counts are recorded in [remote-surfaces.json](evidence/publication-disclosure-2026-11-11/remote-surfaces.json).

Wiki capability is enabled, but the authenticated wiki Git endpoint returned “repository not found.” No wiki refs/content were obtained. An owner UI check remains required; this response is not treated as a complete wiki absence proof.

GitHub secret scanning, push protection and validity checks are disabled. The alerts endpoint returned 404 explicitly because scanning is disabled; this is not a zero-alert security result. No settings were changed or scopes expanded. The local scan is not represented as GitHub provider validation.

GitHub documents that repository visibility changes expose Actions history/logs and that secret scanning has its own coverage and access requirements. Re-inventory remote surfaces immediately before any eventual visibility change; this report does not cover future additions. Sources: [visibility consequences](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/managing-repository-settings/setting-repository-visibility), [secret scanning](https://docs.github.com/en/code-security/concepts/secret-security/secret-scanning), [Gitleaks release](https://github.com/gitleaks/gitleaks/releases/tag/v8.30.1).

## Preservation and next step

The complete pre-review evidence and baselines Git trees are identical to the accepted PR2 merge, as are the eight protected root acceptance/planning documents. Working-tree checks passed. No failed verdict, UNKNOWN, limitation, hash index or journal was modified; no old freeze was rebound to the licensing or disclosure revision. [Preservation proof](evidence/publication-disclosure-2026-11-11/preservation.json).

The next publication decision is whether the reviewed metadata and full development history may be public, plus confirmation of wiki state. The remaining publication-preparation work also includes an accurate current README, valid maintainer contact, clean-clone build instructions/verification, contribution/security reporting guidance and dependency notices. Those are separate from this completed scanner-candidate triage.

**Repository visibility remains private. M3 remains accepted only in its documented simulator/build scope. Intrinsic work remains paused, its PR1 stays draft, and no merge of this review or public release is authorized.**
