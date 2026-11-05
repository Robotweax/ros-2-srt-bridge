#include <robotweax_srt_bridge/dds_expiry_seal.hpp>
#include <gtest/gtest.h>
#include <filesystem>
#include <unistd.h>
namespace rb=robotweax::ros_bridge;
namespace core=robotweax::srt_bridge;
namespace {
core::Identity id(unsigned n){core::Identity x{};x.back()=std::byte(n);return x;}
constexpr std::uint64_t origin=1000000000ULL,deadline=origin+5000000000ULL;
rb::DdsExpirySeal seal(){core::RateCommand cmd{200,5000,0,1};return {id(1),id(2),id(3),cmd,core::command_hash(100,cmd),origin,deadline};}
class ExpirySeal:public testing::Test {
protected:
    std::filesystem::path dir=std::filesystem::temp_directory_path()/("dds-seal-"+std::to_string(getpid())+"-"+std::to_string(serial++));
    static inline unsigned serial=0;
    void SetUp()override{std::filesystem::create_directories(dir);}
    void TearDown()override{std::filesystem::remove_all(dir);}
    core::JournalOptions options(core::JournalSide side=core::JournalSide::receiver,unsigned owner=4){core::JournalOptions o;o.path=(dir/(side==core::JournalSide::receiver?"receiver.sqlite":"sender.sqlite")).string();o.local_peer_id=side==core::JournalSide::receiver?"robot":"operator";o.remote_peer_id=side==core::JournalSide::receiver?"operator":"robot";o.side=side;o.process_epoch=id(owner);return o;}
    core::JournalResult close(core::CommandJournal& j,const rb::DdsExpirySeal& s,std::uint64_t now=deadline+1){return rb::seal_expired(j,s,id(2),id(3),now);}
};
TEST_F(ExpirySeal,StrictDeadlineAndOriginalLiveContextRequiredWithoutAdmission){
    core::CommandJournal j(options());auto s=seal();
    EXPECT_EQ(close(j,s,deadline-1).error,core::JournalError::invalid_state);
    EXPECT_EQ(close(j,s,deadline).error,core::JournalError::invalid_state);
    EXPECT_EQ(rb::seal_expired(j,s,id(9),id(3),deadline+1).error,core::JournalError::context_lost);
    EXPECT_EQ(rb::seal_expired(j,s,id(2),id(9),deadline+1).error,core::JournalError::context_lost);
    auto bad=s;bad.payload_hash={};EXPECT_EQ(close(j,bad).error,core::JournalError::invalid);
    bad=s;bad.origin_ns--;EXPECT_EQ(close(j,bad).error,core::JournalError::invalid);
    bad=s;bad.command.budget_ms=1000;EXPECT_EQ(close(j,bad).error,core::JournalError::invalid);
    bad=s;bad.origin_ns=UINT64_MAX;bad.deadline_ns=0;EXPECT_EQ(close(j,bad).error,core::JournalError::invalid);
    EXPECT_EQ(close(j,s,UINT64_MAX).error,core::JournalError::invalid);
    EXPECT_EQ(j.entry_count(),0U);EXPECT_TRUE(j.healthy());
}
TEST_F(ExpirySeal,DurableExpiredTombstonePreventsLaterDispatchAndDuplicateAdmission){
    auto s=seal();{
        core::CommandJournal j(options());auto r=close(j,s);ASSERT_TRUE(r);ASSERT_TRUE(r.inserted);
        EXPECT_EQ(r.entry->state,core::CommandState::expired);EXPECT_EQ(r.entry->reason,core::CommandReason::start_deadline);
        EXPECT_EQ(r.entry->revision,1U);EXPECT_EQ(r.entry->dispatched_ns,0U);EXPECT_FALSE(r.entry->result.valid);
        auto duplicate=close(j,s);ASSERT_TRUE(duplicate);EXPECT_FALSE(duplicate.inserted);EXPECT_EQ(duplicate.entry->revision,1U);
        auto late=j.admit(s.id,100,s.command,{s.session,s.sender_process,s.origin_ns,s.deadline_ns},deadline+2);
        ASSERT_TRUE(late);EXPECT_FALSE(late.inserted);EXPECT_EQ(late.entry->state,core::CommandState::expired);
        EXPECT_EQ(j.begin_dispatch(s.id,s.session,true,deadline+2).error,core::JournalError::invalid_state);
        EXPECT_EQ(j.entry_count(),1U);
    }
    core::CommandJournal reopened(options(core::JournalSide::receiver,5));auto r=reopened.get(s.id);ASSERT_TRUE(r);
    EXPECT_EQ(r.entry->state,core::CommandState::expired);EXPECT_EQ(r.entry->revision,1U);EXPECT_EQ(r.entry->dispatched_ns,0U);
}
TEST_F(ExpirySeal,ExistingAcceptedOrDispatchingIsNeverConvertedToExpiry){
    core::CommandJournal j(options());auto s=seal();ASSERT_TRUE(j.admit(s.id,100,s.command,{s.session,s.sender_process,s.origin_ns,s.deadline_ns},origin));
    auto r=close(j,s);ASSERT_TRUE(r);EXPECT_FALSE(r.inserted);EXPECT_EQ(r.entry->state,core::CommandState::accepted);EXPECT_EQ(r.entry->revision,1U);
    ASSERT_TRUE(j.begin_dispatch(s.id,s.session,true,origin+1));r=close(j,s);ASSERT_TRUE(r);
    EXPECT_EQ(r.entry->state,core::CommandState::dispatching);EXPECT_EQ(r.entry->revision,2U);
}
TEST_F(ExpirySeal,CommittedSuccessAndUncertaintyAreReturnedWithoutRewritingHistory){
    core::CommandJournal j(options());auto s=seal();
    for(auto state:{core::CommandState::succeeded,core::CommandState::unknown}){
        s.id=id(state==core::CommandState::succeeded?1:2);
        ASSERT_TRUE(j.admit(s.id,100,s.command,{s.session,s.sender_process,s.origin_ns,s.deadline_ns},origin));
        ASSERT_TRUE(j.begin_dispatch(s.id,s.session,true,origin+1));
        const auto reason=state==core::CommandState::succeeded?core::CommandReason::none:core::CommandReason::effect_uncertain;
        const auto result=state==core::CommandState::succeeded?core::RateResult{200,1,true}:core::RateResult{};
        ASSERT_TRUE(j.finish(s.id,state,reason,result,origin+2));
        auto r=close(j,s);ASSERT_TRUE(r);EXPECT_FALSE(r.inserted);EXPECT_EQ(r.entry->state,state);EXPECT_EQ(r.entry->revision,3U);
        EXPECT_EQ(r.entry->result,result);
    }
}
TEST_F(ExpirySeal,ConflictingMetadataCannotCreateOrReplaceTheExistingRecord){
    core::CommandJournal j(options());auto s=seal();ASSERT_TRUE(close(j,s));
    auto bad=s;bad.command.rate_hz=100;bad.payload_hash=core::command_hash(100,bad.command);
    EXPECT_EQ(close(j,bad).error,core::JournalError::conflict);
    bad=s;bad.origin_ns--;bad.deadline_ns--;EXPECT_EQ(close(j,bad).error,core::JournalError::conflict);
    auto r=j.get(s.id);ASSERT_TRUE(r);EXPECT_EQ(r.entry->command,s.command);EXPECT_EQ(r.entry->context.deadline_ns,s.deadline_ns);EXPECT_EQ(r.entry->revision,1U);
}
TEST_F(ExpirySeal,OnlyOriginalUnacknowledgedSenderCanRequestSealing){
    auto s=seal();core::CommandJournal sender(options(core::JournalSide::sender,3));
    auto r=sender.admit(s.id,100,s.command,{s.session,s.sender_process,s.origin_ns,s.deadline_ns},origin);ASSERT_TRUE(r);auto e=*r.entry;
    EXPECT_FALSE(rb::may_seal_expired(e,id(3),id(2),deadline));EXPECT_TRUE(rb::may_seal_expired(e,id(3),id(2),deadline+1));
    EXPECT_FALSE(rb::may_seal_expired(e,id(9),id(2),deadline+1));EXPECT_FALSE(rb::may_seal_expired(e,id(3),id(9),deadline+1));
    EXPECT_FALSE(rb::may_seal_expired(e,id(3),id(2),UINT64_MAX));
    for(auto state:{core::CommandState::accepted,core::CommandState::dispatching,core::CommandState::unknown,core::CommandState::expired}){
        auto acknowledged=e;acknowledged.state=state;EXPECT_FALSE(rb::may_seal_expired(acknowledged,id(3),id(2),deadline+1));
    }
    e.revision=1;EXPECT_FALSE(rb::may_seal_expired(e,id(3),id(2),deadline+1));
}
TEST_F(ExpirySeal,LostSealReplyAndOwnerRestartRecoverViaReadOnlyQuery){
    auto s=seal();{
        core::CommandJournal sender(options(core::JournalSide::sender,3)),receiver(options());
        ASSERT_TRUE(sender.admit(s.id,100,s.command,{s.session,s.sender_process,s.origin_ns,s.deadline_ns},origin));
        ASSERT_TRUE(close(receiver,s)); // Commit but deliver no reply before owner restart.
    }
    core::CommandJournal sender(options(core::JournalSide::sender,8)),receiver(options(core::JournalSide::receiver,9));
    auto local=sender.get(s.id),remote=receiver.get(s.id);ASSERT_TRUE(local);ASSERT_TRUE(remote);
    EXPECT_EQ(local.entry->state,core::CommandState::unknown);
    EXPECT_FALSE(rb::may_seal_expired(*local.entry,id(8),id(10),deadline+2));
    const auto& e=*remote.entry;core::CommandStatus status{e.state,e.reason,e.command,e.payload_hash,e.result,e.revision};
    ASSERT_TRUE(core::valid_remote_status(100,status));
    EXPECT_EQ(sender.observe_remote(s.id,100,status,deadline+2),core::JournalError::none);
    EXPECT_EQ(sender.get(s.id).entry->state,core::CommandState::expired);
    EXPECT_FALSE(sender.sender_may_transmit(s.id,id(10),deadline+2));
}
TEST_F(ExpirySeal,StorageFailureCannotReturnAnExpiryProof){
    core::JournalFaults faults;auto o=options();o.test_faults=&faults;core::CommandJournal j(o);faults.writes_before_failure=0;
    auto r=close(j,seal());EXPECT_FALSE(r);EXPECT_EQ(r.error,core::JournalError::storage);EXPECT_FALSE(r.entry);EXPECT_FALSE(j.healthy());
}
}
