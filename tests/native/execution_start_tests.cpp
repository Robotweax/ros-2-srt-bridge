#include <robotweax/srt_bridge/transport.hpp>
#include <robotweax/srt_bridge/worker.hpp>
#include <chrono>
#include <filesystem>
#include <iostream>
#include <thread>
#include <unistd.h>
using namespace robotweax::srt_bridge;
namespace {
unsigned checks=0;
void check(bool value,const char* text){++checks;if(!value)throw std::runtime_error(text);}
std::uint64_t now(){return TransportOwner::monotonic_ns();}
template<class F> void until(F test,const char* text){const auto end=now()+8000000000ULL;while(!test()){if(now()>=end)throw std::runtime_error(text);std::this_thread::sleep_for(std::chrono::milliseconds(1));}++checks;}
std::string secret(){std::string s;constexpr char hex[]="0123456789abcdef";for(auto b:random_identity()){const auto v=std::to_integer<unsigned>(b);s+=hex[v>>4];s+=hex[v&15];}return s;}
TransportConfig config(Role role,const std::string& ip,const std::string& key){Route command{100,RouteKind::command,Direction::listener_to_caller,QosMapping::request_status,true,4000,5000,0,1,"robotweax.srt_bridge.v1.SetMeasurementRateCommand",rate_command_schema_hash()};auto routes=*make_manifest(std::span(&command,1)).value;
    SessionConfig session{role,role==Role::caller?"robot":"operator",role==Role::caller?"operator":"robot",random_identity(),role==Role::caller?1U:2U,routes,{1000,1000000,5000000000ULL,100000000}};return {std::move(session),{ip,0},{ip,0},key};}
WorkerOptions options(const TransportConfig& config,const std::filesystem::path& path,JournalSide side){WorkerOptions o;o.executable=WORKER_EXECUTABLE;o.journal.path=path.string();o.journal.local_peer_id=config.session.local_peer_id;o.journal.remote_peer_id=config.session.expected_peer_id;o.journal.process_epoch=config.session.local_epoch;o.journal.side=side;o.simulated_rate_handler=side==JournalSide::receiver;return o;}
void ready(JournalWorker& w){WorkerReply reply;until([&]{w.poll(reply);return w.state()==WorkerState::ready||w.state()==WorkerState::failed;},"worker readiness timeout");check(w.state()==WorkerState::ready,"worker startup failed");}
WorkerReply rpc(JournalWorker& w,const WorkerRequest& q){WorkerSubmission submitted;until([&]{submitted=w.submit(q);return submitted.result!=WorkerSubmit::busy;},"worker busy");check(submitted.result==WorkerSubmit::queued,"worker request rejected");WorkerReply reply;until([&]{return w.poll(reply);},"worker reply missing");check(reply.token==submitted.token&&!reply.test_paused,"wrong worker reply");return reply;}
void scenario(const std::string& ip,const std::filesystem::path& directory,unsigned phase){
    const auto key=secret();auto operator_config=config(Role::listener,ip,key);TransportOwner op(operator_config);until([&]{return op.snapshot().control_port!=0;},"listen timeout");
    auto robot_config=config(Role::caller,ip,key);if(phase==6)robot_config.session.clock.max_probe_age_ns=1500000000ULL;robot_config.control.port=op.snapshot().control_port;robot_config.sensor.port=op.snapshot().sensor_port;TransportOwner robot(robot_config);until([&]{return op.snapshot().state==SessionState::active&&robot.snapshot().state==SessionState::active;},"session timeout");
    const auto sender_options=options(operator_config,directory/"sender.sqlite",JournalSide::sender);auto receiver_options=options(robot_config,directory/"receiver.sqlite",JournalSide::receiver);receiver_options.test_handler_pause=phase>=4?1:phase;
    JournalWorker sender(sender_options),receiver(receiver_options);ready(sender);ready(receiver);
    WorkerRequest q;q.operation=WorkerOperation::admit;q.request_id=random_identity();q.route=100;q.command={100,5000,0,1};const auto origin=now();q.context={op.snapshot().context.session,operator_config.session.local_epoch,origin,origin+5000000000ULL};
    auto admitted=rpc(sender,q);check(admitted.ticket.has_value(),"missing sender ticket");auto send_context=op.snapshot().context;if(phase==5)send_context.sensor_generation=0;until([&]{return op.submit_command(send_context,std::move(*admitted.ticket))==SubmitResult::queued;},"command send failed");
    TransportMessage command;until([&]{return robot.poll_control(command);},"command receive timeout");
    q.context={command.context.session,command.envelope.source_epoch,origin,command.deadline_ns};check(bool(rpc(receiver,q).journal),"receiver admission failed");
    if(phase==5)command.context.sensor_generation=0;
    q.operation=WorkerOperation::begin_dispatch;q.session=command.context.session;q.clock_qualified=true;auto dispatch=rpc(receiver,q);check(dispatch.dispatch.has_value(),"no durable dispatch ticket");
    WorkerRequest raw=q;raw.operation=WorkerOperation::execute;check(receiver.submit(raw).result==WorkerSubmit::invalid,"raw execute bypassed grant");
    check(receiver.submit_execute(std::move(*dispatch.dispatch)).result==WorkerSubmit::not_ready,"ungranted ticket started handler");
    until([&]{return robot.request_command_start(command.context,command.envelope,*dispatch.dispatch,1)==SubmitResult::queued;},"owner start request failed");CommandCheck granted;until([&]{return robot.poll_command_check(granted);},"owner start reply missing");check(granted.fresh()&&granted.start_granted,"owner did not grant start");if(phase==6)check(granted.deadline_ns-granted.evaluated_ns<=1500000000ULL,"grant outlived clock qualification");
    check(robot.request_command_start(command.context,command.envelope,*dispatch.dispatch,2)==SubmitResult::obsolete,"start proof granted twice");
    const auto submitted=receiver.submit_execute(std::move(*dispatch.dispatch));check(submitted.result==WorkerSubmit::queued,"execute RPC rejected");check(receiver.submit_execute(std::move(*dispatch.dispatch)).result==WorkerSubmit::invalid,"execute ticket reused");
    WorkerReply reply;until([&]{return receiver.poll(reply);},"execute/barrier reply missing");check(reply.token==submitted.token,"execute token changed");
    if(phase){check(reply.test_paused&&reply.test_handler_point==(phase>=4?1:phase),"handler barrier missing");
        if(phase<=3){op.request_stop();op.join();until([&]{return robot.snapshot().context.session!=command.context.session;},"owner did not revoke session");}
        if(phase==3){check(reply.effects==1&&reply.device==RateResult{100,1,true},"effect barrier preceded effect");const auto start=now();check(receiver.join()&&now()-start<5000000000ULL,"running handler shutdown exceeded deadline");receiver_options.test_handler_pause=0;JournalWorker recovered(receiver_options);ready(recovered);q.operation=WorkerOperation::get;auto result=rpc(recovered,q);check(result.journal.entry->state==CommandState::unknown&&!result.dispatch,"effect crash replayed or lost UNKNOWN");check(recovered.join(),"recovery stop failed");}
        else{
            if(phase==6)until([&]{return now()>=granted.deadline_ns+1000000;},"clock lease wait failed");
            if(phase==4)until([&]{return now()>=command.deadline_ns+1000000;},"deadline wait failed");
            check(receiver.resume_test_barrier(),"handler resume failed");until([&]{return receiver.poll(reply);},"resumed execution reply missing");check(!reply.test_paused&&reply.token==submitted.token,"wrong resumed reply");
        }
    }
    if(phase!=3){const auto expected=(phase==1||phase==6)?CommandState::rejected:phase==4?CommandState::expired:CommandState::succeeded;
        if(!reply.journal||reply.journal.entry->state!=expected){std::cerr<<"phase="<<phase<<" expected="<<int(expected)<<" actual="<<(reply.journal.entry?int(reply.journal.entry->state):-1)<<" reason="<<(reply.journal.entry?int(reply.journal.entry->reason):-1)<<"\n";}check(reply.journal&&reply.journal.entry->state==expected,"wrong fenced handler result");check(reply.effects==((phase==1||phase==4||phase==6)?0U:1U),"revocation/expiry allowed effect or running effect lost");
        q.operation=WorkerOperation::get;auto stored=rpc(receiver,q);check(stored.journal.entry->state==expected&&!stored.dispatch,"GET minted a start ticket");check(receiver.join(),"receiver stop failed");}
    check(sender.join(),"sender stop failed");op.request_stop();op.join();robot.request_stop();robot.join();
}
}
int main(int argc,char** argv){try{check(argc==2,"family required");auto directory=std::filesystem::current_path()/("execution-start-"+std::to_string(getpid()));for(unsigned n=0;std::filesystem::exists(directory);++n)directory=std::filesystem::current_path()/("execution-start-"+std::to_string(getpid())+"-"+std::to_string(n));std::filesystem::create_directories(directory);for(unsigned phase=0;phase<7;++phase)scenario(std::string(argv[1])=="ipv6"?"::1":"127.0.0.1",directory/std::to_string(phase),phase);
    std::cout<<"PASS execution start "<<argv[1]<<": "<<checks<<" checks\n";return 0;}catch(const std::exception& e){std::cerr<<"FAIL: "<<e.what()<<"\n";return 1;}}
