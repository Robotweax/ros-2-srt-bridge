#include <robotweax/srt_bridge/endpoint.hpp>
#include <chrono>
#include <atomic>
#include <filesystem>
#include <iostream>
#include <thread>
#include <unistd.h>
using namespace robotweax::srt_bridge;
namespace {
unsigned checks=0;
void check(bool ok,const char* text){++checks;if(!ok)throw std::runtime_error(text);}
std::uint64_t now(){return TransportOwner::monotonic_ns();}
template<class F> void until(F test,const char* text,unsigned seconds=10){const auto end=now()+std::uint64_t(seconds)*1000000000;while(!test()){if(now()>=end)throw std::runtime_error(text);std::this_thread::sleep_for(std::chrono::milliseconds(1));}++checks;}
std::string secret(){std::string s;constexpr char hex[]="0123456789abcdef";for(auto b:random_identity()){auto v=std::to_integer<unsigned>(b);s+=hex[v>>4];s+=hex[v&15];}return s;}
RouteManifest manifest(){Route r{100,RouteKind::command,Direction::listener_to_caller,QosMapping::request_status,true,4000,5000,0,1,"robotweax.srt_bridge.v1.SetMeasurementRateCommand",rate_command_schema_hash()};auto other=r;other.id=101;const std::array routes{r,other};return *make_manifest(routes).value;}
EndpointOptions config(Role role,const std::string& ip,const std::string& key,const std::filesystem::path& path){
    SessionConfig s{role,role==Role::caller?"robot":"operator",role==Role::caller?"operator":"robot",random_identity(),role==Role::caller?1U:2U,manifest(),{1000,1000000,5000000000ULL,100000000}};
    WorkerOptions w;w.executable=WORKER_EXECUTABLE;w.journal.path=path.string();w.journal.local_peer_id=s.local_peer_id;w.journal.remote_peer_id=s.expected_peer_id;w.journal.process_epoch=s.local_epoch;w.journal.side=role==Role::listener?JournalSide::sender:JournalSide::receiver;w.simulated_rate_handler=role==Role::caller;
    return {{std::move(s),{ip,0},{ip,0},key},w};
}
struct Pair {
    EndpointOptions oc,rc;
    std::unique_ptr<CommandEndpoint> op,robot;
    Pair(const std::string& ip,const std::filesystem::path& path,bool withhold=false,std::optional<JournalPoint> pause={},unsigned handler_pause=0,std::uint64_t timeout=3000000000ULL,bool sender_pause=false,bool trace=false):oc(config(Role::listener,ip,secret(),path/"operator.sqlite")),rc(config(Role::caller,ip,oc.transport.passphrase,path/"robot.sqlite")){
        if(trace){oc.transport.command_trace=std::make_shared<CommandTrace>();rc.transport.command_trace=std::make_shared<CommandTrace>();}
        if(sender_pause)oc.worker.test_pause_at=JournalPoint::admission_before_commit;
        op=std::make_unique<CommandEndpoint>(oc);until([&]{return op->snapshot().transport.control_port!=0;},"operator listen failed");
        rc.transport.control.port=op->snapshot().transport.control_port;rc.transport.sensor.port=op->snapshot().transport.sensor_port;rc.test_withhold_final_status=withhold;rc.worker.test_pause_at=pause;rc.worker.test_handler_pause=handler_pause;rc.operation_timeout_ns=timeout;
        robot=std::make_unique<CommandEndpoint>(rc);ready();
    }
    void ready(){try{until([&]{return op->snapshot().ready&&robot->snapshot().ready&&op->snapshot().transport.state==SessionState::active&&robot->snapshot().transport.state==SessionState::active;},"endpoint readiness failed");}catch(...){for(auto* e:{op.get(),robot.get()}){auto s=e->snapshot();std::cerr<<"endpoint fault="<<int(s.fault)<<" worker="<<int(s.worker)<<" state="<<int(s.transport.state)<<" netfault="<<int(s.transport.fault)<<"\n";}throw;}}
};
CommandEvent result(CommandEndpoint& op,Identity id,CommandState wanted){CommandEvent event;until([&]{while(op.poll(event)){if(event.request_id==id&&event.error==JournalError::none&&event.entry&&event.entry->state==wanted)return true;}return false;},"command result missing");return event;}
void submit(CommandEndpoint& op,Identity id,RateCommand cmd){until([&]{const auto r=op.execute(100,id,cmd,now());if(r!=SubmitResult::queued&&r!=SubmitResult::busy)throw std::runtime_error("execute rejected");return r==SubmitResult::queued;},"execute mailbox busy");}
void stop(CommandEndpoint& endpoint){const auto begin=now();endpoint.request_stop();endpoint.join();check(now()-begin<5000000000ULL,"endpoint shutdown exceeded five seconds");const auto s=endpoint.snapshot();check(!s.running&&!s.ready&&s.worker==WorkerState::stopped&&!s.transport.running,"endpoint not fully stopped");endpoint.join();}
void normal(const std::string& ip,const std::filesystem::path& directory){Pair p(ip,directory,true);const auto id=random_identity();submit(*p.op,id,{100,5000,0,1});auto success=result(*p.op,id,CommandState::succeeded);check(success.entry->result==RateResult{100,1,true},"wrong command result");check(p.robot->snapshot().effects==1&&p.op->snapshot().queries_sent>0,"query recovery failed or duplicate effect");
    const auto sent=p.op->snapshot().commands_sent;submit(*p.op,id,{100,5000,0,1});result(*p.op,id,CommandState::succeeded);check(p.op->snapshot().commands_sent==sent&&p.robot->snapshot().effects==1,"duplicate resent/executed");
    submit(*p.op,id,{300,5000,0,1});CommandEvent conflict;until([&]{return p.op->poll(conflict)&&conflict.request_id==id&&conflict.error==JournalError::conflict;},"conflict not surfaced");check(p.robot->snapshot().effects==1,"conflict affected device");
    const auto bad=random_identity();submit(*p.op,bad,{300,5000,0,1});auto failed=result(*p.op,bad,CommandState::failed);check(failed.entry->reason==CommandReason::generation_conflict&&p.robot->snapshot().effects==1,"generation conflict executed");
    const auto good=random_identity();submit(*p.op,good,{300,5000,1,2});result(*p.op,good,CommandState::succeeded);check(p.robot->snapshot().effects==2&&p.robot->snapshot().device==RateResult{300,2,true},"second generation not applied");
    until([&]{return p.op->query(101,id)==SubmitResult::queued;},"wrong-route query not queued");CommandEvent wrong;until([&]{return p.op->poll(wrong)&&wrong.request_id==id&&wrong.error==JournalError::conflict;},"wrong-route query did not conflict");
    until([&]{return p.op->query(100,id)==SubmitResult::queued;},"client query not queued");result(*p.op,id,CommandState::succeeded);stop(*p.op);stop(*p.robot);check(p.op->execute(100,random_identity(),{100,5000,0,1},now())==SubmitResult::stopped,"post-stop execution accepted");
}
void diagnostic_lifecycle(const std::string& ip,const std::filesystem::path& directory){
    Pair p(ip,directory,false,{},0,3000000000ULL,false,true);const auto id=random_identity();
    submit(*p.op,id,{100,5000,0,1});result(*p.op,id,CommandState::succeeded);stop(*p.op);stop(*p.robot);
    CommandTraceEvent e;unsigned count=0;bool admitted=false,queued=false,sent=false,stopping=false,stopped=false;
    while(p.oc.transport.command_trace->poll(e)){
        ++count;check(e.monotonic_ns>0&&e.owner_epoch==p.oc.transport.session.local_epoch,"trace provenance missing");
        if(e.point==CommandTracePoint::sender_admission){admitted=true;check(e.request==id,"wrong admitted trace ID");}
        if(e.point==CommandTracePoint::submit_result){queued=true;check(e.request==id&&e.value==unsigned(SubmitResult::queued),"wrong handoff trace");}
        if(e.point==CommandTracePoint::provider_sent){sent=true;check(e.request==id,"wrong sent trace ID");}
        if(e.point==CommandTracePoint::endpoint_stopping)stopping=true;
        if(e.point==CommandTracePoint::endpoint_stopped){check(stopping,"missing shutdown boundary");stopped=true;}
    }
    check(admitted&&queued&&sent&&stopped,"trace missing command or lifecycle stages");
    check(count==p.oc.transport.command_trace->attempted()&&p.oc.transport.command_trace->dropped()==0,"trace coverage missing");
}
void lost_result(const std::string& ip,const std::filesystem::path& directory){
    Pair p(ip,directory,false,JournalPoint::result_committed);const auto id=random_identity();submit(*p.op,id,{100,5000,0,1});
    until([&]{return p.robot->snapshot().test_paused;},"result-commit barrier missing");
    stop(*p.robot);p.robot.reset();
    p.rc.worker.test_pause_at.reset();p.rc.transport.session.local_epoch=random_identity();p.rc.worker.journal.process_epoch=p.rc.transport.session.local_epoch;
    p.robot=std::make_unique<CommandEndpoint>(p.rc);p.ready();auto recovered=result(*p.op,id,CommandState::succeeded);
    check(recovered.entry->result==RateResult{100,1,true},"committed result lost across endpoint restart");
    check(p.op->snapshot().commands_sent==1&&p.op->snapshot().queries_sent>0&&p.robot->snapshot().effects==0,"reconnect resent a command");
    stop(*p.op);stop(*p.robot);
}
void unknown_restart(const std::string& ip,const std::filesystem::path& directory){
    Pair p(ip,directory,false,{},2,3000000000ULL,false,true);const auto old_epoch=p.oc.transport.session.local_epoch;const auto id=random_identity();submit(*p.op,id,{100,5000,0,1});
    until([&]{return p.robot->snapshot().test_paused;},"running handler barrier missing");check(p.robot->snapshot().effects==0,"before-effect barrier applied effect");
    const auto ports=p.op->snapshot().transport;stop(*p.robot);stop(*p.op);p.robot.reset();p.op.reset();
    p.oc.transport.control.port=ports.control_port;p.oc.transport.sensor.port=ports.sensor_port;p.oc.transport.session.local_epoch=random_identity();p.oc.worker.journal.process_epoch=p.oc.transport.session.local_epoch;
    p.op=std::make_unique<CommandEndpoint>(p.oc);until([&]{return p.op->snapshot().transport.control_port!=0;},"operator restart listen failed");
    p.rc.worker.test_handler_pause=0;p.rc.transport.session.local_epoch=random_identity();p.rc.worker.journal.process_epoch=p.rc.transport.session.local_epoch;
    p.robot=std::make_unique<CommandEndpoint>(p.rc);p.ready();submit(*p.op,id,{100,5000,0,1});CommandEvent unknown;until([&]{while(p.op->poll(unknown))if(unknown.request_id==id&&unknown.error==JournalError::none&&unknown.entry&&unknown.entry->state==CommandState::unknown&&unknown.entry->reason==CommandReason::context_lost)return true;return false;},"recovered uncertainty not reconciled with peer");
    check(p.op->snapshot().commands_sent==0&&p.robot->snapshot().effects==0,"UNKNOWN restart automatically replayed");stop(*p.op);stop(*p.robot);
    CommandTraceEvent e;bool recovered=false;
    while(p.oc.transport.command_trace->poll(e))if(e.point==CommandTracePoint::worker_unknown&&e.request==id&&e.owner_epoch==p.oc.transport.session.local_epoch){
        check(e.entry_owner_epoch==old_epoch&&e.entry_owner_epoch!=e.owner_epoch,"recovery trace lost original owner epoch");recovered=true;
    }
    check(recovered,"missing recovered UNKNOWN trace");
}
void timeout(const std::string& ip,const std::filesystem::path& directory){
    Pair p(ip,directory,false,{},2,1000000000ULL);const auto id=random_identity();submit(*p.op,id,{100,5000,0,1});
    until([&]{return p.robot->snapshot().test_paused;},"timeout handler barrier missing");
    until([&]{return !p.robot->snapshot().running;},"stalled handler not supervised");
    check(p.robot->snapshot().fault==EndpointFault::timeout&&p.robot->snapshot().worker==WorkerState::stopped&&p.robot->snapshot().effects==0,"timeout did not fail closed");stop(*p.robot);stop(*p.op);
}
void bounded_shutdown(const std::string& ip,const std::filesystem::path& directory){
    Pair p(ip,directory,false,{},0,3000000000ULL,true);const auto id=random_identity();submit(*p.op,id,{100,5000,0,1});
    until([&]{return p.op->snapshot().test_paused;},"sender admission barrier missing");
    std::atomic<unsigned> queued{0},busy{0};std::array<std::thread,4> producers;
    for(auto& producer:producers)producer=std::thread([&]{for(unsigned n=0;n<128;++n){const auto r=p.op->execute(100,id,{100,5000,0,1},now());if(r==SubmitResult::queued)++queued;else if(r==SubmitResult::busy)++busy;}});
    for(auto& producer:producers)producer.join();
    check(queued>0&&queued<=64&&busy>0&&p.op->snapshot().queued<=64,"endpoint ingress not bounded");
    check(p.robot->snapshot().transport.state==SessionState::active,"blocked journal stalled network owner");
    stop(*p.op);unsigned cancelled=0;CommandEvent event;while(p.op->poll(event)){check(event.error==JournalError::context_lost&&!event.entry,"shutdown fabricated an outcome");++cancelled;}
    check(cancelled==queued+1,"unresolved local callbacks lost at shutdown");check(p.robot->snapshot().effects==0,"uncommitted sender admission executed");stop(*p.robot);
}
}
int main(int argc,char** argv){try{check(argc==2,"family required");const auto ip=std::string(argv[1])=="ipv6"?"::1":"127.0.0.1";auto dir=std::filesystem::current_path()/("endpoint-"+std::to_string(getpid()));for(unsigned n=0;std::filesystem::exists(dir);++n)dir=std::filesystem::current_path()/("endpoint-"+std::to_string(getpid())+"-"+std::to_string(n));std::filesystem::create_directories(dir);normal(ip,dir/"normal");diagnostic_lifecycle(ip,dir/"trace");lost_result(ip,dir/"lost-result");unknown_restart(ip,dir/"unknown");timeout(ip,dir/"timeout");bounded_shutdown(ip,dir/"bounded");std::cout<<"PASS command endpoint "<<argv[1]<<": "<<checks<<" checks\n";return 0;}catch(const std::exception& e){std::cerr<<"FAIL: "<<e.what()<<"\n";return 1;}}
