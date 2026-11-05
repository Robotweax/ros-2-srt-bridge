#include "../../src/robotweax_srt_bridge_core/src/worker/execution_pool.hpp"
#include <robotweax/srt_bridge/session.hpp>
#include <barrier>
#include <chrono>
#include <iostream>
#include <thread>
#include <vector>
#include <sys/wait.h>
#include <unistd.h>
using namespace robotweax::srt_bridge;
using namespace robotweax::srt_bridge::execution_detail;
namespace {
unsigned checks=0;
void check(bool ok,const char* text){++checks;if(!ok)throw std::runtime_error(text);}
std::uint64_t now(){return std::chrono::duration_cast<std::chrono::nanoseconds>(std::chrono::steady_clock::now().time_since_epoch()).count();}
JournalEntry entry(){JournalEntry e;e.request_id=random_identity();e.context.deadline_ns=now()+10000000000ULL;e.command={100,5000,0,1};e.route=100;e.payload_hash=command_hash(e.route,e.command);return e;}
void capacity(){auto p=Pool::create();auto live=std::make_shared<std::atomic<bool>>(true);std::vector<std::shared_ptr<Record>> held;
    for(unsigned n=0;n<64;++n){auto r=p->allocate(entry(),"robot","operator",live);check(bool(r),"missing slot");held.push_back(r);}
    check(!p->allocate(entry(),"robot","operator",live),"pool grew beyond 64");
    const auto slot=held[0]->slot;const auto generation=held[0]->generation;p->revoke_all();for(auto& r:held)check(p->state(*r)==State::revoked,"prepared grant not revoked");held.clear();
    auto r=p->allocate(entry(),"robot","operator",live);check(r->slot==slot&&r->generation>generation,"generation reset");
    check(p->grant(*r,r->entry.context.deadline_ns),"grant failed");
    check(p->consume(slot,generation,r->entry.request_id,r->entry.payload_hash,now())==Start::invalid,"stale generation consumed");
    check(p->consume(r->slot,r->generation,random_identity(),r->entry.payload_hash,now())==Start::invalid,"wrong ID consumed");
    auto hash=r->entry.payload_hash;hash[0]^=std::byte{1};check(p->consume(r->slot,r->generation,r->entry.request_id,hash,now())==Start::invalid,"wrong hash consumed");
    check(p->consume(r->slot,r->generation,r->entry.request_id,r->entry.payload_hash,now())==Start::started,"correct start failed");p->revoke_all();check(p->state(*r)==State::running,"revocation stopped already running handler");
    check(p->consume(r->slot,r->generation,r->entry.request_id,r->entry.payload_hash,now())!=Start::started,"grant consumed twice");p->complete(r->slot,r->generation);check(p->state(*r)==State::finished,"completion missing");r.reset();
    r=p->allocate(entry(),"robot","operator",live);check(p->grant(*r,1),"expiry fixture grant failed");check(p->consume(r->slot,r->generation,r->entry.request_id,r->entry.payload_hash,now())==Start::expired,"expired grant consumed");p->revoke(*r);r.reset();
    r=p->allocate(entry(),"robot","operator",live);live->store(false);check(!p->grant(*r,r->entry.context.deadline_ns),"dead worker granted");
}
void process(){auto p=Pool::create();auto r=p->allocate(entry(),"robot","operator",std::make_shared<std::atomic<bool>>(true));check(p->grant(*r,r->entry.context.deadline_ns),"process fixture grant");
    const auto pid=fork();check(pid>=0,"fork failed");if(!pid){try{auto child=Pool::map(p->fd());if(child->consume(r->slot,r->generation,r->entry.request_id,r->entry.payload_hash,now())!=Start::started)_exit(2);child->complete(r->slot,r->generation);_exit(0);}catch(...){_exit(3);}}
    int status=0;check(waitpid(pid,&status,0)==pid&&WIFEXITED(status)&&WEXITSTATUS(status)==0,"mapped child start failed");check(p->state(*r)==State::finished,"child state not shared");
}
void races(){auto p=Pool::create();auto live=std::make_shared<std::atomic<bool>>(true);std::shared_ptr<Record> record;Start result=Start::invalid;std::barrier sync(3);constexpr unsigned rounds=5000;
    std::thread consumer([&]{for(unsigned n=0;n<rounds;++n){sync.arrive_and_wait();auto r=record;result=p->consume(r->slot,r->generation,r->entry.request_id,r->entry.payload_hash,now());sync.arrive_and_wait();}});
    std::thread revoker([&]{for(unsigned n=0;n<rounds;++n){sync.arrive_and_wait();auto r=record;p->revoke(*r);sync.arrive_and_wait();}});
    bool valid=true;
    for(unsigned n=0;n<rounds;++n){record=p->allocate(entry(),"robot","operator",live);if(!record||!p->grant(*record,record->entry.context.deadline_ns))std::terminate();sync.arrive_and_wait();sync.arrive_and_wait();const auto state=p->state(*record);
        valid=valid&&((result==Start::started&&state==State::running)||(result==Start::revoked&&state==State::revoked));if(result==Start::started)p->complete(record->slot,record->generation);record.reset();++checks;}
    consumer.join();revoker.join();check(valid,"revocation/start race had two winners or no winner");
}
}
int main(){try{capacity();process();races();std::cout<<"PASS execution fence: "<<checks<<" checks\n";return 0;}catch(const std::exception& e){std::cerr<<"FAIL: "<<e.what()<<"\n";return 1;}}
