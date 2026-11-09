#pragma once
#include <robotweax/srt_bridge/journal.hpp>
#include <atomic>

namespace robotweax::srt_bridge {
class JournalWorker;
class TransportOwner;
class SenderSubmissionReceipt;
enum class SubmissionDisposition { unsubmitted,queued,sdk_accepted,abandoned };
// A one-use sender admission proof, created only from a newly committed worker
// admission. It is not an execution acknowledgment. BUSY preserves the ticket;
// successful transport mailbox admission consumes it. No ticket on GET/duplicate.
class DurableCommandTicket {
public:
    DurableCommandTicket(DurableCommandTicket&&) noexcept=default;
    DurableCommandTicket& operator=(DurableCommandTicket&&) noexcept=default;
    DurableCommandTicket(const DurableCommandTicket&)=delete;
    DurableCommandTicket& operator=(const DurableCommandTicket&)=delete;
    SenderSubmissionReceipt receipt() const;
private:
    struct Proof {
        JournalEntry entry;
        std::string local_peer,remote_peer;
        std::shared_ptr<std::atomic<bool>> live;
        std::atomic<bool> claimed{false};
        std::atomic<SubmissionDisposition> disposition{SubmissionDisposition::unsubmitted};
        std::atomic<bool> reconciliation_submitted{false};
    };
    std::shared_ptr<Proof> proof_;
    explicit DurableCommandTicket(std::shared_ptr<Proof> proof):proof_(std::move(proof)){}
    friend class JournalWorker;
    friend class TransportOwner;
    friend class SenderSubmissionReceipt;
};
// Opaque observation/capability, never a send ticket or execution acknowledgment.
// The shared proof identity and live worker token fence generation reuse.
class SenderSubmissionReceipt {
public:
    SenderSubmissionReceipt()=default;
    SenderSubmissionReceipt(SenderSubmissionReceipt&&) noexcept=default;
    SenderSubmissionReceipt& operator=(SenderSubmissionReceipt&&) noexcept=default;
    SenderSubmissionReceipt(const SenderSubmissionReceipt&)=delete;
    SenderSubmissionReceipt& operator=(const SenderSubmissionReceipt&)=delete;
    explicit operator bool()const noexcept{return bool(proof_);}
    SubmissionDisposition disposition()const noexcept{return proof_?proof_->disposition.load(std::memory_order_acquire):SubmissionDisposition::unsubmitted;}
    Identity session()const noexcept{return proof_?proof_->entry.context.session:Identity{};}
private:
    std::shared_ptr<DurableCommandTicket::Proof> proof_;
    explicit SenderSubmissionReceipt(std::shared_ptr<DurableCommandTicket::Proof> proof):proof_(std::move(proof)){}
    friend class DurableCommandTicket;
    friend class JournalWorker;
};
inline SenderSubmissionReceipt DurableCommandTicket::receipt()const{return SenderSubmissionReceipt(proof_);}
}
