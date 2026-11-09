#include <robotweax/srt_bridge/endpoint.hpp>
#include <chrono>
#include <cstdlib>
#include <filesystem>
#include <iostream>
#include <thread>
#include <unistd.h>
using namespace robotweax::srt_bridge;
namespace {
unsigned checks=0;
void check(bool ok,const char* text){++checks;if(!ok)throw std::runtime_error(text);}
uint64_t now(){return TransportOwner::monotonic_ns();}
template<class F>void until(F f,const char* text){const auto end=now()+7000000000ULL;while(!f()){check(now()<end,text);std::this_thread::sleep_for(std::chrono::milliseconds(1));}}
std::string secret(){std::string s;constexpr char h[]="0123456789abcdef";for(auto b:random_identity()){auto n=std::to_integer<unsigned>(b);s+=h[n>>4];s+=h[n&15];}return s;}
TransportConfig config(Role role,const std::string& ip,const std::string& key){
    Route route{100,RouteKind::command,Direction::listener_to_caller,QosMapping::request_status,true,4000,5000,0,1,"robotweax.srt_bridge.v1.SetMeasurementRateCommand",rate_command_schema_hash()};
    return {{role,role==Role::caller?"robot":"operator",role==Role::caller?"operator":"robot",random_identity(),role==Role::caller?1U:2U,*make_manifest(std::span(&route,1)).value,{1000,1000000,5000000000ULL,100000000}},{ip,0},{ip,0},key};
}
WorkerOptions options(const std::filesystem::path& path,const TransportConfig& c){WorkerOptions w;w.executable=WORKER_EXECUTABLE;w.journal.path=path.string();w.journal.local_peer_id=c.session.local_peer_id;w.journal.remote_peer_id=c.session.expected_peer_id;w.journal.process_epoch=c.session.local_epoch;w.journal.side=c.session.role==Role::listener?JournalSide::sender:JournalSide::receiver;return w;}
void ready(JournalWorker& w){WorkerReply r;until([&]{w.poll(r);return w.state()==WorkerState::ready||w.state()==WorkerState::failed;},"worker readiness");check(w.state()==WorkerState::ready,"worker failed");}
WorkerReply rpc(JournalWorker& w,const WorkerRequest& q,bool resume=true){
    WorkerSubmission s;until([&]{s=w.submit(q);return s.result!=WorkerSubmit::busy;},"RPC busy");check(s.result==WorkerSubmit::queued,"RPC refused");WorkerReply r;until([&]{return w.poll(r);},"RPC reply");check(r.token==s.token,"wrong RPC token");
    if(r.test_paused&&resume){check(w.resume_test_barrier(),"resume failed");until([&]{return w.poll(r);},"resumed RPC reply");check(r.token==s.token&&!r.test_paused,"wrong resumed reply");}return r;
}
WorkerRequest admit(const TransportConfig& c,TransportContext context){WorkerRequest q;q.operation=WorkerOperation::admit;q.request_id=random_identity();q.route=100;q.command={100,5000,0,1};const auto t=now();q.context={context.session,c.session.local_epoch,t,t+5000000000ULL};return q;}
WorkerRequest get(Identity id){WorkerRequest q;q.operation=WorkerOperation::get;q.request_id=id;return q;}
struct Link {
    TransportConfig oc,rc;std::unique_ptr<TransportOwner> op,robot;
    Link(const std::string& ip,bool hold):oc(config(Role::listener,ip,secret())),rc(config(Role::caller,ip,oc.passphrase)){
        oc.test_hold_command_handoff=hold;op=std::make_unique<TransportOwner>(oc);until([&]{return op->snapshot().control_port!=0;},"listen");rc.control.port=op->snapshot().control_port;rc.sensor.port=op->snapshot().sensor_port;robot=std::make_unique<TransportOwner>(rc);
        until([&]{return op->snapshot().state==SessionState::active&&robot->snapshot().state==SessionState::active&&op->snapshot().clock_qualified;},"link ready");
    }
};
void abandoned(const std::string& ip,const std::filesystem::path& dir){
    Link link(ip,true);auto opt=options(dir/"sender.sqlite",link.oc);opt.test_pause_at=JournalPoint::admission_committed;
    SenderSubmissionReceipt stale;
    {JournalWorker w(opt);ready(w);SenderSubmissionReceipt empty;check(w.submit_reconcile(empty).result==WorkerSubmit::invalid,"empty receipt accepted");
        auto a=admit(link.oc,link.op->snapshot().context);auto first=rpc(w,a);check(first.ticket.has_value(),"fresh ticket missing");auto receipt=first.ticket->receipt();auto copy=first.ticket->receipt();
        check(w.submit_reconcile(receipt).result==WorkerSubmit::invalid,"unclaimed receipt accepted");
        check(link.op->submit_command(link.op->snapshot().context,std::move(*first.ticket))==SubmitResult::queued,"claim failed");
        auto cancelled_request=admit(link.oc,link.op->snapshot().context);auto cancelled=rpc(w,cancelled_request);auto cancelled_receipt=cancelled.ticket->receipt();
        check(link.op->abandon_unsubmitted_command(std::move(*cancelled.ticket)),"unsubmitted ticket abandonment failed");
        check(link.op->submit_command(link.op->snapshot().context,std::move(*cancelled.ticket))==SubmitResult::invalid,"abandoned ticket reused");
        auto cs=w.submit_reconcile(cancelled_receipt);check(cs.result==WorkerSubmit::queued,"unsubmitted receipt refused");WorkerReply cr;until([&]{return w.poll(cr);},"unsubmitted receipt reply");check(cr.token==cs.token&&cr.journal.entry&&cr.journal.entry->state==CommandState::unknown,"unsubmitted receipt result");
        auto c=admit(link.oc,link.op->snapshot().context);auto third=rpc(w,c);stale=third.ticket->receipt();check(link.op->submit_command(link.op->snapshot().context,std::move(*third.ticket))==SubmitResult::queued,"second claim failed");
        auto b=admit(link.oc,link.op->snapshot().context);auto paused=rpc(w,b,false);check(paused.test_paused,"expected worker barrier");
        link.robot->request_stop();link.robot->join();until([&]{return receipt.disposition()==SubmissionDisposition::abandoned&&stale.disposition()==SubmissionDisposition::abandoned;},"abandonment missing");
        check(now()<a.context.deadline_ns,"fixture waited for expiry");
        auto foreign_opt=opt;foreign_opt.test_pause_at.reset();foreign_opt.journal.path=(dir/"foreign.sqlite").string();JournalWorker foreign(foreign_opt);ready(foreign);
        check(foreign.submit_reconcile(receipt).result==WorkerSubmit::invalid,"foreign worker consumed receipt");foreign.request_stop();check(foreign.join(),"foreign shutdown");
        WorkerRequest raw;raw.operation=WorkerOperation::reconcile_sender;raw.request_id=a.request_id;check(w.submit(raw).result==WorkerSubmit::invalid,"raw forged reconciliation accepted");
        unsigned queued=0;for(unsigned n=0;n<64;++n){auto s=w.submit(get(b.request_id));if(s.result==WorkerSubmit::busy)break;check(s.result==WorkerSubmit::queued,"pipeline error");++queued;}
        check(queued>0&&w.pending()<=64,"pipeline not bounded");check(w.submit_reconcile(receipt).result==WorkerSubmit::busy,"receipt BUSY missing");
        check(w.resume_test_barrier(),"pipeline resume");WorkerReply r;until([&]{while(w.poll(r)){}return w.pending()==0;},"pipeline drain");
        check(rpc(w,get(a.request_id)).journal.entry->state==CommandState::local_queued,"journal changed without receipt RPC");
        WorkerSubmission submitted;until([&]{submitted=w.submit_reconcile(receipt);return submitted.result!=WorkerSubmit::busy;},"receipt submit busy");check(submitted.result==WorkerSubmit::queued,"receipt consumed on BUSY");
        check(w.submit_reconcile(copy).result==WorkerSubmit::invalid,"duplicate receipt submitted");until([&]{return w.poll(r);},"receipt reply");
        check(r.operation==WorkerOperation::reconcile_sender&&r.token==submitted.token&&r.journal.entry&&r.journal.entry->state==CommandState::unknown&&r.journal.entry->reason==CommandReason::reconcile_required&&!r.journal.entry->revision&&!r.journal.entry->result.valid,"receipt journal result");
        check(rpc(w,get(b.request_id)).journal.entry->state==CommandState::local_queued,"unrelated sender invalidated");
        check(!rpc(w,a).ticket,"duplicate admission minted ticket");w.request_stop();check(w.join(),"sender shutdown");
    }
    opt.test_pause_at.reset();JournalWorker replacement(opt);ready(replacement);check(replacement.submit_reconcile(stale).result==WorkerSubmit::invalid,"old generation receipt accepted");replacement.request_stop();check(replacement.join(),"replacement shutdown");link.op->request_stop();link.op->join();
    std::cout<<"RECEIPT_CONTRACT abandonment=UNKNOWN unrelated=queued busy_preserved=1 forged_stale_reuse_refused=1 no_expiry=1\n";
}
void accepted(const std::string& ip,const std::filesystem::path& dir){
    Link link(ip,false);JournalWorker w(options(dir/"accepted.sqlite",link.oc));ready(w);auto q=admit(link.oc,link.op->snapshot().context);auto r=rpc(w,q);auto receipt=r.ticket->receipt();check(link.op->submit_command(link.op->snapshot().context,std::move(*r.ticket))==SubmitResult::queued,"send claim");until([&]{return receipt.disposition()==SubmissionDisposition::sdk_accepted;},"SDK receipt missing");
    link.robot->request_stop();link.robot->join();link.op->request_stop();link.op->join();check(receipt.disposition()==SubmissionDisposition::sdk_accepted&&w.submit_reconcile(receipt).result==WorkerSubmit::invalid,"SDK acceptance regressed to dropped");w.request_stop();check(w.join(),"accepted worker shutdown");
}
void endpoint(const std::string& ip,const std::filesystem::path& dir){
    auto oc=config(Role::listener,ip,secret());oc.test_hold_command_handoff=true;oc.command_trace=std::make_shared<CommandTrace>();oc.sender_diagnostics=true;CommandEndpoint op({oc,options(dir/"endpoint-sender.sqlite",oc)});
    until([&]{return op.snapshot().transport.control_port!=0;},"endpoint listen");auto rc=config(Role::caller,ip,oc.passphrase);rc.control.port=op.snapshot().transport.control_port;rc.sensor.port=op.snapshot().transport.sensor_port;auto rw=options(dir/"endpoint-receiver.sqlite",rc);rw.simulated_rate_handler=true;CommandEndpoint robot({rc,rw});until([&]{return op.snapshot().ready&&robot.snapshot().ready;},"endpoint ready");
    auto id=random_identity();check(op.execute(100,id,{100,5000,0,1},now())==SubmitResult::queued,"endpoint submit");until([&]{return op.snapshot().commands_sent==1;},"endpoint volatile admission");robot.request_stop();robot.join();check(robot.snapshot().effects==0,"held command executed");
    bool receipt=false,unknown=false;CommandEvent event;CommandTraceEvent trace;
    until([&]{while(op.poll(event))if(event.request_id==id&&event.entry&&event.entry->state==CommandState::unknown&&event.entry->reason==CommandReason::reconcile_required)unknown=true;
        while(oc.command_trace->poll(trace)){if(trace.point==CommandTracePoint::sender_journal&&trace.detail==unsigned(WorkerOperation::reconcile_sender)&&trace.request==id)receipt=true;check(trace.point!=CommandTracePoint::provider_sent,"held command handed to SDK");}return receipt&&unknown;},"coordinator did not service receipt");
    check(op.snapshot().fault==EndpointFault::none,"receipt endpoint fault");
    auto restarted_options=options(dir/"endpoint-restarted-receiver.sqlite",rc);restarted_options.simulated_rate_handler=true;CommandEndpoint restarted({rc,restarted_options});until([&]{return op.snapshot().ready&&restarted.snapshot().ready;},"endpoint reconnect");
    check(op.query(100,id)==SubmitResult::queued,"UNKNOWN query refused");until([&]{while(op.poll(event))if(event.request_id==id&&event.entry&&event.entry->state==CommandState::unknown)return true;return false;},"UNKNOWN not queryable");op.request_stop();op.join();restarted.request_stop();restarted.join();check(restarted.snapshot().effects==0,"query replayed command");check(oc.command_trace->dropped()==0,"trace overflow");
    std::cout<<"RECEIPT_ENDPOINT operation11=observed UNKNOWN=queryable SDK_handoffs=0 effects=0\n";
}
void capacity(const std::string& ip,const std::filesystem::path& dir){
    auto oc=config(Role::listener,ip,secret());CommandEndpoint op({oc,options(dir/"capacity.sqlite",oc)});until([&]{return op.snapshot().transport.control_port!=0;},"capacity listen");auto rc=config(Role::caller,ip,oc.passphrase);rc.control.port=op.snapshot().transport.control_port;rc.sensor.port=op.snapshot().transport.sensor_port;TransportOwner peer(rc);until([&]{return op.snapshot().ready&&peer.snapshot().state==SessionState::active;},"capacity ready");
    const auto origin=now();CommandEvent event;
    for(unsigned n=0;n<64;++n){auto id=random_identity();check(op.execute(100,id,{100,5000,0,1},now())==SubmitResult::queued,"capacity task refused");until([&]{while(op.poll(event))if(event.request_id==id){check(event.error==JournalError::none&&event.entry.has_value(),"capacity admission failed");return true;}return false;},"capacity queued event");}
    check(op.snapshot().tracked==64,"tracking bound missing");auto extra=random_identity();check(op.execute(100,extra,{100,5000,0,1},now())==SubmitResult::queued,"extra task not queued");until([&]{while(op.poll(event))if(event.request_id==extra){check(event.error==JournalError::busy&&!event.entry,"extra admission persisted");return true;}return false;},"capacity BUSY missing");
    check(op.query(100,extra)==SubmitResult::queued,"absent query refused");until([&]{while(op.poll(event))if(event.request_id==extra){check(event.error==JournalError::not_found&&!event.entry,"overflow admission left a journal row");return true;}return false;},"overflow query missing");check(now()-origin<5000000000ULL,"capacity fixture waited for expiry");op.request_stop();op.join();peer.request_stop();peer.join();std::cout<<"RECEIPT_CAPACITY tracked=64 overflow=BUSY absent_journal=1\n";
}
}
int main(int argc,char** argv){try{check(argc==2,"family required");std::string family=argv[1];check(family=="ipv4"||family=="ipv6","family");const auto ip=family=="ipv4"?"127.0.0.1":"::1";const char* output=std::getenv("RECEIPT_OUTPUT");const auto root=output?std::filesystem::path(output)/family:std::filesystem::path("/tmp")/("sender-receipt-"+std::to_string(getpid()));check(!std::filesystem::exists(root),"output exists");std::filesystem::create_directories(root);
    abandoned(ip,root);accepted(ip,root);endpoint(ip,root);capacity(ip,root);std::cout<<"PASS sender receipt "<<family<<" checks="<<checks<<'\n';if(!output)std::filesystem::remove_all(root);
}catch(const std::exception& e){std::cerr<<"FAIL sender receipt: "<<e.what()<<'\n';return 1;}}
