#pragma once
#include <robotweax/srt_bridge/journal.hpp>
#include <limits>

namespace robotweax::ros_bridge {
namespace core=robotweax::srt_bridge;
struct DdsExpirySeal {
    core::Identity id{},session{},sender_process{};
    core::RateCommand command{};
    core::Digest payload_hash{};
    std::uint64_t origin_ns=0,deadline_ns=0;
};
inline bool valid_expiry_seal(const DdsExpirySeal& s){
    return s.id!=core::Identity{}&&s.session!=core::Identity{}&&s.sender_process!=core::Identity{}&&
        core::valid_command(s.command)&&s.command.budget_ms==5000&&s.origin_ns&&
        s.origin_ns<=std::uint64_t(std::numeric_limits<std::int64_t>::max())-5000000000ULL&&
        s.deadline_ns==s.origin_ns+5000000000ULL&&s.payload_hash==core::command_hash(100,s.command);
}
// Only an unacknowledged admission in this sender/process/session can request
// absence sealing. Recovery across owner or session changes stays QUERY-only.
inline bool may_seal_expired(const core::JournalEntry& e,core::Identity owner,core::Identity session,std::uint64_t now){
    return e.owner_epoch==owner&&e.context.source_epoch==owner&&e.context.session==session&&
        e.route==100&&e.state==core::CommandState::local_queued&&e.reason==core::CommandReason::none&&
        e.revision==0&&!e.result.valid&&now<=std::uint64_t(std::numeric_limits<std::int64_t>::max())&&now>e.context.deadline_ns&&
        valid_expiry_seal({e.request_id,e.context.session,e.context.source_epoch,e.command,e.payload_hash,e.context.source_monotonic_ns,e.context.deadline_ns});
}
// Receiver journal worker only, after fresh protocol/session/peer validation.
// The journal is retained for the whole session, with no record eviction. This
// operation never dispatches, invokes a handler, or alters an existing entry.
inline core::JournalResult seal_expired(core::CommandJournal& journal,const DdsExpirySeal& s,
        core::Identity current_session,core::Identity expected_sender,std::uint64_t now){
    if(now>std::uint64_t(std::numeric_limits<std::int64_t>::max())||!valid_expiry_seal(s))return {core::JournalError::invalid};
    if(s.session!=current_session||s.sender_process!=expected_sender)return {core::JournalError::context_lost};
    if(now<=s.deadline_ns)return {core::JournalError::invalid_state};
    auto existing=journal.get(s.id);
    if(existing.error!=core::JournalError::not_found){
        if(existing.entry&&(existing.entry->route!=100||existing.entry->payload_hash!=s.payload_hash||existing.entry->command!=s.command||
                existing.entry->context.session!=s.session||existing.entry->context.source_epoch!=s.sender_process||
                existing.entry->context.source_monotonic_ns!=s.origin_ns||existing.entry->context.deadline_ns!=s.deadline_ns))
            existing.error=core::JournalError::conflict;
        return existing;
    }
    // Strictly past deadline: the unchanged SDK admits only EXPIRED/revision 1.
    // Its FULL-synchronous commit precedes the STATUS reply. A later COMMAND
    // finds this same ID/hash and cannot enter DISPATCHING.
    auto result=journal.admit(s.id,100,s.command,{s.session,s.sender_process,s.origin_ns,s.deadline_ns},now);
    if(result&&(!result.inserted||result.entry->state!=core::CommandState::expired||
            result.entry->reason!=core::CommandReason::start_deadline||result.entry->revision!=1||
            result.entry->dispatched_ns||result.entry->result.valid))result.error=core::JournalError::corrupt;
    return result;
}
}
