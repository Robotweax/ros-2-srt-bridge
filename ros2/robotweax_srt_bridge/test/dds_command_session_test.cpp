#include <robotweax_srt_bridge/dds_command_session.hpp>
#include <gtest/gtest.h>
#include <robotweax_srt_bridge/dds_inbox.hpp>
#include <barrier>
#include <thread>
#include <atomic>
namespace rb=robotweax::ros_bridge;
namespace core=robotweax::srt_bridge;
namespace {
core::Identity id(unsigned value){core::Identity out{};out.back()=std::byte(value);return out;}
core::Digest proof(unsigned value=1){core::Digest out{};out.back()=std::byte(value);return out;}
struct Pair {
    rb::DdsCommandSession a{true,id(1),id(2),proof()},b{false,id(3),id(4),proof()};
    Pair(){EXPECT_TRUE(a.hello(id(3),id(4),{},{},proof(),1,100,100));EXPECT_TRUE(b.hello(id(1),id(2),{},{},proof(),1,100,100));EXPECT_EQ(a.session(),b.session());EXPECT_TRUE(a.hello(id(3),id(4),id(2),b.session(),proof(),2,101,101));EXPECT_TRUE(b.hello(id(1),id(2),id(4),a.session(),proof(),2,101,101));}
};
TEST(DdsInbox,ConcurrentReceivedFramesAreNotDroppedOnMutexContention){
    struct Task {unsigned id=0;std::array<std::byte,512> payload{};};
    for(unsigned run=0;run<16;++run){
        rb::DdsInbox<Task> inbox;std::barrier start(8);std::array<std::thread,8> threads;
        std::atomic<unsigned> admitted=0;
        for(unsigned n=0;n<threads.size();++n)threads[n]=std::thread([&,n]{start.arrive_and_wait();for(unsigned i=0;i<8;++i){Task task;task.id=n*8+i;if(inbox.receive(task))++admitted;}});
        for(auto& thread:threads)thread.join();
        EXPECT_EQ(admitted,64U);EXPECT_FALSE(inbox.receive({}));
        std::array<bool,64> seen{};Task task;unsigned count=0;
        while(inbox.pop(task)){ASSERT_LT(task.id,seen.size());EXPECT_FALSE(seen[task.id]);seen[task.id]=true;++count;}
        EXPECT_EQ(count,64U);EXPECT_TRUE(inbox.try_push({}));EXPECT_TRUE(inbox.pop(task));
    }
}
TEST(DdsSession,RequiresNamespaceAcknowledgmentAndFreshMonotonicLease){
    rb::DdsCommandSession a{true,id(1),id(2),proof()};
    EXPECT_FALSE(a.hello(id(3),id(4),{},{},proof(2),1,100,100));
    EXPECT_TRUE(a.hello(id(3),id(4),{},{},proof(),1,100,100));
    EXPECT_FALSE(a.fresh(a.session(),100));
    Pair p;EXPECT_TRUE(p.a.fresh(p.a.session(),101));EXPECT_FALSE(p.a.fresh(p.a.session(),101+rb::DdsCommandSession::lease_ns));
}
TEST(DdsSession,RejectsReplayWrongTargetNamespaceProcessAndFutureTime){
    Pair p;const auto sid=p.a.session();
    EXPECT_FALSE(p.a.frame(id(3),id(4),id(2),sid,proof(),3,300,299));
    EXPECT_FALSE(p.a.frame(id(3),id(4),id(9),sid,proof(),3,300,300));
    EXPECT_FALSE(p.a.frame(id(9),id(4),id(2),sid,proof(),3,300,300));
    EXPECT_FALSE(p.a.frame(id(3),id(4),id(2),sid,proof(2),3,300,300));
    EXPECT_TRUE(p.a.frame(id(3),id(4),id(2),sid,proof(),3,300,300));
    EXPECT_FALSE(p.a.frame(id(3),id(4),id(2),sid,proof(),3,300,300));
}
TEST(DdsSession,ExpiredLeaseCannotBeRevivedByOldReliableTraffic){
    Pair p;const auto old=p.a.session();const auto time=101+rb::DdsCommandSession::lease_ns;
    p.a.tick(time,id(5));EXPECT_NE(p.a.session(),old);EXPECT_FALSE(p.a.fresh(old,time));
    EXPECT_FALSE(p.a.hello(id(3),id(4),id(2),old,proof(),3,time,time));
    EXPECT_FALSE(p.a.frame(id(3),id(4),id(5),old,proof(),3,time,time));
    EXPECT_TRUE(p.b.hello(id(1),id(5),id(4),p.a.session(),proof(),3,time,time));
    EXPECT_TRUE(p.a.hello(id(3),id(4),id(5),p.b.session(),proof(),3,time,time));
    EXPECT_TRUE(p.a.fresh(p.a.session(),time));EXPECT_EQ(p.a.session(),p.b.session());
}
TEST(DdsSession,RetiredPeerNonceCannotRollBackSession){
    Pair p;const auto old=p.a.session();
    EXPECT_TRUE(p.a.hello(id(6),id(7),{},{},proof(),1,200,200));
    EXPECT_NE(p.a.session(),old);
    EXPECT_FALSE(p.a.hello(id(3),id(4),{},{},proof(),100,201,201));
    EXPECT_FALSE(p.a.fresh(old,201));
}
TEST(DdsSession,WrongSessionHeartbeatCannotExtendAcknowledgedLease){
    Pair p;EXPECT_FALSE(p.a.hello(id(3),id(4),id(2),id(99),proof(),3,1000,1000));
    EXPECT_FALSE(p.a.fresh(p.a.session(),101+rb::DdsCommandSession::lease_ns));
}
TEST(DdsSession,RetiredNonceCapacityFailsClosedRatherThanForgettingOldEpochs){
    Pair p;for(unsigned n=10;n<74;++n)EXPECT_TRUE(p.a.hello(id(n+1),id(n),{},{},proof(),1,200,200));
    EXPECT_FALSE(p.a.hello(id(75),id(74),{},{},proof(),1,200,200));EXPECT_TRUE(p.a.failed());
}
TEST(DdsSession,InvalidReplacementFailsClosed){
    Pair p;p.a.tick(101+rb::DdsCommandSession::lease_ns,id(2));
    EXPECT_TRUE(p.a.failed());EXPECT_FALSE(p.a.fresh(p.a.session(),101));
}
}
