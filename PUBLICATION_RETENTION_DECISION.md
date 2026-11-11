# Publication retention decision — 2026-11-11

The owner explicitly chose to **retain the reviewed history and evidence** after [disclosure-review PR5](https://github.com/Robotweax/ros-2-srt-bridge/pull/5) was reviewed and merged. This supersedes the pending owner decisions in the dated [disclosure report](PUBLICATION_DISCLOSURE_REVIEW.md) for its reviewed population only.

The retained population includes the reviewed workstation paths, synthetic/private test-network metadata, existing author/committer identities, simulator journals/captures and dated M4 proposal. Original failure verdicts, intent 118 UNKNOWN, acceptance limits, hashes and Git provenance remain unchanged. No redaction, deletion, history rewrite, journal recovery or reclassification is authorized or performed by this decision.

The owner also instructed that the public maintainer email match [Robotweax SRT](https://github.com/Robotweax/srt). Its [published security policy](https://github.com/Robotweax/srt/blob/532fd6fe7648546c50a5f49b50f791718ec08fb9/SECURITY.md) provides **info@robotweax.ai**. The bridge README and three ROS manifests use that company address; no personal commit address is substituted.

The new README is a current entry point. The full previous README remains available at [the pre-publication commit](https://github.com/Robotweax/ros-2-srt-bridge/blob/a29f8564494e3433315fb1638d069df8b1e32fe4/README.md); hash-bound evidence and protected acceptance/handoff documents are untouched. [Fresh-clone build instructions](docs/BUILDING.md) describe separate build verification rather than an M3 campaign.

**The repository stays private.** Retention is not a public-release or visibility-change authorization, a security certification or an extension of M3's accepted simulator/build scope. The wiki absence/content check remains open because no wiki content was obtained in the review. Future source, metadata and artifacts require their own disclosure review.

Intrinsic integration remains paused, with its PR1 draft/unmerged and no implementation, runtime setup or experiment authorized.

[Decision/source/validation records](evidence/publication-docs-2026-11-11/README.md) are separate from the historical M3 packages.
