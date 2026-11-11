#pragma once
#include <robotweax/srt_bridge/commands.hpp>
#include <optional>
#include <string>
#include <memory>

namespace robotweax::srt_bridge {
enum class JournalSide { sender=1,receiver=2 };
struct CommandContext {
    Identity session{},source_epoch{};
    std::uint64_t source_monotonic_ns=0,deadline_ns=0;
};
struct JournalEntry {
    Identity request_id{},owner_epoch{};
    std::uint32_t route=0;
    RateCommand command{};
    CommandContext context{};
    Digest payload_hash{};
    CommandState state=CommandState::unknown;
    CommandReason reason=CommandReason::none;
    RateResult result{};
    std::uint64_t admitted_ns=0,dispatched_ns=0,finished_ns=0,revision=0;
};
enum class JournalError { none,invalid,not_found,conflict,capacity,busy,context_lost,clock_unqualified,invalid_state,storage,corrupt };
struct JournalResult {
    JournalError error=JournalError::none;
    std::optional<JournalEntry> entry{};
    bool inserted=false;
    explicit operator bool() const noexcept{return error==JournalError::none&&entry.has_value();}
};
enum class JournalPoint { admission_before_commit,admission_committed,dispatch_committed,result_before_commit,result_committed };
// Test-only fault controls. Production defaults are null; no config/CLI/environment
// switch enables them. A zero counter fails every following write/sync.
struct JournalFaults { int writes_before_failure=-1,syncs_before_failure=-1;bool full=false; };
struct JournalOptions {
    std::string path,local_peer_id,remote_peer_id;
    JournalSide side=JournalSide::receiver;
    Identity process_epoch{};
    std::uint32_t max_entries=10000;
    std::uint64_t max_bytes=64ULL*1024*1024,wal_bytes=8ULL*1024*1024;
    JournalFaults* test_faults=nullptr;
    void (*test_hook)(JournalPoint,void*)=nullptr;
    void* test_context=nullptr;
};
// One dedicated worker owns this blocking SQLite API. Never call it from ROS or
// SRT callbacks. Reopening always recovers unfinished work conservatively.
class CommandJournal {
public:
    explicit CommandJournal(JournalOptions options);
    ~CommandJournal();
    CommandJournal(const CommandJournal&)=delete;
    CommandJournal& operator=(const CommandJournal&)=delete;
    JournalResult admit(Identity id,std::uint32_t route,RateCommand command,CommandContext context,std::uint64_t now);
    JournalResult get(Identity id);
    // Caller must freshly check session/clock before dispatch and again before
    // invoking the handler after this durable DISPATCHING commit.
    JournalResult begin_dispatch(Identity id,Identity current_session,bool clock_qualified,std::uint64_t now);
    JournalResult decline(Identity id,CommandState state,CommandReason reason,std::uint64_t now);
    JournalResult finish(Identity id,CommandState state,CommandReason reason,RateResult result,std::uint64_t now);
    JournalError invalidate_session(Identity session,std::uint64_t now);
    JournalResult reconcile_sender(Identity id,std::uint32_t route,RateCommand command,CommandContext context,std::uint64_t now);
    JournalError observe_remote(Identity id,std::uint32_t route,const CommandStatus& status,std::uint64_t now);
    bool sender_may_transmit(Identity id,Identity session,std::uint64_t now);
    std::uint64_t file_bytes() const;
    std::uint32_t entry_count() const;
    bool healthy() const noexcept;
private:
    struct Impl;
    std::unique_ptr<Impl> impl_;
};
}
