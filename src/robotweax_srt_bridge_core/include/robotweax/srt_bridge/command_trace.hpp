#pragma once
#include <robotweax/srt_bridge/commands.hpp>
#include <atomic>


namespace robotweax::srt_bridge {
enum class CommandTracePoint : unsigned {
    endpoint_started=1,session_changed,invalidate_requested,invalidate_completed,
    sender_admission,submit_result,worker_unknown,endpoint_stopping,endpoint_stopped,
    mailbox_flushed=20,input_dropped,make_rejected,queue_rejected,outbound_dropped,
    provider_sent,provider_error,outbound_flushed,transport_stopping,clock_deferred
};
enum class CommandTraceReason : unsigned {
    none,session_changed,abandoned_submit,context_mismatch,proof_revoked,deadline,
    missing_proof,session_rejected,queue_rejected,provider_error,shutdown
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
