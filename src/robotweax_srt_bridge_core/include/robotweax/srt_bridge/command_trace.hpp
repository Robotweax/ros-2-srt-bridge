#pragma once
#include <robotweax/srt_bridge/commands.hpp>
#include <atomic>


namespace robotweax::srt_bridge {
enum class CommandTracePoint : unsigned {
    endpoint_started=1,session_changed,invalidate_requested,invalidate_completed,
    sender_admission,submit_result,worker_unknown,endpoint_stopping,endpoint_stopped,
    mailbox_flushed=20,input_dropped,make_rejected,queue_rejected,outbound_dropped,
    provider_sent,provider_error,outbound_flushed,transport_stopping,clock_deferred,session_action,link_lost,
    control_admission,peer_error_received,receiver_worker_result,
    receiver_deferred,receiver_resumed,receiver_retained_dropped,receiver_capacity_rejected,receiver_expiry_admission,
    start_submission,start_check,execute_submission,worker_start,start_declined,
    sender_clock,sender_pending_release,sender_journal,sender_event
};
enum class CommandTraceReason : unsigned {
    none,session_changed,abandoned_submit,context_mismatch,proof_revoked,deadline,
    missing_proof,session_rejected,queue_rejected,provider_error,shutdown,socket_state,security_timeout,epoll_error,receive_error,wire_decode,session_decision
};
struct CommandTraceEvent {
    std::uint64_t sequence=0,monotonic_ns=0;
    CommandTracePoint point=CommandTracePoint::endpoint_started;
    CommandTraceReason reason=CommandTraceReason::none;
    Identity request{},session{},owner_epoch{};
    std::uint64_t control_generation=0,sensor_generation=0;
    std::uint32_t route=0;
    // Point-specific enum/error value, not an authoritative command outcome.
    unsigned value=0;
    Identity entry_owner_epoch{}; // Populated for worker-record observations only.
    unsigned detail=0; // session_action: close-control/close-sensor/flush bits 1/2/4; link_lost: channel 0/1.
    // Points32..38: detail=original request Kind (COMMAND6/QUERY8),
    // value=SessionError/ControlErrorCode/JournalError for32/33/34;
    //35..37=SessionError,38=ControlErrorCode.
    std::uint64_t request_sequence=0,origin_ns=0,evaluated_ns=0,clock_deadline_ns=0;
    std::int64_t age_lower_ns=0,age_upper_ns=0;
    std::uint64_t expiry_deadline_ns=0;unsigned budget_ms=0; // Point39 qualified expiry proof.
    unsigned clock_error=0,age_error=0; // Point32: post-admission clock state and returned AgeResult error.
    // age_error is meaningful for COMMAND freshness decisions, not QUERY/identity rejection.
    // Points40..44 only. Local diagnostics, not IPC/wire authority.
    std::uint64_t check_token=0,worker_token=0,grant_generation=0,grant_deadline_ns=0,command_deadline_ns=0;
    std::uint32_t grant_slot=UINT32_MAX;
    bool start_granted=false,worker_observation_available=false;
    std::uint64_t consume_ns=0,consume_deadline_ns=0,second_gate_ns=0,second_gate_deadline_ns=0;
    unsigned consume_result=0;
    bool second_gate_checked=false,handler_invoked=false;
    unsigned terminal_state=0,terminal_reason=0;
    // Points45..48 only, default-off sender diagnostics. No worker IPC fields.
    //45 detail1=first deferral,2=recovered;46 value:1=stale drop,2=make
    // rejection,3=queue rejection,4=outbound queued,5=mailbox flush.
    //47 detail=WorkerOperation,value=JournalError;48 value=local JournalError,
    // detail=received peer ControlErrorCode (0 if absent).
    std::uint64_t clock_previous_deadline_ns=0,probe_anchor_ns=0,journal_revision=0;
    std::int64_t offset_lower_ns=0,offset_upper_ns=0;
    bool clock_observed=false,journal_entry_available=false;
};
enum class CommandTraceProducer : unsigned { coordinator=0,transport=1 };
// Two fixed SPSC lanes: exactly one coordinator producer and one transport
// producer, plus one external consumer. No producer/consumer mutex contention,
// retry loop, allocation, callback or I/O. Each lane retains FIFO order; a full
// lane drops new observations explicitly. Traces never authorize decisions.
// One producer thread per lane is mandatory; producer replacement requires join.
class CommandTrace {
public:
    static constexpr std::size_t capacity=256,lane_capacity=capacity/2;
    void record(CommandTraceProducer producer,CommandTraceEvent event){
        event.sequence=attempted_.fetch_add(1)+1;
        auto& lane=lanes_[static_cast<unsigned>(producer)];
        const auto tail=lane.tail.load(std::memory_order_relaxed);
        if(tail-lane.head.load(std::memory_order_acquire)>=lane_capacity){++dropped_;return;}
        lane.events[tail%lane_capacity]=event;
        lane.tail.store(tail+1,std::memory_order_release);
    }
    // Convenience for a standalone single coordinator producer.
    void record(CommandTraceEvent event){record(CommandTraceProducer::coordinator,event);}
    bool poll(CommandTraceEvent& event){
        for(unsigned n=0;n<2;++n){const auto index=(cursor_+n)%2;auto& lane=lanes_[index];
            const auto head=lane.head.load(std::memory_order_relaxed);
            if(head==lane.tail.load(std::memory_order_acquire))continue;
            event=lane.events[head%lane_capacity];lane.head.store(head+1,std::memory_order_release);
            cursor_=(index+1)%2;return true;
        }
        return false;
    }
    std::uint64_t attempted()const{return attempted_.load();}
    std::uint64_t dropped()const{return dropped_.load();} // Full lane only, never contention.
private:
    struct Lane {
        std::array<CommandTraceEvent,lane_capacity> events{};
        std::atomic<std::uint64_t> head{0},tail{0};
    };
    std::array<Lane,2> lanes_{};
    unsigned cursor_=0; // Single consumer only.
    std::atomic<std::uint64_t> attempted_{0},dropped_{0};
};
}
