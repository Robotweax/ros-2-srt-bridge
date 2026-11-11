# Missing robot socket-close markers: retained diagnosis — 2026-11-10

**The stage gate requires markers unconditionally that the source emits only
conditionally. The retained robot trace is consistent with already-invalid link
slots at local shutdown, not a missing outer cleanup path.** The exact earlier
close trigger/time/result is unobserved. The previous diagnostic remains FAIL;
this analysis does not waive it, qualify M3 or identify the original bridge hang.

No workload, observer, bridge, capture, test fixture, build or Docker operation
was run. No source/harness/filter/gate/runtime change, tuning, original-case
retry, expiry/replay or new experiment. All29 remaining campaign cases remain
disabled; M3 open, PR2 draft, M4 untouched.

## Source-established contract mismatch

In [transport.cpp](../../src/robotweax_srt_bridge_core/src/transport/transport.cpp),
close_fd at lines223–231 does nothing for SRT_INVALID_SOCK. For a valid handle,
it removes the epoll socket and calls srt_close, then invalidates the slot.
The socket_epoll_remove_begin/socket_close_begin/socket_close_end markers each
require stopping or shutting_down. Ordinary earlier link-loss/connection cleanup
uses the same helper with both flags false and produces no shutdown-stage marker.
The srt_close return value is not recorded or checked by these markers.

Local final cleanup sets shutting_down before session.stop, then always emits
CONTROL/SENSOR begin/end around close_fd for each link and listener. Epoll,
provider and thread completion follow. A caller creates no listener sockets;
its listener slots stay invalid. Therefore entering these outer boundaries does
not imply any still-valid handle exists to produce inner socket-close markers.
Other direct temporary/rejected-socket close paths also are not lifetime tracing.

The [stage assessor](../m3-shutdown-live-calibration-2026-11-09/calibrate.py) requires
socket_close_begin/end for every healthy role without testing handle ownership
or earlier closure. That requirement is stronger than the instrumentation
contract. No mandatory-presence rule was changed in this diagnosis.

## Retained comparison and timeline

After removing only the three conditional per-fd markers, all eight role traces
have exactly the same39-record point multiset, contiguous sequence populations
and zero reported dropped_before. Counts below are observations, not new runs.

| Retained capture | Operator records / close triplets | Robot records / close triplets |
|---|---:|---:|
| Original enabled calibration | 51 / 4 | 42 / 1 |
| Initial N0 bridge diagnostic | 51 / 4 | 39 / 0 |
| Capability-name correction | 51 / 4 | 39 / 0 |
| Explicit worker lifecycle | 51 / 4 | 39 / 0 |

The last robot trace reaches both session-stop boundaries, CONTROL/SENSOR
begin/end, epoll release, provider cleanup, transport/endpoint join, node reset
and main_context_shutdown_end. No socket triplets were attempted in that trace's
contiguous39 sequence population. With the same source/trace object and completed
final paths, already-invalid slots are the source-supported explanation. This is
an inference about adapter slot state, not a captured FD inventory or proof that
every underlying close succeeded and no unrelated handle leaked.

Latest shared-monotonic timeline:

| Event | Monotonic ns |
|---|---:|
| Operator bridge SIGINT begins | 31,095,331,722 |
| Last operator socket_close_end | 31,119,523,430 |
| Robot source reaped | 31,266,105,055 |
| Robot bridge SIGINT begins | 31,266,139,055 |
| Robot transport shutdown begins | 31,280,543,847 |
| Robot CONTROL final-close begin | 31,280,990,430 |
| Robot SENSOR final-close end | 31,281,238,763 |

The operator finishes its socket-close calls146.615625ms before robot SIGINT.
The robot scenario deliberately stops/reaps its source before signalling its
bridge (reverse child order). The peer-first interval permits the still-running
robot transport to observe link loss and invoke lost/apply/drop/close_fd before
its own stopping flag. That path explains why the last locally traced sweep
can have no valid handles. It is strongly consistent with the timeline, but the
exact epoll/socket/provider/session trigger is not recorded here. An earlier
calibration retaining one close triplet demonstrates a different owned-handle
state, not a guarantee that every caller must emit one.

## Observation limits and next corrective scope

The last robot ready metrics are27,790,434,388ns; its sample trace ends at
25,525,464,178ns. Both measurement packet captures stop before operator SIGINT
(robot stop-before29,999,485,972ns). The final robot endpoint process sample ends
30,944,188,055ns, also before peer shutdown; those samples contain process/resource
information, not socket-slot transitions. Command/provider close diagnostics
were disabled, and the stack observer targets only the operator. Consequently
there is no robot per-fd before/after state or srt_close outcome during the
peer-first interval. No packet, syscall or specific error cause can be invented.

A future narrowly scoped diagnostic correction should distinguish a valid fd
being closed from an already-invalid slot at each unconditional final boundary,
retain fd/channel/phase/identity and actual close outcome where available, and
fail missing or inconsistent disposition evidence. Source/mock controls should
cover valid close, preclosed caller, listener-owned handles and omitted/failed
records. This would align an explicit gate with an explicit trace contract;
simply deleting required markers or accepting any absent pair would conceal
real observation gaps. Nothing is implemented, rebuilt, scheduled or executed
by this recommendation. No runtime tuning is indicated by the marker absence.

## Integrity and status

analyze.py reads only existing files and recomputes the comparison/timing/bounds.
report.json separates established facts, source-supported inference and unknowns;
inputs-sha256 binds all source/closed reports consumed. postflight verifies all13
matched entries/preserved build chain, latest source/input freeze and previous
raw indexes, including latest116 raw files. The transport source also matches
the original shutdown-build freeze. No archived evidence or runtime byte changed.
Prior484 tests are historical validation; no tests/build were rerun for analysis.
Original N3 remains8 PASS/1 FAIL/unknown hang cause; latest N0 diagnostic remains
FAIL at its frozen stage gate. All29 later campaign cases stay disabled.
