# Explicit same-row SENSOR selector

Development evidence only. M3 remains open and PR #2 remains draft. Neither
synthetic header generation nor forwarding proves authenticated SRT/FEC recovery.

The prospective plan and code were frozen in `6990da6`. Exactly two fresh owned
Docker fixtures ran once, one per planned selection. All 163 host tests and Python
syntax checks passed before measurement. No SDK/ROS runtime was changed or rebuilt.
The immutable image reference and original outputs are in `result.json`; source
hashes match the frozen commit in `source-provenance.json`.

| Case | Source positions | Selected transmissions dropped | Receiver/native/PCAP known identities including restore | Kernel drops |
| --- | --- | --- | --- | --- |
| One source | 3 | 2 | 11 at each endpoint and receiver | 0 |
| Two sources | 2, 3 | 3 | 10 at each endpoint and receiver | 0 |

Each case sent 12 synthetic public SRT headers, followed by one send after selector
removal. The repeated selected identity sets the retransmit flag: it is also
removed, rather than exhausting a packet-count budget. This is a selector check,
not an assertion that SENSOR retransmissions occur. The parity header has message
number zero and exactly the selected last source's sequence. It was preserved.
SRT CONTROL, another row, another destination socket, another message number,
CONTROL port traffic and another source port were also preserved. Exact identities
match in receiver output and both native/PCAP observations. Standalone final
footers reconcile file/captured/filter counts, native reserve/copy failures are
zero, the bounded drain returns stable equality, and interface features are
unchanged. The restored send uses the previously selected identity and arrives.
Original filter readbacks and gact counters are retained, including filter removal.

`tools/m3_sensor_fault.py` requires an explicit initial sequence, first-half row
index, one/two distinct positions in the four-source row, nonzero message numbers,
destination socket and SENSOR UDP tuple. It never treats the first observed DATA
as a row origin. It matches fixed-IHL unfragmented IPv4, exact peer addresses,
ports, full sequence (excluding SRT CONTROL), message-number bits and socket ID.
Parity message zero cannot match. Existing classifier hooks are refused. Partial
installation failure removes the newly owned hook. This is opt-in tooling and is
not wired into `run_m3 --profile N3`.

The local pinned provider (`.deps/srt/src/fec.cpp`, `unwrap_sequence`,
`RowFecEncoder::feed_source`, `finish_group`) establishes the source-origin-relative
four-column grouping and last-source-sequence/message-zero parity convention.
No decryption, authentication, receiver FEC repair, sensor publication age or ROS
command behavior is inferred from these synthetic packets. The known packet header
fixture is distinct from encrypted/authenticated production traffic. Tests cover
sequence wrap in the selector, but the finite live fixtures do not cross wrap.

Next: obtain trusted live sender origin/row/message/socket identity before arming,
then run separately planned one/two loss cases with authenticated parity and
receiver repair/rejection counters plus the existing capture/accounting guards.
Do not enable N3 on a guessed first observation. N4 command-phase barriers, prior
N5/PCAP failures, the historical unresolved command and all other M3 gates remain
open; no earlier failed cohort is replaced.

Raw captures remain under `.local/m3-sensor-selector/`; their hashes are retained.
The archive excludes payload captures, credentials, full container inspect and
environment dumps. Network changes occurred only in disposable owned containers.
