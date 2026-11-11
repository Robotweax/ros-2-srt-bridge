# Explicit paced DDS N5, current capture configuration — 2026-11-06

This frozen cohort requests three 300-second repetitions with base seeds 1701,
2903 and 4211, fresh sequential owned endpoints and simultaneous startup. It uses
`--dds-profile paced-sensors`, not system/default DDS. The known default-DDS N5
cold-discovery failure remains open; passing this tuned candidate cannot repair
or qualify the default profile. Full SRT N5 is separate remaining work.

N5 applies a shared 512-kbit/s root TBF in each direction (4,096-byte burst,
32,768-byte limit), a child 16-packet netem queue and a live UDP competitor from
robot to operator targeting 128,000 bits/s, 1,024-byte blocks. Whole-run offered
load and process liveness are validated; these are not matched-window competitor
delivery/loss proofs. Direction seeds are base/base+1. N5 configures no stochastic
loss/jitter; seeds label repetitions rather than three random impairment samples.
Actual TC arguments/readbacks are retained. The pinned iproute JSON exposes TBF
rate/burst and normalized latency rather than an explicit limit field; the
32,768-byte limit request remains in the successful TC arguments. No fabricated
limit readback is added. No host qdisc or published ports.

## Explicit profile and measurement scope

The two sensor writers use asynchronous publication, Best Effort/Volatile/
KeepLast(1) and a shared 1,600-controller-byte/50-ms flow budget inside their
participant, with 1,200-byte UDPv4/SHM packetization. Controls retain Reliable/
Volatile/KeepLast(64), synchronous/default-controller behavior; independent HELLO
liveness remains unchanged. There is no control-first publication hold, discovery
server bypass or network priority. Fewer sensor callbacks are expected. Configured
200/50-Hz production, source/callback counts and middleware replacement remain
separate from isolated WAN loss or a global Ethernet bandwidth cap.

Every child runs the existing native provider preflight in a separate network-none
container, verifying applied participant/controller and sensor/control settings
without warming measured discovery. The frozen inventory covers its binary as
well as eight selected application/worker/capture/SDK hashes. XML/source hashes
and installed demo Python bytes remain constant; no rebuild or runtime/policy
change occurs. Main captures use native v2, immediate/full snapshots, a 32,768-KiB
buffer request and sixteen 16-MB rotating files (256,000,000 nominal bytes).
Historical v1/buffered and smaller-retention measurements remain separate.

Commands target absolute 200-Hz rate changes every two seconds, one pending intent.
Busy work skips slots, UNKNOWN pauses new intents, and no automatic replay is
introduced. Admission, deadlines/leases, atomic handler claim, durable journal,
status correlation and original-session absence seals remain unchanged. Success,
expiry, nonadmission, UNKNOWN and unresolved records are distinct. Missing or
NOT_FOUND alone is not nonexecution; final generation checks withhold claims
across uncertainty. Closed original-owner success timelines use timestamps
sampled before journal mutations/commits, not fsync completion or handler start.

PCAP zero-kernel-drop/captured-file-integrity gates stay strict. Filter population
reconciliation is independent and required alongside clock qualification for
realtime packet windows. Native kernel-monotonic coverage/loss is separate;
GSO/VLAN/MTU interpretation does not establish physical frames/delivery/checksum/
FCS or wire overhead. Age estimates use shared-VM realtime Header time, not SRT's
conservative bridge-ingress clock bounds. Source/callback populations, tuning,
security and shared emulated host prevent an SRT/DDS performance-advantage claim.

## Reproduction

After existing M3 setup, run each seed in a fresh lab:

```sh
python3 tools/run_m3_dds.py --commands --dds-profile paced-sensors \
  --profile N5 --seed 1701 --seconds 300 --skip-build --monotonic-capture
```

Repeat with 2903 and 4211. The archived orchestration freezes the plan before
execution, checks sources/installed bytes around each child and stops on failure.
No retry, replacement or post hoc removal is allowed. Raw PCAPs, prefixes,
journals, clocks and sampler files remain local with hashes; only selected
inspect capability/namespace fields are published. All three current-capture repetitions passed: 450 confirmed commands/effects,
no expiry/UNKNOWN/unresolved/nonadmitted/skipped intents, six agreeing journals
and twelve exactly replayed cgroup windows. Native profile preflights, competitor
offered-load/liveness and recorder gates passed. Shared-VM age estimates qualified;
realtime packet windows remained withheld.
See [results](RESULTS.md) and study.json for full populations and limits.
The previous 83-test suite is unchanged; no new ROS GTest/full M2 build is claimed.
M3 and PR #2 remain in progress/draft; Intrinsic/M4 is unchanged.
