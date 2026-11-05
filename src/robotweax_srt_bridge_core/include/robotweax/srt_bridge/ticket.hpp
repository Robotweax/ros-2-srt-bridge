#pragma once
#include <robotweax/srt_bridge/journal.hpp>
#include <atomic>

namespace robotweax::srt_bridge {
class JournalWorker;
class TransportOwner;
// A one-use sender admission proof, created only from a newly committed worker
// admission. It is not an execution acknowledgment. BUSY preserves the ticket;
// successful transport mailbox admission consumes it. No ticket on GET/duplicate.
class DurableCommandTicket {
public:
    DurableCommandTicket(DurableCommandTicket&&) noexcept=default;
    DurableCommandTicket& operator=(DurableCommandTicket&&) noexcept=default;
    DurableCommandTicket(const DurableCommandTicket&)=delete;
    DurableCommandTicket& operator=(const DurableCommandTicket&)=delete;
private:
    struct Proof {
        JournalEntry entry;
        std::string local_peer,remote_peer;
        std::shared_ptr<std::atomic<bool>> live;
        std::atomic<bool> claimed{false};
    };
    std::shared_ptr<Proof> proof_;
    explicit DurableCommandTicket(std::shared_ptr<Proof> proof):proof_(std::move(proof)){}
    friend class JournalWorker;
    friend class TransportOwner;
};
}
