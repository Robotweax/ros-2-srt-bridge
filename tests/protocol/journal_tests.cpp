#include <robotweax/srt_bridge/journal.hpp>
#include <filesystem>
#include <iostream>
#include <stdexcept>
#include <unistd.h>
using namespace robotweax::srt_bridge;
namespace {
unsigned checks=0;void check(bool b,const char* m){++checks;if(!b)throw std::runtime_error(m);}
Identity id(unsigned value){Identity i{};i[0]=static_cast<std::byte>(value&255);i[1]=static_cast<std::byte>((value>>8)&255);return i;}
std::filesystem::path root;
JournalOptions options(const std::string& name,JournalSide side=JournalSide::receiver){JournalOptions o;
    o.path=(root/name).string();o.local_peer_id=side==JournalSide::receiver?"robot":"operator";o.remote_peer_id=side==JournalSide::receiver?"operator":"robot";
    o.side=side;o.process_epoch=id(1);return o;}
CommandContext context(){return {id(10),id(2),100,5000};}
RateCommand rate(){return {100,5000,0,1};}
CommandStatus status(const JournalEntry& e){return {e.state,e.reason,e.command,e.payload_hash,e.result,e.revision};}
void basic(){
    auto o=options("basic.sqlite");
    {CommandJournal journal(o);
        check(journal.get(id(1)).error==JournalError::not_found,"absent ID");
        const auto first=journal.admit(id(1),100,rate(),context(),100);check(first&&first.inserted&&first.entry->state==CommandState::accepted,"durable admission");
        auto duplicate=journal.admit(id(1),100,rate(),{id(11),id(3),200,9000},200);
        check(duplicate&&!duplicate.inserted&&duplicate.entry->context.deadline_ns==5000,"duplicate renewed deadline/context");
        auto changed=rate();changed.rate_hz=200;
        check(journal.admit(id(1),100,changed,context(),100).error==JournalError::conflict,"conflicting ID");
        check(journal.begin_dispatch(id(1),id(10),false,200).error==JournalError::clock_unqualified,"unknown clock dispatch");
        check(journal.begin_dispatch(id(1),id(10),true,200).entry->state==CommandState::dispatching,"dispatch commit");
        check(journal.begin_dispatch(id(1),id(10),true,201).error==JournalError::invalid_state,"repeated execution admitted");
        check(bool(journal.admit(id(2),100,rate(),context(),100)),"second admission");
        check(journal.begin_dispatch(id(2),id(10),true,200).error==JournalError::busy,"parallel route dispatch");
        check(journal.finish(id(1),CommandState::succeeded,CommandReason::none,{100,2,true},300).error==JournalError::invalid,"false generation success");
        check(journal.finish(id(1),CommandState::succeeded,CommandReason::none,{100,1,true},300).entry->state==CommandState::succeeded,"result commit");
        check(journal.invalidate_session(id(10),400)==JournalError::none,"context loss");
        check(journal.get(id(2)).entry->state==CommandState::rejected,"accepted context not rejected");
        check(journal.get(id(1)).entry->result==RateResult{100,1,true},"context loss changed result");
        bool locked=false;try{CommandJournal other(o);}catch(const std::exception&){locked=true;}check(locked,"two workers opened journal");
        check(journal.admit(id(3),100,rate(),context(),6000).entry->state==CommandState::expired,"expired admission");
    }
    o.process_epoch=id(9);CommandJournal reopened(o);
    check(reopened.get(id(1)).entry->state==CommandState::succeeded&&reopened.get(id(1)).entry->result.valid,"completed result lost at restart");
    check(reopened.admit(id(1),100,rate(),context(),7000).entry->state==CommandState::succeeded,"duplicate result not retained");
}
void recovery_and_sender(){
    auto o=options("recovery.sqlite");
    {CommandJournal j(o);j.admit(id(1),100,rate(),context(),100);j.admit(id(2),100,rate(),context(),100);j.begin_dispatch(id(2),id(10),true,200);}
    {o.process_epoch=id(9);CommandJournal j(o);check(j.get(id(1)).entry->state==CommandState::rejected,"ACCEPTED restart");
        check(j.get(id(2)).entry->state==CommandState::unknown,"DISPATCHING restart");
        check(j.begin_dispatch(id(2),id(10),true,300).error==JournalError::invalid_state,"UNKNOWN retried");}
    auto sender=options("sender.sqlite",JournalSide::sender);
    {CommandJournal j(sender);check(j.admit(id(1),100,rate(),context(),100).entry->state==CommandState::local_queued,"sender persist before send");
        check(j.sender_may_transmit(id(1),id(10),200),"fresh durable sender ticket");}
    sender.process_epoch=id(9);CommandJournal j(sender);
    check(j.get(id(1)).entry->state==CommandState::unknown&&!j.sender_may_transmit(id(1),id(10),300),"restart automatically resent command");
    JournalEntry remote;remote.request_id=id(1);remote.route=100;remote.command=rate();remote.payload_hash=command_hash(100,rate());remote.state=CommandState::succeeded;remote.result={100,1,true};remote.revision=3;
    check(j.observe_remote(id(1),100,status(remote),300)==JournalError::none&&j.get(id(1)).entry->state==CommandState::succeeded,"query reconciliation");
    remote.state=CommandState::accepted;remote.result={};remote.revision=1;
    check(j.observe_remote(id(1),100,status(remote),400)==JournalError::invalid_state,"late status downgraded result");
}
void storage_and_capacity(){
    auto o=options("capacity.sqlite");o.max_entries=4;
    {CommandJournal j(o);for(unsigned i=1;i<=4;++i)check(bool(j.admit(id(i),100,rate(),context(),100)),"capacity admission");
        check(j.admit(id(5),100,rate(),context(),100).error==JournalError::capacity,"entry capacity exceeded");
        check(j.get(id(1)).entry.has_value(),"capacity evicted history");}
    o=options("quota.sqlite");o.max_bytes=262144;o.wal_bytes=65536;CommandJournal q(o);unsigned count=0;
    q.admit(id(1),100,rate(),context(),100);q.begin_dispatch(id(1),id(10),true,200);
    // Terminal entries avoid the independent 64 active-admission limit.
    for(unsigned i=2;i<=1000;++i){auto r=q.admit(id(i),100,rate(),context(),6000);if(r.error==JournalError::capacity)break;check(bool(r),"quota admission failed unexpectedly");++count;check(q.file_bytes()<=o.max_bytes,"file budget exceeded");}
    check(count>4&&count<1000,"file reserve did not stop admission");
    check(q.finish(id(1),CommandState::succeeded,CommandReason::none,{100,1,true},7000).entry->result.valid,"reserved result space unavailable at capacity");
    check(q.file_bytes()<=o.max_bytes,"result exceeded file budget");
    auto f=options("full.sqlite");JournalFaults faults;f.test_faults=&faults;
    {CommandJournal j(f);j.admit(id(1),100,rate(),context(),100);j.begin_dispatch(id(1),id(10),true,200);
        faults.full=true;faults.writes_before_failure=0;
        auto result=j.finish(id(1),CommandState::succeeded,CommandReason::none,{100,1,true},300);
        check(result.error==JournalError::storage&&!result.entry&&!j.healthy(),"disk-full reported success");
        check(j.get(id(1)).error==JournalError::storage,"errored connection exposed unverified state");}
    f.test_faults=nullptr;CommandJournal recovered(f);check(recovered.get(id(1)).entry->state==CommandState::unknown,"disk-full result not UNKNOWN at recovery");
    auto s=options("sync.sqlite");JournalFaults sync;s.test_faults=&sync;
    {CommandJournal j(s);sync.syncs_before_failure=0;const auto result=j.admit(id(1),100,rate(),context(),100);
        check(result.error==JournalError::storage&&!result.entry,"sync error reported ACCEPTED");}
}
}
int main(){try{root=std::filesystem::current_path()/("journal-artifacts-"+std::to_string(getpid()));for(unsigned suffix=0;std::filesystem::exists(root);++suffix)root=std::filesystem::current_path()/("journal-artifacts-"+std::to_string(getpid())+"-"+std::to_string(suffix));
    std::filesystem::create_directories(root);
    basic();recovery_and_sender();storage_and_capacity();std::cout<<"PASS journal contract: "<<checks<<" checks, WAL/FULL, quota and storage faults\n";
}catch(const std::exception& e){std::cerr<<"FAIL: "<<e.what()<<'\n';return 1;}}
