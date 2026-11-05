#pragma once
#include <robotweax/srt_bridge/transport.hpp>
#include <robotweax/srt_bridge/worker.hpp>

namespace robotweax::srt_bridge {
enum class EndpointFault { none,worker,transport,protocol,capacity,timeout,shutdown_timeout,internal };
struct CommandEvent {
    Identity request_id{};
    std::uint32_t route=0;
    JournalError error=JournalError::none;
    std::optional<JournalEntry> entry{};
    // Peer diagnostics have no authoritative entry and never mutate the journal.
    std::optional<ControlError> peer_error{};
    TransportContext peer_context{};
};
struct EndpointSnapshot {
    TransportSnapshot transport{};
    WorkerState worker=WorkerState::starting;
    WorkerFault worker_fault=WorkerFault::none;
    EndpointFault fault=EndpointFault::none;
    bool running=false,ready=false,test_paused=false;
    std::size_t queued=0,events=0,tracked=0,suspended=0;
    RateResult device{};
    std::uint64_t effects=0,commands_sent=0,queries_sent=0,peer_errors=0;
};
struct EndpointOptions {
    TransportConfig transport;
    WorkerOptions worker;
    std::uint64_t operation_timeout_ns=3000000000ULL;
    // Test only: suppress the direct final reply, while QUERY remains functional.
    bool test_withhold_final_status=false;
};
// Linux MVP rate-command endpoint. Owns transport + one supervised journal/rate
// handler process + a bounded coordinator thread. External callbacks own their
// payload copies and never perform network/storage/handler work.
// Receiver requires the explicit simulated_rate_handler option. No general ROS
// handler is installed. The transport accessor is for sensors/diagnostics only;
// CONTROL/check replies are exclusively consumed by this coordinator.
class CommandEndpoint {
public:
    explicit CommandEndpoint(EndpointOptions options);
    ~CommandEndpoint();
    CommandEndpoint(const CommandEndpoint&)=delete;
    CommandEndpoint& operator=(const CommandEndpoint&)=delete;
    SubmitResult execute(std::uint32_t route,Identity request,RateCommand command,std::uint64_t ingress_ns);
    SubmitResult query(std::uint32_t route,Identity request);
    bool poll(CommandEvent& event);
    EndpointSnapshot snapshot() const;
    TransportOwner& transport() noexcept;
    void request_stop() noexcept;
    void join();
private:
    struct Impl;
    std::unique_ptr<Impl> impl_;
};
}
