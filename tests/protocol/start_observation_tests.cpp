#include "../../src/robotweax_srt_bridge_core/src/worker/execution_pool.hpp"
#include <sys/wait.h>
#include <unistd.h>
#include <iostream>
#include <stdexcept>
using namespace robotweax::srt_bridge;
using namespace robotweax::srt_bridge::execution_detail;
namespace {
unsigned checks=0;
void check(bool b,const char* s){++checks;if(!b)throw std::runtime_error(s);}
JournalEntry entry(){JournalEntry e;e.request_id[0]=std::byte{7};e.context.deadline_ns=10000;e.payload_hash[0]=std::byte{42};return e;}
WorkerStartObservation data(){return {100,200,110,200,1,true,true};}
void contract(){
 auto live=std::make_shared<std::atomic<bool>>(true);
 auto off=Pool::create();auto r=off->allocate(entry(),"robot","operator",live);off->publish_observation(r->slot,r->generation,data());check(!off->observation(*r),"disabled diagnostics published");
 auto p=Pool::create(true);r=p->allocate(entry(),"robot","operator",live);check(!p->observation(*r),"unpopulated diagnostics invented");
 p->publish_observation(64,r->generation,data());p->publish_observation(r->slot,r->generation+1,data());check(!p->observation(*r),"wrong slot/generation published");
 p->publish_observation(r->slot,r->generation,data());auto o=p->observation(*r);check(o&&o->consume_ns==100&&o->second_gate_checked&&o->handler_invoked,"snapshot lost fields");
 auto altered=data();altered.consume_ns=999;p->publish_observation(r->slot,r->generation,altered);check(p->observation(*r)->consume_ns==100,"observation overwritten");
 const auto slot=r->slot;const auto old_generation=r->generation;r.reset();auto next=p->allocate(entry(),"robot","operator",live);check(next->slot==slot&&next->generation>old_generation,"slot reuse did not advance");check(!p->observation(*next),"stale observation survived reuse");
 p->publish_observation(slot,old_generation,data());check(!p->observation(*next),"old child published to reused slot");
 p->publish_observation(next->slot,next->generation,data());check(bool(p->observation(*next)),"new generation cannot publish");
 const auto fd=p->fd();std::uint64_t wrong=1;check(pwrite(fd,&wrong,8,8)==8,"header corruption fixture");bool rejected=false;try{auto m=Pool::map(fd);(void)m;}catch(...){rejected=true;}check(rejected,"old mapping version accepted");wrong=2;check(pwrite(fd,&wrong,8,8)==8,"header restoration");
 wrong=2;check(pwrite(fd,&wrong,8,16)==8,"flag fixture");rejected=false;try{auto m=Pool::map(fd);(void)m;}catch(...){rejected=true;}check(rejected,"unknown mapping flags accepted");wrong=1;check(pwrite(fd,&wrong,8,16)==8,"flag restoration");
}
void process(){auto p=Pool::create(true);auto r=p->allocate(entry(),"robot","operator",std::make_shared<std::atomic<bool>>(true));auto pid=fork();check(pid>=0,"fork");if(!pid){try{auto m=Pool::map(p->fd());m->publish_observation(r->slot,r->generation,data());_exit(0);}catch(...){_exit(3);}}
 int status=0;check(waitpid(pid,&status,0)==pid&&WIFEXITED(status)&&WEXITSTATUS(status)==0,"child failed");auto o=p->observation(*r);check(o&&o->consume_result==1&&o->second_gate_ns==110,"shared publication missing");}
}
int main(){try{contract();process();std::cout<<"PASS start observation "<<checks<<" checks\n";return 0;}catch(const std::exception&e){std::cerr<<e.what()<<"\n";return 1;}}
