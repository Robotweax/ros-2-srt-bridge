# Development baseline: fixed-size Reliable/Volatile control frames, common VM only.
uint8 HELLO=1
uint8 COMMAND=2
uint8 QUERY=3
uint8 STATUS=4
uint8 ERROR=5
# Non-executing, same-session durable absence seal, strictly past original deadline.
uint8 SEAL_EXPIRED=6
uint16 PROTOCOL_VERSION=2
uint8 kind
uint8[16] process_epoch
uint8[16] link_epoch
uint8[16] target_link
uint8[16] session_id
uint8[32] clock_namespace
uint64 sequence
uint64 sent_monotonic_ns
uint64 reply_to_sequence
uint32 route_id
uint8[16] request_id
uint64 origin_monotonic_ns
uint64 deadline_ns
uint32 rate_hz
uint32 budget_ms
uint64 expected_generation
uint64 new_generation
uint8[32] payload_hash
CommandStatus status
# HELLO owner eligibility; never a handler-start grant.
bool owner_ready

uint16 protocol_version
