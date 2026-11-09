#pragma once
#include <robotweax/srt_bridge/clock.hpp>
#include <robotweax/srt_bridge/management.hpp>
#include <robotweax/srt_bridge/routes.hpp>

namespace robotweax::srt_bridge {
enum class Role { caller, listener };
enum class SessionState { disconnected, awaiting_hello, awaiting_welcome, synchronizing, control_active, sensor_binding, active, failed, stopped };
enum class SessionError {
    none, invalid_state, bad_security, invalid_identity, bad_peer, manifest_mismatch,
    limits_mismatch, malformed, obsolete_connection, stale_session, epoch_mismatch,
    domain_mismatch, replay, clock_unqualified, clock_invalid, probe_not_pending,
    probe_busy, invalid_time, handshake_timeout, binding_mismatch, binding_timeout,
    wrong_direction, unknown_route, disabled_route, oversize, stale_sample, sequence_exhausted
};
struct Connection {
    Channel channel = Channel::control;
    std::uint64_t generation = 0;
    bool operator==(const Connection&) const = default;
};
// Supplied only after checking the installed provider/profile and negotiated
// socket options. These booleans are evidence from the I/O owner, not peer input.
struct Security {
    Channel profile = Channel::control;
    bool gcm = false, sessionauth_v2 = false, enforced_encryption = false;
};
struct OutboundManagement {
    Connection connection;
    Envelope envelope;
    Management payload;
};
struct SessionAction {
    SessionError error = SessionError::none;
    std::optional<OutboundManagement> send{};
    bool close_control = false, close_sensor = false, flush_samples = false;
};
struct SampleResult {
    SessionAction action;
    std::optional<Envelope> envelope;
    AgeResult age;
    std::uint64_t evaluated_ns=0;
};
struct SessionConfig {
    Role role;
    std::string local_peer_id, expected_peer_id;
    Identity local_epoch;
    std::uint32_t local_clock_domain;
    RouteManifest manifest;
    ClockConfig clock;
    Limits limits{};
};
// Optional stack-only diagnostic output from the existing validated decode.
struct ProbeAdmissionObservation {
    std::uint64_t t1=0,t2=0,t3=0;
    bool fields_available=false,mapper_submitted=false;
    ClockError mapper_result=ClockError::unqualified;
};
// Event-driven, single I/O owner. No sockets, callbacks, queues or locks here.
// Actions carry socket generations so stale queued sends can be discarded.
class Session {
public:
    explicit Session(SessionConfig config);
    Session(const Session&) = delete;
    Session& operator=(const Session&) = delete;
    Session(Session&&) = delete;
    Session& operator=(Session&&) = delete;
    SessionAction control_connected(std::uint64_t generation, Security security, std::uint64_t now,
                                    Identity listener_assigned_session = {});
    SessionAction sensor_connected(std::uint64_t generation, Security security, std::uint64_t now,
                                   Identity caller_binding_id = {});
    SessionAction receive(Connection source, const MessageView& message, std::uint64_t now,ProbeAdmissionObservation* observation=nullptr);
    SessionAction begin_probe(std::uint64_t now);
    SessionAction tick(std::uint64_t now);
    SessionAction control_lost(std::uint64_t generation);
    SessionAction sensor_lost(std::uint64_t generation);
    SessionAction stop();
    bool reactivate();
    SampleResult make_control(Kind kind,std::uint32_t route,Identity request,std::size_t payload_bytes,std::uint64_t origin_ns,std::uint64_t now);
    SampleResult admit_control(Connection source,const MessageView& message,std::uint64_t now);
    SampleResult check_command(const Envelope& command,std::uint64_t now);
    SampleResult make_sample(std::uint32_t route, std::size_t payload_bytes, std::uint64_t now);
    SampleResult admit_sample(Connection source, const MessageView& sample, std::uint64_t now);
    SessionState state() const noexcept;
    const Identity& local_epoch() const noexcept { return config_.local_epoch; }
    const Identity& session_id() const noexcept { return session_id_; }
    std::optional<std::uint64_t> clock_deadline() const noexcept { return clock_.qualification_deadline(); }
    ClockError clock_state() const noexcept { return clock_.state(); }
    ClockObservation clock_observation() const noexcept { return clock_.observation(); }
    std::uint64_t pending_probe_origin() const noexcept { return pending_probe_.value_or(0); }
private:
    SessionConfig config_;
    ClockMapper clock_;
    bool control_up_ = false, remote_known_ = false, local_ready_ = false, peer_ready_ = false;
    bool sensor_up_ = false, bound_ = false, failed_ = false, stopped_ = false;
    std::uint64_t control_generation_ = 0, sensor_generation_ = 0, last_time_ = 0;
    std::uint64_t management_tx_ = 0, control_rx_ = 0, sensor_rx_ = 0;
    std::uint64_t handshake_deadline_ = 0, bind_deadline_ = 0, next_bind_ = 0, last_probe_start_ = 0;
    bool ever_probed_ = false;
    std::optional<std::uint64_t> pending_probe_;
    Identity session_id_{}, last_session_{}, remote_epoch_{}, last_remote_epoch_{};
    Identity binding_id_{}, last_local_binding_{}, last_peer_binding_{};
    std::uint32_t remote_domain_ = 0;
    std::array<std::uint64_t,8> route_tx_{}, route_rx_{};
    bool advance(std::uint64_t now);
    bool control_ready() const noexcept { return control_up_ && local_ready_ && peer_ready_; }
    bool secure(Security evidence, Channel expected) const noexcept;
    SessionAction terminate(SessionError error, bool permanent);
    SessionAction emit(Management payload, Connection destination, std::uint64_t now);
    void bind_remote(const Envelope& envelope);
    SessionError identity(const Envelope& envelope) const noexcept;
    SessionError parameters(const Hello& hello) const noexcept;
    std::size_t route_index(std::uint32_t route) const noexcept;
};
// The I/O owner calls this for process epochs, listener sessions and each new
// caller SENSOR binding. Deterministic test IDs are never production defaults.
Identity random_identity();
}
