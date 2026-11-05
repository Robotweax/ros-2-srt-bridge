bool ready
bool journal_ready
bool failed
uint8[16] process_epoch
uint8[16] link_epoch
uint8[16] session_id
uint64 commands_sent
uint64 queries_sent
uint64 dispatches
uint64 start_claims
uint64 inbox_drops
uint64 rejected_frames
uint64 journal_errors
uint64 effects
uint64 hellos_sent
uint64 hellos_received
uint64 hellos_rejected
uint64 lease_expirations
uint64 control_subscribers
uint64 control_publishers
uint64 last_peer_hello_ns
uint8[16] peer_link_epoch
uint8[16] hello_target
uint64 hello_subscribers
uint64 hello_publishers
bool qos_verified
bool handler_ready
bool peer_ready
# Session validation only, after kind/route/request-ID checks; first failure wins.
# Indices: accepted, session, peer, clock namespace, sequence, invalid time, stale.
uint64[7] control_checks
uint64 stale_commands
uint8[16] last_stale_command_id
uint64 last_stale_command_sent_ns
uint64 last_stale_command_received_ns
# Sender receipt-matched ERROR/not_found responses, not local polling snapshots.
uint64 remote_not_found
# Reliable publish call wall duration; excludes queue time before/after that call.
uint64 control_publish_max_ns
uint64 control_publish_over_freshness
# Protocol-v2 reconciliation; distinct from executable COMMAND and read-only QUERY.
uint64 expiry_seals_sent
uint64 expiry_seals_received
uint64 expiry_seals_inserted
uint64 expiry_seals_existing
uint64 expiry_seals_rejected
