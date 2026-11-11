#include <robotweax/srt_bridge/endpoint.hpp>
#include <chrono>
#include <filesystem>
#include <iostream>
#include <thread>
#include <unistd.h>
#include <vector>
#include <algorithm>
#include "control_gate.hpp"
using namespace robotweax::srt_bridge;
namespace {
unsigned checks=0;
void check(bool ok,const char* text){++checks;if(!ok)throw std::runtime_error(text);}
std::uint64_t now(){return TransportOwner::monotonic_ns();}
template<class F> void until(F f,const char* text){const auto end=now()+8000000000ULL;while(!f()){if(now()>=end)throw std::runtime_error(text);std::this_thread::sleep_for(std::chrono::milliseconds(1));}++checks;}
std::string secret(){std::string key;constexpr char hex[]="0123456789abcdef";for(auto b:random_identity()){auto v=std::to_integer<unsigned>(b);key+=hex[v>>4];key+=hex[v&15];}return key;}
TransportConfig config(Role role,const std::string& ip,const std::string& key,unsigned budget=5000){Route c{100,RouteKind::command,Direction::listener_to_caller,QosMapping::request_status,true,4000,budget,0,1,"robotweax.srt_bridge.v1.SetMeasurementRateCommand",rate_command_schema_hash()};auto d=c;d.id=101;const std::array routes{c,d};SessionConfig s{role,role==Role::caller?"robot":"operator",role==Role::caller?"operator":"robot",random_identity(),role==Role::caller?1U:2U,*make_manifest(routes).value,{1000,1000000,5000000000ULL,100000000}};return {std::move(s),{ip,0},{ip,0},key};}
WorkerOptions worker_options(const TransportConfig& c,const std::filesystem::path& path,JournalSide side){WorkerOptions o;o.executable=WORKER_EXECUTABLE;o.journal.path=path.string();o.journal.local_peer_id=c.session.local_peer_id;o.journal.remote_peer_id=c.session.expected_peer_id;o.journal.process_epoch=c.session.local_epoch;o.journal.side=side;o.simulated_rate_handler=side==JournalSide::receiver;return o;}
void worker_ready(JournalWorker& worker){WorkerReply reply;until([&]{worker.poll(reply);return worker.state()==WorkerState::ready||worker.state()==WorkerState::failed;},"worker not ready");check(worker.state()==WorkerState::ready,"worker failed");}
WorkerReply rpc(JournalWorker& worker,const WorkerRequest& q){WorkerSubmission submitted;until([&]{submitted=worker.submit(q);return submitted.result!=WorkerSubmit::busy;},"worker busy");check(submitted.result==WorkerSubmit::queued,"worker request rejected");WorkerReply reply;until([&]{return worker.poll(reply);},"worker reply missing");check(reply.token==submitted.token,"wrong worker correlation");return reply;}
void send(TransportOwner& op,JournalWorker& worker,Identity epoch,Identity id,RateCommand command){WorkerRequest q;q.operation=WorkerOperation::admit;q.request_id=id;q.route=100;q.command=command;const auto origin=now();q.context={op.snapshot().context.session,epoch,origin,origin+5000000000ULL};auto reply=rpc(worker,q);check(reply.ticket.has_value(),"no fresh send ticket");until([&]{return op.submit_command(op.snapshot().context,std::move(*reply.ticket))==SubmitResult::queued;},"command not queued");}
TransportMessage receive(TransportOwner& owner,Kind kind,Identity id){TransportMessage message;until([&]{while(owner.poll_control(message))if(message.envelope.kind==kind&&message.envelope.request_id==id)return true;return false;},"transport message missing");return message;}
void error(TransportOwner& peer,const TransportMessage& original,ControlErrorCode code,std::uint64_t sequence=0){const ControlError value{code,original.envelope.kind,sequence?sequence:original.envelope.sequence,(code==ControlErrorCode::busy||code==ControlErrorCode::capacity)?250U:0U};until([&]{return peer.submit_error(peer.snapshot().context,original.envelope.route_id,original.envelope.request_id,value)==SubmitResult::queued;},"ERROR submit failed");}
CommandEvent peer_error(CommandEndpoint& endpoint,Identity id,ControlErrorCode code){CommandEvent e;until([&]{while(endpoint.poll(e))if(e.request_id==id&&e.peer_error&&e.peer_error->code==code)return true;return false;},"peer ERROR not observable");check(!e.entry&&e.error!=JournalError::none,"ERROR fabricated a journal status");return e;}
void stop(CommandEndpoint& endpoint){const auto begin=now();endpoint.request_stop();endpoint.join();check(now()-begin<5000000000ULL&&!endpoint.snapshot().running&&endpoint.snapshot().worker==WorkerState::stopped,"endpoint stop failed");}
void receiver_errors(const std::string& ip,const std::filesystem::path& directory){
    const auto key=secret();auto oc=config(Role::listener,ip,key);TransportOwner op(oc);until([&]{return op.snapshot().control_port!=0;},"operator bind failed");
    auto rc=config(Role::caller,ip,key);rc.control.port=op.snapshot().control_port;rc.sensor.port=op.snapshot().sensor_port;rc.command_trace=std::make_shared<CommandTrace>();auto rw=worker_options(rc,directory/"receiver.sqlite",JournalSide::receiver);rw.journal.max_entries=1;CommandEndpoint robot({rc,rw});
    until([&]{return robot.snapshot().ready&&op.snapshot().state==SessionState::active;},"receiver endpoint not ready");
    auto sw=worker_options(oc,directory/"sender.sqlite",JournalSide::sender);JournalWorker sender(sw);worker_ready(sender);
    const auto id=random_identity();const RateCommand original{100,5000,0,1};send(op,sender,oc.session.local_epoch,id,original);
    TransportMessage message;until([&]{while(op.poll_control(message)){if(message.envelope.kind!=Kind::status)continue;auto s=decode_command_status(100,message.body());if(s&&s->state==CommandState::succeeded)return true;}return false;},"initial handler result missing");check(robot.snapshot().effects==1,"first effect missing");
    const auto absent=random_identity();until([&]{return op.submit_query(op.snapshot().context,100,absent)==SubmitResult::queued;},"missing query submit failed");message=receive(op,Kind::error,absent);auto value=decode_control_error(message.body());check(value&&value->code==ControlErrorCode::not_found&&value->request_kind==Kind::query,"missing query got false status");
    until([&]{return op.submit_query(op.snapshot().context,101,id)==SubmitResult::queued;},"wrong-route query submit failed");message=receive(op,Kind::error,id);value=decode_control_error(message.body());check(value&&value->code==ControlErrorCode::conflict&&message.envelope.route_id==101,"wrong-route query not scoped");
    const auto full=random_identity();send(op,sender,oc.session.local_epoch,full,{300,5000,1,2});message=receive(op,Kind::error,full);value=decode_control_error(message.body());check(value&&value->code==ControlErrorCode::capacity&&value->request_kind==Kind::command&&value->retry_after_ms>0,"full journal not peer-visible");
    // Deliberately use an independent sender DB to exercise a conflicting peer
    // payload. Normal endpoint duplicate protection would prevent this send.
    sw.journal.path=(directory/"conflicting-sender.sqlite").string();JournalWorker conflicting(sw);worker_ready(conflicting);send(op,conflicting,oc.session.local_epoch,id,{500,5000,0,1});message=receive(op,Kind::error,id);value=decode_control_error(message.body());check(value&&value->code==ControlErrorCode::conflict&&value->request_kind==Kind::command,"payload conflict got a success response");
    until([&]{return op.submit_query(op.snapshot().context,100,id)==SubmitResult::queued;},"stored query submit failed");message=receive(op,Kind::status,id);auto stored=decode_command_status(100,message.body());check(stored&&stored->state==CommandState::succeeded&&stored->result==RateResult{100,1,true}&&robot.snapshot().effects==1,"errors changed stored result or device effect");
    check(robot.snapshot().transport.errors_sent>=4,"wire errors not counted");check(sender.join()&&conflicting.join(),"sender worker stop failed");op.request_stop();op.join();stop(robot);
    bool admitted=false,missing=false,capacity=false;CommandTraceEvent event;
    while(rc.command_trace->poll(event)){
        if(event.point==CommandTracePoint::control_admission&&event.request==id&&event.detail==unsigned(Kind::command)){
            check(event.value==unsigned(SessionError::none)&&event.request_sequence>0&&event.origin_ns>0&&event.evaluated_ns<=event.monotonic_ns,"admission trace lost envelope/clock provenance");admitted=true;
        }
        if(event.point==CommandTracePoint::receiver_worker_result&&event.request==absent&&event.detail==unsigned(Kind::query))missing=event.value==unsigned(JournalError::not_found)&&event.request_sequence>0;
        if(event.point==CommandTracePoint::receiver_worker_result&&event.request==full&&event.detail==unsigned(Kind::command))capacity=event.value==unsigned(JournalError::capacity)&&event.request_sequence>0;
    }
    check(admitted&&missing&&capacity&&rc.command_trace->dropped()==0,"receiver admission/worker errors not observed separately");
}
void sender_errors(const std::string& ip,const std::filesystem::path& directory){
    const auto key=secret();auto oc=config(Role::listener,ip,key);oc.command_trace=std::make_shared<CommandTrace>();auto sw=worker_options(oc,directory/"sender.sqlite",JournalSide::sender);CommandEndpoint op({oc,sw});until([&]{return op.snapshot().transport.control_port!=0;},"sender bind failed");
    auto rc=config(Role::caller,ip,key);rc.control.port=op.snapshot().transport.control_port;rc.sensor.port=op.snapshot().transport.sensor_port;auto robot=std::make_unique<TransportOwner>(rc);until([&]{return op.snapshot().ready&&robot->snapshot().state==SessionState::active;},"sender endpoint not ready");
    const auto id=random_identity();const RateCommand command{100,5000,0,1};until([&]{return op.execute(100,id,command,now())==SubmitResult::queued;},"sender execution submit failed");auto original=receive(*robot,Kind::command,id);
    check(op.transport().submit_error(op.transport().snapshot().context,100,id,{ControlErrorCode::not_found,Kind::query,1,0})==SubmitResult::invalid,"operator could send ERROR");
    error(*robot,original,ControlErrorCode::busy);auto busy=peer_error(op,id,ControlErrorCode::busy);check(busy.error==JournalError::busy&&busy.peer_context.session==original.envelope.session_id,"BUSY lost request context");until([&]{return op.snapshot().suspended==1;},"BUSY did not suspend query campaign");
    const auto queries=op.snapshot().queries_sent;std::this_thread::sleep_for(std::chrono::milliseconds(1150));check(op.snapshot().queries_sent==queries&&op.snapshot().commands_sent==1,"ERROR retried command or flooded query");TransportMessage pending;while(robot->poll_control(pending)){} // Discard an already-in-flight QUERY.
    until([&]{return op.query(100,id)==SubmitResult::queued;},"explicit query not accepted");auto query=receive(*robot,Kind::query,id);
    const auto unmatched=op.snapshot().transport.unmatched_errors;error(*robot,query,ControlErrorCode::not_found,query.envelope.sequence+1);until([&]{return op.snapshot().transport.unmatched_errors>unmatched;},"unmatched ERROR was trusted");
    error(*robot,query,ControlErrorCode::not_found);peer_error(op,id,ControlErrorCode::not_found);until([&]{return op.snapshot().suspended==1;},"NOT_FOUND kept querying");
    until([&]{return op.query(100,id)==SubmitResult::queued;},"storage diagnostic query not accepted");query=receive(*robot,Kind::query,id);
    const auto wrong_id_count=op.snapshot().transport.unmatched_errors;
    until([&]{return robot->submit_error(robot->snapshot().context,100,random_identity(),{ControlErrorCode::storage,Kind::query,query.envelope.sequence,0})==SubmitResult::queued;},"wrong-ID diagnostic not submitted");
    until([&]{return op.snapshot().transport.unmatched_errors>wrong_id_count;},"wrong-ID ERROR trusted");
    error(*robot,query,ControlErrorCode::storage);const auto storage=peer_error(op,id,ControlErrorCode::storage);
    check(storage.error==JournalError::storage&&op.snapshot().fault==EndpointFault::none&&op.snapshot().worker==WorkerState::ready,"peer storage diagnostic poisoned local journal");
    // Reconnect resumes query-first, never COMMAND. The journal's old local
    // intent becomes UNKNOWN; the peer's diagnostic still cannot replace it.
    robot->request_stop();robot->join();robot.reset();rc.session.local_epoch=random_identity();robot=std::make_unique<TransportOwner>(rc);until([&]{return op.snapshot().ready&&robot->snapshot().state==SessionState::active;},"reconnect failed");query=receive(*robot,Kind::query,id);error(*robot,query,ControlErrorCode::not_found);auto missing=peer_error(op,id,ControlErrorCode::not_found);check(missing.peer_context.session!=busy.peer_context.session&&op.snapshot().commands_sent==1,"new-session error rebound old send");
    until([&]{return op.execute(100,id,command,now())==SubmitResult::queued;},"existing ID not accepted for reconciliation");CommandEvent local;until([&]{while(op.poll(local))if(local.request_id==id&&local.entry&&local.entry->state==CommandState::unknown&&local.entry->reason==CommandReason::reconcile_required)return true;return false;},"ERROR rewrote durable sender state");query=receive(*robot,Kind::query,id);check(op.snapshot().commands_sent==1,"existing ID minted another send");
    // Inject a well-formed peer result to verify precedence. This fixture has
    // no receiver handler and makes no claim that a physical effect occurred.
    CommandStatus status{CommandState::succeeded,CommandReason::none,command,command_hash(100,command),{100,1,true},3};until([&]{return robot->submit_status(robot->snapshot().context,100,id,status)==SubmitResult::queued;},"late status not submitted");
    CommandEvent success;until([&]{while(op.poll(success))if(success.request_id==id&&success.entry&&success.entry->state==CommandState::succeeded)return true;return false;},"late proven status did not resolve uncertainty");
    const auto errors=op.snapshot().peer_errors;error(*robot,query,ControlErrorCode::not_found);until([&]{return op.snapshot().peer_errors>errors;},"late ERROR not processed");
    until([&]{return op.query(100,id)==SubmitResult::queued;},"terminal query not submitted");until([&]{while(op.poll(success)){check(!success.peer_error,"late ERROR displaced known result");if(success.request_id==id&&success.entry&&success.entry->state==CommandState::succeeded)return true;}return false;},"terminal result downgraded by ERROR");check(op.snapshot().tracked==0&&op.snapshot().commands_sent==1,"terminal tracking or send count wrong");
    stop(op);robot->request_stop();robot->join();
    bool command_busy=false,query_missing=false;CommandTraceEvent event;
    while(oc.command_trace->poll(event))if(event.point==CommandTracePoint::peer_error_received&&event.request==id){
        if(event.detail==unsigned(Kind::command)&&event.value==unsigned(ControlErrorCode::busy))command_busy=event.request_sequence==original.envelope.sequence;
        if(event.detail==unsigned(Kind::query)&&event.value==unsigned(ControlErrorCode::not_found))query_missing=event.request_sequence>0;
    }
    check(command_busy&&query_missing&&oc.command_trace->dropped()==0,"peer error trace lost COMMAND versus QUERY correlation");
}
void receiver_clock_diagnostics(const std::string& ip,const std::filesystem::path& directory,const std::string& mode){
    const auto budget=mode=="expiry"?500U:5000U;const auto key=secret();auto oc=config(Role::listener,ip,key,budget);oc.command_trace=std::make_shared<CommandTrace>();
    auto sw=worker_options(oc,directory/"sender.sqlite",JournalSide::sender);CommandEndpoint op({oc,sw});
    until([&]{return op.snapshot().transport.control_port!=0;},"retention sender bind failed");
    auto rc=config(Role::caller,ip,key,budget);rc.control.port=op.snapshot().transport.control_port;rc.sensor.port=op.snapshot().transport.sensor_port;
    rc.session.clock.max_probe_age_ns=150000000;rc.command_trace=std::make_shared<CommandTrace>();
    auto rw=worker_options(rc,directory/"receiver.sqlite",JournalSide::receiver);CommandEndpoint robot({rc,rw});
    until([&]{return op.snapshot().ready&&robot.snapshot().ready&&robot.snapshot().transport.clock_qualified;},"retention endpoints not ready");
    until([&]{return !robot.snapshot().transport.clock_qualified;},"receiver clock gap missing");
    const auto id=random_identity();const RateCommand command{100,budget,0,1};const auto origin=now();
    until([&]{return op.execute(100,id,command,origin)==SubmitResult::queued;},"retention execute not queued");
    std::vector<CommandTraceEvent> receiver;auto collect=[&]{CommandTraceEvent e;while(rc.command_trace->poll(e))receiver.push_back(e);};
    until([&]{collect();return std::any_of(receiver.begin(),receiver.end(),[&](const auto& e){return e.request==id&&e.point==CommandTracePoint::receiver_deferred;});},"receiver did not retain clock-unqualified command");
    if(mode=="recover"){
        CommandEvent event;until([&]{collect();while(op.poll(event))if(event.request_id==id&&event.entry&&event.entry->state==CommandState::succeeded)return true;return false;},"retained command did not complete after qualification");
        check(event.entry->context.source_monotonic_ns==origin&&event.entry->context.deadline_ns==origin+std::uint64_t(budget)*1000000&&event.entry->result==RateResult{100,1,true}&&robot.snapshot().effects==1,"retention renewed intent or wrong effect");
        stop(op);stop(robot);
    }else if(mode=="expiry"){
        CommandEvent event;until([&]{collect();while(op.poll(event))if(event.request_id==id&&event.peer_error&&event.peer_error->request_kind==Kind::command){check(!event.entry&&(event.peer_error->code==ControlErrorCode::clock_unqualified||event.peer_error->code==ControlErrorCode::start_expired),"expiry invented terminal result");return true;}return false;},"expired retention diagnostic missing");
        until([&]{return op.query(100,id)==SubmitResult::queued;},"expiry query not queued");
        bool local=false,missing=false;until([&]{collect();while(op.poll(event))if(event.request_id==id){
            if(event.entry){check(event.entry->state==CommandState::local_queued&&!event.entry->result.valid&&event.entry->context.deadline_ns==origin+std::uint64_t(budget)*1000000,"expired retention changed original uncertainty");local=true;}
            if(event.peer_error&&event.peer_error->request_kind==Kind::query){check(event.peer_error->code==ControlErrorCode::not_found&&!event.entry,"absence invented status");missing=true;}
        }return local&&missing;},"expiry uncertainty query proof missing");
        check(robot.snapshot().effects==0,"expired retained command executed");stop(op);stop(robot);
    }else if(mode=="context"){
        stop(op);until([&]{collect();return std::any_of(receiver.begin(),receiver.end(),[&](const auto& e){return e.request==id&&e.point==CommandTracePoint::receiver_retained_dropped&&e.reason==CommandTraceReason::context_mismatch;});},"context loss did not clear retained command");stop(robot);
    }else{stop(robot);stop(op);}
    collect();CommandTraceEvent e;unsigned sends=0,resumes=0,drops=0;
    while(oc.command_trace->poll(e))if(e.request==id&&e.point==CommandTracePoint::provider_sent)++sends;
    for(const auto& v:receiver)if(v.request==id){
        if(v.point==CommandTracePoint::receiver_resumed){++resumes;check(v.origin_ns==origin&&v.value==0&&v.age_error==0&&v.evaluated_ns<origin+std::uint64_t(budget)*1000000,"resume lacked original fresh budget");}
        if(v.point==CommandTracePoint::receiver_retained_dropped){++drops;if(mode=="shutdown")check(v.reason==CommandTraceReason::shutdown,"shutdown drop reason missing");}
    }
    check(sends==1&&resumes==(mode=="recover"?1U:0U)&&drops==(mode=="recover"?0U:1U)&&!oc.command_trace->dropped()&&!rc.command_trace->dropped(),"retention replay/trace/drop accounting failed");
    check(mode=="recover"||robot.snapshot().effects==0,"dropped retained command affected device");
    sw.journal.process_epoch=random_identity();CommandJournal sender(sw.journal),target(rw.journal);const auto a=sender.get(id),b=target.get(id);
    check(a.entry&&a.entry->context.source_monotonic_ns==origin&&a.entry->context.deadline_ns==origin+std::uint64_t(budget)*1000000,"closed original budget changed");
    if(mode=="recover")check(a.entry->state==CommandState::succeeded&&b.entry&&b.entry->state==CommandState::succeeded&&b.entry->dispatched_ns<b.entry->context.deadline_ns&&a.entry->result==b.entry->result,"closed success/dispatch mismatch");
    else check(a.entry->state==CommandState::unknown&&a.entry->reason==CommandReason::reconcile_required&&!a.entry->result.valid&&b.error==JournalError::not_found&&!sender.sender_may_transmit(id,a.entry->context.session,now()),"dropped retained command invented result/send permission");
    std::cout<<"RECEIVER_RETENTION_NATIVE {\"mode\":\""<<mode<<"\",\"original_budget_ms\":"<<budget<<",\"sdk_handoffs\":"<<sends<<",\"resumes\":"<<resumes<<",\"drops\":"<<drops<<",\"effects\":"<<robot.snapshot().effects<<"}\n";
}

void durable_expiry(const std::string& ip,const std::filesystem::path& directory,bool retained){
    const auto key=secret();auto oc=config(Role::listener,ip,key,500);oc.command_trace=std::make_shared<CommandTrace>();
    auto sw=worker_options(oc,directory/"sender.sqlite",JournalSide::sender);CommandEndpoint op({oc,sw});
    until([&]{return op.snapshot().transport.control_port!=0;},"expiry sender bind missing");
    ControlGate gate(ip=="::1",op.snapshot().transport.control_port);
    auto rc=config(Role::caller,ip,key,500);rc.control.port=gate.listen_port();rc.sensor.port=op.snapshot().transport.sensor_port;rc.command_trace=std::make_shared<CommandTrace>();
    if(retained)rc.session.clock.max_probe_age_ns=150000000;
    auto rw=worker_options(rc,directory/"receiver.sqlite",JournalSide::receiver);auto robot=std::make_unique<CommandEndpoint>(EndpointOptions{rc,rw});
    until([&]{return op.snapshot().ready&&robot->snapshot().ready&&robot->snapshot().transport.clock_qualified;},"expiry endpoints not ready");
    gate.drop_reply=true;
    if(retained)until([&]{return !robot->snapshot().transport.clock_qualified;},"retained expiry clock did not lapse");
    const auto id=random_identity();const RateCommand command{100,500,0,1};const auto origin=now();
    until([&]{return op.execute(100,id,command,origin)==SubmitResult::queued;},"expiry execute not queued");
    until([&]{return now()>origin+650000000;},"expiry gate interval missing");gate.drop_reply=false;
    CommandEvent event;until([&]{while(op.poll(event))if(event.request_id==id&&event.entry&&event.entry->state==CommandState::expired){check(event.entry->reason==CommandReason::start_deadline&&!event.entry->result.valid,"expiry status not authoritative negative");return true;}return false;},"durable expiry result missing");
    check(robot->snapshot().effects==0&&op.snapshot().commands_sent==1&&!gate.failed&&gate.dropped>0,"expiry executed/replayed or gate unproved");
    const auto original_session=op.snapshot().transport.context.session;stop(*robot);robot.reset();rc.session.local_epoch=random_identity();rc.session.clock.max_probe_age_ns=5000000000ULL;rw.journal.process_epoch=rc.session.local_epoch;
    const auto first_trace=rc.command_trace;rc.command_trace=std::make_shared<CommandTrace>();robot=std::make_unique<CommandEndpoint>(EndpointOptions{rc,rw});
    until([&]{return op.snapshot().ready&&robot->snapshot().ready&&op.snapshot().transport.context.session!=original_session;},"expiry receiver restart not ready");
    until([&]{return op.transport().submit_query(op.transport().snapshot().context,100,id)==SubmitResult::queued;},"expiry recovery wire query failed");
    until([&]{while(op.poll(event))if(event.request_id==id&&event.entry&&event.entry->state==CommandState::expired)return true;return false;},"query lost durable expiry");
    until([&]{return op.execute(100,id,command,now())==SubmitResult::queued;},"expiry duplicate reconciliation failed");
    until([&]{while(op.poll(event))if(event.request_id==id&&event.entry&&event.entry->state==CommandState::expired)return true;return false;},"duplicate expiry lost record");
    const auto fresh=random_identity();until([&]{return op.execute(100,fresh,command,now())==SubmitResult::queued;},"later fresh command not queued");
    until([&]{while(op.poll(event))if(event.request_id==fresh&&event.entry&&event.entry->state==CommandState::succeeded)return true;return false;},"expired intent blocked later fresh work");
    check(op.snapshot().commands_sent==2&&robot->snapshot().effects==1,"expiry replay or fresh generation failed");stop(op);stop(*robot);
    CommandTraceEvent e;unsigned sdk=0,proofs=0,held=0;
    while(oc.command_trace->poll(e))if(e.request==id&&e.point==CommandTracePoint::provider_sent)++sdk;
    while(first_trace->poll(e))if(e.request==id){
        if(e.point==CommandTracePoint::receiver_deferred)++held;
        if(e.point==CommandTracePoint::receiver_expiry_admission){++proofs;check(e.age_error==0&&e.clock_error==0&&e.age_lower_ns>500000000&&e.age_lower_ns<=e.age_upper_ns&&e.expiry_deadline_ns<e.evaluated_ns,"expiry lower-bound proof missing");}
    }
    bool restarted_query=false;while(rc.command_trace->poll(e))if(e.request==id&&e.point==CommandTracePoint::receiver_worker_result&&e.detail==unsigned(Kind::query)&&e.value==0)restarted_query=true;
    check(restarted_query&&sdk==1&&proofs==1&&(!retained||held==1)&&!oc.command_trace->dropped()&&!first_trace->dropped()&&!rc.command_trace->dropped(),"expiry evidence/replay accounting failed");
    sw.journal.process_epoch=random_identity();CommandJournal sender(sw.journal),target(rw.journal);const auto a=sender.get(id),b=target.get(id);
    check(a.entry&&b.entry&&a.entry->state==CommandState::expired&&b.entry->state==CommandState::expired&&a.entry->revision==b.entry->revision&&!a.entry->result.valid&&!b.entry->result.valid&&!b.entry->dispatched_ns&&a.entry->context.source_monotonic_ns==origin&&a.entry->context.deadline_ns==origin+500000000&&b.entry->context.deadline_ns<b.entry->admitted_ns,"closed expiry/journal-only invariant failed");
    std::cout<<"DURABLE_EXPIRY_NATIVE {\"retained\":"<<(retained?"true":"false")<<",\"sdk_handoffs\":1,\"expired_dispatches\":0,\"expired_effects\":0,\"restart_query_duplicate\":true,\"later_fresh_success\":true}\n";
}


}
int main(int argc,char** argv){try{check(argc==2,"family required");auto directory=std::filesystem::current_path()/("wire-errors-"+std::to_string(getpid()));for(unsigned n=0;std::filesystem::exists(directory);++n)directory=std::filesystem::current_path()/("wire-errors-"+std::to_string(getpid())+"-"+std::to_string(n));std::filesystem::create_directories(directory);const auto ip=std::string(argv[1])=="ipv6"?"::1":"127.0.0.1";receiver_errors(ip,directory/"receiver");sender_errors(ip,directory/"sender");for(const auto& mode:{"recover","expiry","context","shutdown"})receiver_clock_diagnostics(ip,directory/(std::string("retention-")+mode),mode);for(bool retained:{false,true})durable_expiry(ip,directory/(retained?"durable-retained":"durable-direct"),retained);std::cout<<"PASS wire errors "<<argv[1]<<": "<<checks<<" checks\n";return 0;}catch(const std::exception& e){std::cerr<<"FAIL: "<<e.what()<<'\n';return 1;}}
