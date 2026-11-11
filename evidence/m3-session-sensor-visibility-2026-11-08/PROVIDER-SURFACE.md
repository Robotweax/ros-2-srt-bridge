# Targeted existing SENSOR provider surface

No dependency modification. The C API layout and library remain pinned to
52be7c86ee1f303cbb0c8718c364217e4dd97a36 / archive
3fa56e487e6c6408d9e41779d18aba9ff866978892ddbe3b88ac12fc51141673.
Reads call srt_bstats(fd,&stats,0): no interval clearing, same owner thread as I/O.
Read brackets are local VM monotonic; provider work/mutex overhead is not removed.

`--sensor-provider-diagnostics` enables an independent default-off stream, fixed
128-row SPSC storage,75000-record cap,100ms nominal cadence and before-close read.
It carries actual SENSOR fd/generation, local process owner/current session label,
state before/after and availability/error. Availability means a statistics call
succeeded, not healthy/connected state. A zero session during teardown cannot
associate the old socket with a new logical session. Missing/no-ready/error rows
are unavailable; their default field values are not zero-valued measurements.
Footer/schema/channel/population/loss/budget checks are mandatory; loss/exhaustion
invalidates diagnostic completeness. Existing CONTROL stream/CLI is unchanged.

| SENSOR field | Existing SRT_TRACEBSTATS source | Interpretation limit |
|---|---|---|
| data_sent/received | pktSentTotal/pktRecvTotal | Provider DATA-path counts, including filter semantics; not API messages or complete raw UDP counts |
| unique_sent/received | pktSentUniqueTotal/pktRecvUniqueTotal | Unique provider packets; receive includes accepted FEC supply; not typed SAMPLE delivery |
| sender_loss/receiver_loss | pktSndLossTotal/pktRcvLossTotal | Provider loss observations, not uniquely physical drops |
| sender_drop/receiver_drop | pktSndDropTotal/pktRcvDropTotal | Aggregate TTL/TLPKTDROP/gap/peer retirement/decrypt paths as applicable, not reason-isolated events |
| undecrypt | pktRcvUndecryptTotal | Observed provider undecryptable DATA; included in aggregate receive drop, never sum as independent loss |
| sender_filter_extra/receiver_filter_extra | pktSndFilterExtraTotal/pktRcvFilterExtraTotal | Repair/control filter activity, separate from source packets |
| receiver_filter_supply/loss | pktRcvFilterSupplyTotal/pktRcvFilterLossTotal | Recovery candidates supplied/missing source accounting; not guaranteed application recovery |
| send/receive buffer packets/bytes | pktSndBuf/byteSndBuf/pktRcvBuf/byteRcvBuf | Smoothed provider bookkeeping gauges, not exact instantaneous queue lengths |
| flow/congestion window, flight | pktFlowWindow/pktCongestionWindow/pktFlightSize | Gauges; no subtraction as counters |
| RTT | msRTT | Zero need not be an estimate; no application/wire latency claim |

32-bit cumulative loss/drop/filter/retransmit/ACK/NAK/undecrypt counters can
saturate. Report saturation; flat counters then cannot exclude further events.
No interpolation across unavailable reads, process/socket/generation resets or
application-window boundaries. Closed analysis reports lifetime last counters and
separate fully-contained adjacent-read increments, with their actual brackets.
Partial increments omit gaps/tails and are not exact application-window totals.

Read-only source contracts: .deps/srt/src/compat/statistics.cpp populates the
public fields; transport_runtime.cpp records unique acceptance and accepted FEC
supply, undecrypt/drop and receiver gap expiry. Existing API does **not** expose
per-insertion rejection/window-boundary reasons, applied retirement vs gap-expiry
reasons, per-message application delivery, encrypted typed mapping or exact terminal
break reason/last peer activity. Those dimensions remain explicitly unavailable;
aggregate zeroes or captured cleartext DROP_REQUEST cannot fill them in.

Drop counters can retire packets already transmitted or observed. Sender/receiver
drops are overlapping provider accounting, not exclusive path-loss categories;
never subtract them from unique sent or add them to the application gap.
