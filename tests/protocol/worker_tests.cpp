#include <robotweax/srt_bridge/worker.hpp>
#include <robotweax/srt_bridge/session.hpp>
#include "../../src/robotweax_srt_bridge_core/src/worker/ipc.hpp"
#include <chrono>
#include <filesystem>
#include <iostream>
#include <thread>
#include <unistd.h>
#include <vector>
using namespace robotweax::srt_bridge;
namespace {
unsigned checks=0;
void check(bool value,const char* text){++checks;if(!value)throw std::runtime_error(text);}
std::uint64_t now(){return std::chrono::duration_cast<std::chrono::nanoseconds>(std::chrono::steady_clock::now().time_since_epoch()).count();}
template<class F> void until(F test,const char* text){const auto end=now()+5000000000ULL;while(!test()){if(now()>=end)throw std::runtime_error(text);std::this_thread::sleep_for(std::chrono::milliseconds(1));}++checks;}
void ready(JournalWorker& w){WorkerReply ignored;until([&]{w.poll(ignored);return w.state()==WorkerState::ready||w.state()==WorkerState::failed;},"worker readiness timeout");check(w.state()==WorkerState::ready,"worker failed at startup");}
WorkerReply rpc(JournalWorker& w,WorkerRequest q){WorkerSubmission s;until([&]{s=w.submit(q);return s.result!=WorkerSubmit::busy;},"IPC admission timeout");check(s.result==WorkerSubmit::queued,"IPC admission failed");WorkerReply r;until([&]{return w.poll(r);},"IPC response timeout");check(r.token==s.token&&r.operation==q.operation,"wrong IPC correlation");return r;}
WorkerOptions options(const std::filesystem::path& dir,std::string name,JournalSide side){WorkerOptions o;o.executable=WORKER_EXECUTABLE;o.journal.path=(dir/(name+".sqlite")).string();o.journal.local_peer_id=side==JournalSide::sender?"operator":"robot";o.journal.remote_peer_id=side==JournalSide::sender?"robot":"operator";o.journal.side=side;o.journal.process_epoch=random_identity();return o;}
WorkerRequest admission(const WorkerOptions& o){WorkerRequest q;q.operation=WorkerOperation::admit;q.request_id=random_identity();q.route=100;q.command={100,5000,0,1};const auto origin=now();q.context={random_identity(),o.journal.process_epoch,origin,origin+5000000000ULL};return q;}
void stopped(JournalWorker& w){const auto start=now();w.request_stop();check(w.join(),"worker not reaped");check(now()-start<5000000000ULL,"worker shutdown exceeded five seconds");check(w.state()==WorkerState::stopped&&w.pending()==0,"worker not stopped cleanly");check(w.join(),"repeat join failed");}
void basic(const std::filesystem::path& dir){
    auto sender_options=options(dir,"sender",JournalSide::sender);JournalWorker sender(sender_options);ready(sender);
    auto q=admission(sender_options);auto r=rpc(sender,q);check(r.journal&&r.journal.entry->state==CommandState::local_queued&&r.ticket.has_value(),"no committed sender ticket");
    auto duplicate=rpc(sender,q);check(duplicate.journal&&!duplicate.journal.inserted&&!duplicate.ticket,"duplicate minted ticket");
    auto changed=q;changed.command.rate_hz=300;auto conflict=rpc(sender,changed);check(conflict.journal.error==JournalError::conflict&&!conflict.ticket,"conflict minted ticket");
    auto get=q;get.operation=WorkerOperation::get;r=rpc(sender,get);check(r.journal&&!r.ticket,"GET minted ticket");
    auto may=get;may.operation=WorkerOperation::sender_may_transmit;may.session=q.context.session;r=rpc(sender,may);check(r.may_transmit,"sender permission missing");
    auto invalid=get;invalid.operation=WorkerOperation::invalidate_session;invalid.session=q.context.session;r=rpc(sender,invalid);check(r.journal.error==JournalError::none,"invalidation failed");
    r=rpc(sender,get);check(r.journal.entry->state==CommandState::unknown,"sender not UNKNOWN on context loss");
    auto expired=admission(sender_options);expired.context.source_monotonic_ns=now()-6000000000ULL;expired.context.deadline_ns=expired.context.source_monotonic_ns+5000000000ULL;
    auto expired_reply=rpc(sender,expired);check(expired_reply.journal.entry->state==CommandState::expired&&!expired_reply.ticket,"expired admission minted ticket");
    stopped(sender);
    JournalWorker reopened(sender_options);ready(reopened);r=rpc(reopened,get);check(r.journal.entry->state==CommandState::unknown&&!r.ticket,"restart replayed sender");stopped(reopened);

    auto receiver_options=options(dir,"receiver",JournalSide::receiver);JournalWorker receiver(receiver_options);ready(receiver);
    q=admission(receiver_options);r=rpc(receiver,q);check(r.journal.entry->state==CommandState::accepted&&!r.ticket,"receiver minted sender ticket");
    auto dispatch=q;dispatch.operation=WorkerOperation::begin_dispatch;dispatch.session=q.context.session;dispatch.clock_qualified=false;
    r=rpc(receiver,dispatch);check(r.journal.error==JournalError::clock_unqualified,"unqualified dispatch accepted");
    dispatch.clock_qualified=true;r=rpc(receiver,dispatch);check(r.journal.entry->state==CommandState::dispatching,"dispatch missing");
    auto finish=q;finish.operation=WorkerOperation::finish;finish.state=CommandState::succeeded;finish.result={100,1,true};
    r=rpc(receiver,finish);check(r.journal.entry->state==CommandState::succeeded&&r.journal.entry->result==finish.result,"result missing");
    auto denied=admission(receiver_options);check(bool(rpc(receiver,denied).journal),"decline fixture admission failed");auto decline=denied;decline.operation=WorkerOperation::decline;decline.state=CommandState::expired;decline.reason=CommandReason::start_deadline;
    auto declined=rpc(receiver,decline);check(declined.journal.entry->state==CommandState::expired&&declined.journal.entry->revision==2,"pre-dispatch decline not durable");check(rpc(receiver,decline).journal.error==JournalError::invalid_state,"terminal decline changed result");
    auto second=admission(receiver_options);check(bool(rpc(receiver,second).journal),"second admission failed");
    stopped(receiver);JournalWorker recovery(receiver_options);ready(recovery);
    get=q;get.operation=WorkerOperation::get;r=rpc(recovery,get);check(r.journal.entry->state==CommandState::succeeded,"terminal result lost");
    get.request_id=second.request_id;r=rpc(recovery,get);check(r.journal.entry->state==CommandState::rejected&&r.journal.entry->reason==CommandReason::context_lost,"accepted recovery unsafe");
    // Exercise bounded parent outstanding storage without consuming child replies.
    std::vector<std::uint64_t> tokens;
    get.request_id=random_identity();
    for(unsigned i=0;i<1000;++i){const auto s=recovery.submit(get);if(s.result==WorkerSubmit::busy)break;check(s.result==WorkerSubmit::queued,"unexpected batch admission");tokens.push_back(s.token);}
    check(!tokens.empty()&&tokens.size()<=64&&recovery.pending()==tokens.size(),"unbounded IPC outstanding requests");
    // Kernel backpressure may clear as the child drains requests even without
    // parent polling. Only the fixed outstanding limit must remain stable.
    if(tokens.size()==64)check(recovery.submit(get).result==WorkerSubmit::busy,"logical IPC capacity exceeded");
    for(const auto token:tokens){until([&]{return recovery.poll(r);},"batch reply missing");check(r.token==token&&r.journal.error==JournalError::not_found,"IPC FIFO/correlation lost");}
    check(recovery.pending()==0,"pending entries leaked");stopped(recovery);
}
void paused(const std::filesystem::path& dir,JournalPoint point,CommandState expected){
    auto o=options(dir,"pause-"+std::to_string(unsigned(point)),JournalSide::receiver);o.test_pause_at=point;JournalWorker child(o);ready(child);
    auto q=admission(o);WorkerReply reply;
    if(point==JournalPoint::dispatch_committed||point==JournalPoint::result_before_commit||point==JournalPoint::result_committed){check(bool(rpc(child,q).journal),"crash fixture admission failed");q.operation=WorkerOperation::begin_dispatch;q.session=q.context.session;q.clock_qualified=true;}
    if(point==JournalPoint::result_before_commit||point==JournalPoint::result_committed){check(bool(rpc(child,q).journal),"crash fixture dispatch failed");q.operation=WorkerOperation::finish;q.state=CommandState::succeeded;q.result={100,1,true};}
    const auto s=child.submit(q);check(s.result==WorkerSubmit::queued,"pause request rejected");
    until([&]{return child.poll(reply);},"worker barrier missing");check(reply.test_paused&&reply.token==s.token&&child.pending()==1,"wrong worker barrier");
    stopped(child);check(child.fault()==WorkerFault::none,"forced stop reported a protocol error");
    o.test_pause_at.reset();JournalWorker recovery(o);ready(recovery);q.operation=WorkerOperation::get;reply=rpc(recovery,q);
    if(point==JournalPoint::admission_before_commit)check(reply.journal.error==JournalError::not_found,"uncommitted admission survived");
    else check(reply.journal&&reply.journal.entry->state==expected,"wrong worker recovery state");
    stopped(recovery);
}
void faults(const std::filesystem::path& dir){
    auto o=options(dir,"write-fault",JournalSide::sender);o.test_faults=JournalFaults{0,-1,true};JournalWorker w(o);ready(w);auto q=admission(o);auto r=rpc(w,q);
    check(r.journal.error==JournalError::storage&&!r.ticket&&w.fault()==WorkerFault::storage,"storage failure minted ticket or remained healthy");stopped(w);
    auto sync_options=options(dir,"sync-fault",JournalSide::sender);sync_options.test_faults=JournalFaults{-1,0,false};JournalWorker sync(sync_options);ready(sync);auto sync_request=admission(sync_options);auto sync_reply=rpc(sync,sync_request);check(sync_reply.journal.error==JournalError::storage&&!sync_reply.ticket&&sync.fault()==WorkerFault::storage,"sync failure minted ticket");stopped(sync);
    auto invalid=o;invalid.executable="/nonexistent/robotweax-journal-worker";bool rejected=false;std::unique_ptr<JournalWorker> missing;try{missing=std::make_unique<JournalWorker>(invalid);}catch(const std::exception&){rejected=true;}if(missing){WorkerReply ignored;until([&]{missing->poll(ignored);return missing->state()==WorkerState::failed;},"missing executable did not fail");rejected=true;}check(rejected,"missing executable accepted");
    o=options(dir,"early-stop",JournalSide::sender);JournalWorker early(o);stopped(early);check(early.fault()==WorkerFault::none,"early stop created protocol failure");
    q.operation=WorkerOperation::get;check(early.submit(q).result==WorkerSubmit::stopped,"post-stop request accepted");
}
void backend_configuration(const std::filesystem::path& dir){
    for(bool conflicting:{false,true}){
        auto o=options(dir,conflicting?"conflicting-handlers":"missing-backend",JournalSide::receiver);
        o.external_rate_handler=true;o.simulated_rate_handler=conflicting;
        JournalWorker child(o);WorkerReply reply;
        until([&]{child.poll(reply);return child.state()==WorkerState::failed;},"invalid backend configuration remained ready");
        check(child.fault()==WorkerFault::configuration,"backend error misclassified as storage");
        check(child.join(),"invalid backend child not reaped");
        check(!std::filesystem::exists(o.journal.path),"invalid backend created journal");
    }
}
void codec(){
    namespace ipc=worker_ipc;WorkerRequest q;q.operation=WorkerOperation::admit;q.request_id=random_identity();q.route=100;q.command={200,5000,8,9};q.context.source_monotonic_ns=99;
    const auto frame=ipc::encode(q,7);ipc::Reader r(frame);auto copy=ipc::request(r);check(copy.request_id==q.request_id&&copy.command==q.command&&copy.context.source_monotonic_ns==99&&r.token==7,"IPC roundtrip");
    auto old=frame;old[5]=std::byte{3};bool refused=false;try{ipc::Reader obsolete(old);}catch(const std::exception&){refused=true;}check(refused,"old IPC worker version accepted");
    q.operation=WorkerOperation::reconcile_sender;const auto receipt=ipc::encode(q,9);ipc::Reader receipt_reader(receipt);check(ipc::request(receipt_reader).operation==WorkerOperation::reconcile_sender,"receipt IPC operation missing");
    std::uint64_t seed=17;
    for(unsigned n=0;n<5000;++n){auto mutation=frame;seed=seed*6364136223846793005ULL+1;mutation[(seed>>16)%mutation.size()]^=std::byte((seed>>32)|1);
        try{ipc::Reader reader(mutation);(void)ipc::request(reader);}catch(const std::exception&){}++checks;}
}
}
int main(){try{auto dir=std::filesystem::current_path()/("worker-"+std::to_string(getpid()));for(unsigned n=0;std::filesystem::exists(dir);++n)dir=std::filesystem::current_path()/("worker-"+std::to_string(getpid())+"-"+std::to_string(n));std::filesystem::create_directories(dir);
    codec();backend_configuration(dir);basic(dir);paused(dir,JournalPoint::admission_before_commit,CommandState::unknown);paused(dir,JournalPoint::admission_committed,CommandState::rejected);paused(dir,JournalPoint::dispatch_committed,CommandState::unknown);paused(dir,JournalPoint::result_before_commit,CommandState::unknown);paused(dir,JournalPoint::result_committed,CommandState::succeeded);faults(dir);
    std::cout<<"PASS process journal worker: "<<checks<<" checks\n";return 0;}catch(const std::exception& e){std::cerr<<"FAIL: "<<e.what()<<"\n";return 1;}}
