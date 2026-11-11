#pragma once
#include <robotweax/srt_bridge/journal.hpp>

namespace robotweax::srt_bridge {
namespace execution_detail { struct Record; }
class JournalWorker;
class TransportOwner;
// Diagnostic snapshots only; never authorize start or mutate journal outcomes.
// Published once by the child, read by supervisor after the matching IPC reply.
struct WorkerStartObservation {
    std::uint64_t consume_ns=0,consume_deadline_ns=0,second_gate_ns=0,second_gate_deadline_ns=0;
    unsigned consume_result=0; // 0 unavailable, 1 started, 2 expired, 3 revoked, 4 invalid.
    bool second_gate_checked=false,handler_invoked=false;
};
// Minted from a fresh durable DISPATCHING commit, never GET or duplicate.
// The owner must grant it, then the same worker consumes its shared start fence.
// A freshness reply alone cannot be substituted for this move-only proof.
class DispatchTicket {
public:
    DispatchTicket(DispatchTicket&&) noexcept=default;
    DispatchTicket& operator=(DispatchTicket&&) noexcept=default;
    DispatchTicket(const DispatchTicket&)=delete;
    DispatchTicket& operator=(const DispatchTicket&)=delete;
private:
    std::shared_ptr<execution_detail::Record> record_;
    explicit DispatchTicket(std::shared_ptr<execution_detail::Record> record):record_(std::move(record)){}
    friend class JournalWorker;
    friend class TransportOwner;

};
}
