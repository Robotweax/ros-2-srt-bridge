#pragma once
#include <robotweax/srt_bridge/ticket.hpp>
#include <robotweax/srt_bridge/execution.hpp>
#include <array>

namespace robotweax::srt_bridge {
enum class WorkerOperation : std::uint16_t { admit=1,get,begin_dispatch,finish,invalidate_session,observe_remote,sender_may_transmit,execute,handler_snapshot,decline,reconcile_sender };
struct WorkerRequest {
    WorkerOperation operation=WorkerOperation::get;
    Identity request_id{},session{};
    std::uint32_t route=0;
    RateCommand command{};
    CommandContext context{};
    CommandStatus remote_status{};
    CommandState state=CommandState::unknown;
    CommandReason reason=CommandReason::none;
    RateResult result{};
    bool clock_qualified=false;
    std::uint32_t grant_slot=UINT32_MAX;
    std::uint64_t grant_generation=0;
};
enum class WorkerState { starting,ready,failed,stopping,stopped };
enum class WorkerFault { none,spawn,protocol,storage,exited,shutdown_timeout,configuration };
enum class WorkerSubmit { queued,busy,not_ready,invalid,stopped };
struct WorkerSubmission { WorkerSubmit result=WorkerSubmit::invalid;std::uint64_t token=0; };
struct WorkerReply {
    std::uint64_t token=0;
    WorkerOperation operation=WorkerOperation::get;
    JournalResult journal{};
    bool may_transmit=false,test_paused=false;
    unsigned test_handler_point=0;
    std::optional<DurableCommandTicket> ticket{};
    std::optional<DispatchTicket> dispatch{};
    RateResult device{};
    std::uint64_t effects=0;
    std::optional<WorkerStartObservation> start_observation{};
};
struct WorkerOptions {
    std::string executable; // Absolute path to the installed/built worker executable.
    JournalOptions journal;
    // Explicit test-only subprocess barriers/faults; never CLI/env/peer input.
    std::optional<JournalPoint> test_pause_at{};
    std::optional<JournalFaults> test_faults{};
    bool simulated_rate_handler=false,external_rate_handler=false;
    bool start_diagnostics=false; // Local shared-mapping diagnostics only, default off.
    // 1: before atomic start, 2: after start, 3: after simulated effect.
    unsigned test_handler_pause=0;
};
// Linux process supervisor, single external coordinator. Uses posix_spawn (never
// fork after transport threads exist), fixed 2048-byte SOCK_SEQPACKET IPC and at
// most 64 outstanding requests. No blocking storage/handler work in the parent.
// poll advances child/IPC state; caller must service it, including while idle.
class JournalWorker {
public:
    explicit JournalWorker(WorkerOptions options);
    ~JournalWorker();
    JournalWorker(const JournalWorker&)=delete;
    JournalWorker& operator=(const JournalWorker&)=delete;
    WorkerSubmission submit(const WorkerRequest& request);
    WorkerSubmission submit_execute(DispatchTicket&& ticket);
    WorkerSubmission submit_reconcile(SenderSubmissionReceipt& receipt);
    bool poll(WorkerReply& reply);
    bool resume_test_barrier() noexcept;
    WorkerState state() const noexcept;
    WorkerFault fault() const noexcept;
    std::size_t pending() const noexcept;
    void request_stop() noexcept; // Revokes all outstanding sender tickets immediately.
    bool join(); // <= 4 s user-space deadline; see shutdown_timeout on unreaped child.
private:
    struct Impl;
    std::unique_ptr<Impl> impl_;
};
}
