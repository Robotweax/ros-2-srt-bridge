# Contribution guidance and dependency notice preparation

[Contribution guide](../../CONTRIBUTING.md) and [dependency notices](../../THIRD_PARTY.md) prepare the current private source repository for a later publication decision. The notices separate direct SDK dependencies, declared ROS packages and selected development tools from a complete binary/image distribution inventory. No binaries, images, dependency implementations or upstream package manifests are added.

sources.json records exact upstream license-reference commits and Git blob identities; each file was read again at the resolved commit and matched the observed ref. ROS/DDS/test reference revisions are not new build pins. SQLite's official copyright page was reviewed separately. inputs.json binds the local CMake/manifests/container recipes and existing SRT license/provenance files used for this assessment.

review.json records the PR7 review/merge and preservation boundary. verification.json records documentation/link/scope/secret-scan checks. hashes.json binds this separate evidence package and the new guidance documents; the mutable README is not bound. Earlier reports, evidence indexes, baselines and acceptance documents remain untouched.

Repository visibility remains private. M3 acceptance keeps its exact simulator/build scope, historical failures, intent 118 UNKNOWN and limitations. Intrinsic stays paused with PR1 draft/unmerged and M4 disabled. No build, campaign, experiment, tuning or publication is performed by this preparation.
