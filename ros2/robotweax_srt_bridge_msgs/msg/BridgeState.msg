bool ready
bool sensor_qos_verified
bool clock_qualified
uint8 session_state
uint8 fault
uint8 worker_fault
uint8[16] session_id
uint64 control_generation
uint64 sensor_generation
uint64 samples_ingress
uint64 samples_published
uint64 invalid_samples
uint64 oversize_samples
uint64 stale_samples
uint64 context_drops
uint64 imu_sequence
uint64 joint_sequence
uint64 commands_sent
uint64 queries_sent
uint64 peer_errors
# Cumulative counters for this node lifetime. Histogram buckets are ceil(ms).
uint32 max_clock_interval_ms
uint64 transport_samples_received
uint64 transport_samples_rejected
uint64 transport_samples_unknown_age
uint64 transport_samples_stale
uint64 transport_sensor_replaced
uint64 transport_rejected
uint64[251] imu_age_upper_histogram_ms
uint64[251] joint_age_upper_histogram_ms
uint64 imu_age_upper_max_ns
uint64 joint_age_upper_max_ns
# Ingress at typed ROS callbacks, before validation/serialization.
uint64 imu_ingress
uint64 joint_ingress
uint64 samples_submit_busy
uint64 samples_submit_obsolete

# Detailed bounded sensor accounting, cumulative owner lifetime.
uint64 sensor_submitted
uint64 sensor_ingress_replaced
uint64 sensor_ingress_flushed
uint64 sensor_inputs
uint64 sensor_input_rejected
uint64 sensor_outbound_replaced
uint64 sensor_outbound_expired
uint64 sensor_outbound_flushed
uint64 sensor_sent
uint64 sensor_receive_replaced
uint64 sensor_receive_flushed
uint64 sensor_polled
uint64 sensor_poll_expired
uint64 sensor_ingress_pending
uint64 sensor_outbound_pending
uint64 sensor_receive_pending

# Stable across reconnects; changes if this bridge owner is reconstructed.
uint8[16] owner_epoch
