# Post-run fenced callback and packet recheck

The corrected5ba20c1 pair PASSES both originally planned cases. Their original
result.json files remain unchanged. An added offline gate counts fresh callbacks
only through the recorded three-second steady VM end fence, excluding shutdown
tails: baseline30/30 and fragment-cut33/33, still above the original>=20 gate.
The live report's broader counts are retained separately, never overwritten.
A regression rejects callbacks after the fence.

Closed-capture follow-up uses the same qualified filter-before-bind packet
populations, pinned tshark4.2.2 and submessage-scoped parser. Bind the fixture's
known28-byte CDR type by actual original writer GUID, exact magic/role/sequence/
origin and payload hash. Require matching full-run HELLO identity sets at both
taps. For the fault case, select all robot HELLO origins between VM hold begin
and removal begin, require>=20 matching identities at each tap and>=20 observed
before the first complete robot publication advertisement in operator PCAP order.
This is encoded origin plus observed file order, not a realtime-PCAP arrival
latency or proof every selected DATA arrived before filter removal.

No new live execution, parameter change, rewritten verdict or original-capture
mutation. The separate native wire type remains a diagnostic, not production
DdsCommandFrame. Preserve partial/discovery/callback distinctions and historical
ROS/N5 uncertainty. All host tests261 pass before the closed-capture analysis.
