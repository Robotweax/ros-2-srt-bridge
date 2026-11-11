# Standalone participant-listener status-mask fix

The third no-loss baseline (2fe1737) still FAILED and its fault case was skipped.
Both readers have unread history1, callbacks0, deserialize0, no sample rejection.
The native probe's DomainParticipantListener was installed with StatusMask::all().
Its inherited empty DATA_ON_READERS handler takes precedence over the per-reader
DATA_AVAILABLE handler, leaving the sample unread. This is a fixture listener
configuration defect, not a demonstrated defect in original ROS/RMW or a cause
of the historical N5 failure.

Fast DDS2.14 DataReaderImpl first dispatches DATA_ON_READERS via its subscriber/
participant listener, otherwise DATA_AVAILABLE to the reader listener. Source:
https://raw.githubusercontent.com/eProsima/Fast-DDS/v2.14.5/src/cpp/fastdds/subscriber/DataReaderImpl.cpp
(lines847..875). The installed runtime result remains the local validation gate.

Register the fixture participant listener with StatusMask::none(), leaving its
vendor participant-discovery callback and the reader/writer status listeners
intact. Keep wire, QoS, metadata, locators, callback-only taking and all original
acceptance/deadline gates unchanged. No polling fallback or manual notification.
Run one new baseline, then the originally planned fragment-cut only if baseline
passes, in a distinct directory. Preserve all3 earlier failed baselines and their
unexecuted fault cases. No production binary or default change; native fixture
ELF rebuilt with new source/binary provenance. Corrected baseline must demonstrate
actual reader callbacks and deserialization before fragment evidence is accepted.
