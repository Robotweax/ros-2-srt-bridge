#pragma once
#include <robotweax/srt_bridge/commands.hpp>
#include <atomic>
#include <mutex>

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
// Optional observational storage shared by coordinator/transport producers and
// one external consumer. Producers never wait, allocate, call back or perform
// I/O. Full/contended writes are counted and dropped, never used for decisions.
// Sequence allocation precedes try-lock: concurrent producer arrival order is
// not a causal order. Monotonic timestamps bracket local observations only.
class CommandTrace {
public:
    static constexpr std::size_t capacity=256;
    void record(CommandTraceEvent event){
        event.sequence=attempted_.fetch_add(1)+1;
        std::unique_lock lock(mutex_,std::try_to_lock);
        if(!lock.owns_lock()||count_==capacity){++dropped_;return;}
        events_[(head_+count_++)%capacity]=event;
    }
    bool poll(CommandTraceEvent& event){
        std::lock_guard lock(mutex_);if(!count_)return false;
        event=events_[head_];head_=(head_+1)%capacity;--count_;return true;
    }
    std::uint64_t attempted()const{return attempted_.load();}
    std::uint64_t dropped()const{return dropped_.load();}
private:
    std::array<CommandTraceEvent,capacity> events_{};
    std::size_t head_=0,count_=0;
    std::mutex mutex_;
    std::atomic<std::uint64_t> attempted_{0},dropped_{0};
};
}
