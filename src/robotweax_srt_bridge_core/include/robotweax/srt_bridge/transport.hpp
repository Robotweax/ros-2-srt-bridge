#pragma once
#include <robotweax/srt_bridge/commands.hpp>
#include <robotweax/srt_bridge/ticket.hpp>
#include <robotweax/srt_bridge/execution.hpp>
#include <robotweax/srt_bridge/errors.hpp>
#include <robotweax/srt_bridge/bandwidth.hpp>
#include <robotweax/srt_bridge/reconnect.hpp>
#include <robotweax/srt_bridge/command_trace.hpp>
#include <robotweax/srt_bridge/provider_diagnostics.hpp>
#include <robotweax/srt_bridge/sample_trace.hpp>
#include <robotweax/srt_bridge/session.hpp>
#include <memory>

namespace robotweax::srt_bridge {
struct Endpoint { std::string address; std::uint16_t port=0; };
struct TransportConfig {
    SessionConfig session;
    Endpoint control,sensor; // Numeric IPv4/IPv6, same family. Listener may use port zero.
    std::string passphrase;
    BandwidthConfig bandwidth{1000000,128000,131072,16384,65536};
    std::shared_ptr<CommandTrace> command_trace{}; // Opt-in, lossy diagnostics only.
    std::shared_ptr<ProviderDiagnostics> provider_diagnostics{}; // CONTROL only; non-clearing SDK reads add observer work.
    std::shared_ptr<SampleTrace> sample_trace{}; // Opt-in ROS admission / SENSOR SDK handoff observations.
    std::shared_ptr<ProviderDiagnostics> sensor_provider_diagnostics{}; // Independent opt-in SENSOR SDK reads.
    bool start_diagnostics=false; // Requires command_trace; bounded start-stage observations.
    bool sender_diagnostics=false; // Requires command_trace; no outcome/replay authority.
};
struct TransportContext {
    Identity session{};
    std::uint64_t control_generation=0,sensor_generation=0;
    bool operator==(const TransportContext&) const = default;
};
enum class SubmitResult { queued,busy,stopped,invalid,obsolete };
enum class TransportFault { none,configuration,provider,io,protocol,internal };
struct TransportSnapshot {
    SessionState state=SessionState::disconnected;
    TransportContext context{};
    std::uint16_t control_port=0,sensor_port=0;
    RetryState control_retry=RetryState::idle,sensor_retry=RetryState::idle;
    TransportFault fault=TransportFault::none;
    bool running=false,clock_qualified=false;
    std::uint64_t clock_deadline_ns=0;
    std::size_t control_ingress=0,control_received=0;
    std::uint64_t received=0,sent=0,rejected=0,stale_work=0,sensor_replaced=0;
    std::uint64_t errors_sent=0,errors_received=0,unmatched_errors=0;
    std::uint64_t sensor_submitted=0,sensor_ingress_replaced=0,sensor_ingress_flushed=0,sensor_inputs=0,sensor_input_rejected=0,sensor_outbound_replaced=0,sensor_outbound_expired=0,sensor_outbound_flushed=0,sensor_sent=0,sensor_receive_replaced=0,sensor_receive_flushed=0,sensor_polled=0,sensor_poll_expired=0,sensor_ingress_pending=0,sensor_outbound_pending=0,sensor_receive_pending=0;
    std::uint64_t samples_received=0,samples_rejected=0,samples_unknown_age=0,samples_stale=0;
};
struct TransportMessage {
    TransportContext context{};
    Envelope envelope{};
    std::array<std::byte,control_message_bytes-envelope_bytes> payload{};
    std::size_t size=0;
    std::uint64_t evaluated_ns=0,deadline_ns=0,publication_epoch=0;
    bool expiry_only=false; // Verified stale COMMAND: journal/status only, never dispatch.
    std::span<const std::byte> body() const noexcept { return {payload.data(),size}; }
};
struct CommandCheck {
    std::uint64_t token=0,evaluated_ns=0,deadline_ns=0;
    TransportContext context{};
    SessionError error=SessionError::invalid_state;
    bool start_granted=false;
    std::uint32_t grant_slot=UINT32_MAX;
    std::uint64_t grant_generation=0,clock_deadline_ns=0;
    bool fresh() const noexcept { return error==SessionError::none; }
};
// One thread exclusively owns all provider sockets/epoll, Session, outbound
// queues, budget and retry plans. No user callbacks, journal I/O or handlers run
// on that thread. External submit methods try-lock bounded storage, never wait
// for the network. queued means volatile mailbox admission only.
class TransportOwner {
public:
    explicit TransportOwner(TransportConfig config);
    ~TransportOwner();
    TransportOwner(const TransportOwner&)=delete;
    TransportOwner& operator=(const TransportOwner&)=delete;
    SubmitResult submit_sample(TransportContext context,std::uint32_t route,
                               std::span<const std::byte> payload,std::uint64_t ingress_ns);
    SubmitResult submit_query(TransportContext context,std::uint32_t route,Identity request);
    // Trusted worker integration must supply only durably committed status.
    SubmitResult submit_status(TransportContext context,std::uint32_t route,Identity request,const CommandStatus& status);
    SubmitResult submit_error(TransportContext context,std::uint32_t route,Identity request,const ControlError& error);
    // Only a newly committed sender-worker admission can supply this ticket.
    // BUSY leaves it usable; QUEUED consumes it once. No receiver execution grant.
    SubmitResult submit_command(TransportContext context,DurableCommandTicket&& ticket);
    // CONTROL is FIFO (64); samples latest-only per route. Poll copies ownership.
    // Sample deadlines are rechecked at poll. Consumers must still recheck before
    // deferred publication. Neither poll method authorizes command execution.
    // Bounded asynchronous freshness observation by the Session owner. Use
    // before/after dispatch commit. A reply is a point-in-time check, not a
    // transferable execution grant: final handler fencing is still required.
    SubmitResult request_command_check(TransportContext context,const Envelope& command,std::uint64_t token);
    // Durable dispatch proof + owner freshness -> one shared atomic start fence.
    // The same worker must still consume it before deadline/session revocation.
    SubmitResult request_command_start(TransportContext context,const Envelope& command,DispatchTicket& ticket,std::uint64_t token);
    bool poll_command_check(CommandCheck& check);
    bool poll_control(TransportMessage& message);
    bool poll_sample(TransportMessage& message);
    // Immediate local publication boundary; revocation after this check may
    // complete an already-started publish. Call only after bounded decoding.
    bool authorize_sample(const TransportMessage& message) const;
    TransportSnapshot snapshot() const;
    void request_stop() noexcept;
    void join(); // External lifecycle owner only; idempotent, not concurrent.
    static std::uint64_t monotonic_ns() noexcept;
private:
    struct Impl;
    std::unique_ptr<Impl> impl_;
};
}
