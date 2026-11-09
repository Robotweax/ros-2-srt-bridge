#include <robotweax/srt_bridge/endpoint.hpp>
#include <robotweax/srt_bridge/start_trace_json.hpp>
#include <chrono>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <thread>
#include <vector>
#include <unistd.h>
using namespace robotweax::srt_bridge;
namespace {
unsigned checks=0;
void check(bool ok,const char* text){++checks;if(!ok)throw std::runtime_error(text);}
uint64_t now(){return TransportOwner::monotonic_ns();}
std::string hex(Identity id){std::string s;constexpr char h[]="0123456789abcdef";for(auto b:id){auto n=std::to_integer<unsigned>(b);s+=h[n>>4];s+=h[n&15];}return s;}
EndpointOptions options(Role role,const std::string& ip,const std::string& key,const std::filesystem::path& path,bool enabled,unsigned phase){
 Route route{100,RouteKind::command,Direction::listener_to_caller,QosMapping::request_status,true,4000,5000,0,1,"robotweax.srt_bridge.v1.SetMeasurementRateCommand",rate_command_schema_hash()};auto manifest=*make_manifest(std::span(&route,1)).value;
 SessionConfig s{role,role==Role::caller?"robot":"operator",role==Role::caller?"operator":"robot",random_identity(),role==Role::caller?1U:2U,manifest,{1000,1000000,phase==1?500000000ULL:phase==2?1500000000ULL:5000000000ULL,100000000}};
 EndpointOptions o{{s,{ip,0},{ip,0},key},WorkerOptions{}};o.transport.command_trace=std::make_shared<CommandTrace>();o.transport.start_diagnostics=enabled;
 o.worker.executable=WORKER_EXECUTABLE;o.worker.journal.path=path.string();o.worker.journal.local_peer_id=s.local_peer_id;o.worker.journal.remote_peer_id=s.expected_peer_id;o.worker.journal.process_epoch=s.local_epoch;o.worker.journal.side=role==Role::listener?JournalSide::sender:JournalSide::receiver;o.worker.simulated_rate_handler=role==Role::caller;
 if(role==Role::caller&&phase==1)o.worker.test_pause_at=JournalPoint::dispatch_committed;
 if(role==Role::caller&&phase==2)o.worker.test_handler_pause=2;
 return o;
}
void write_trace(const std::filesystem::path& path,const std::vector<CommandTraceEvent>& rows,const CommandTrace& trace){
 std::ofstream f(path);for(const auto&e:rows){f<<"COMMAND_TRACE {\"sequence\":"<<e.sequence<<",\"monotonic_ns\":"<<e.monotonic_ns<<",\"point\":"<<unsigned(e.point)<<",\"reason\":"<<unsigned(e.reason)<<",\"request\":\""<<hex(e.request)<<"\",\"session\":\""<<hex(e.session)<<"\",\"owner_epoch\":\""<<hex(e.owner_epoch)<<"\",\"entry_owner_epoch\":\""<<hex(e.entry_owner_epoch)<<"\",\"control_generation\":"<<e.control_generation<<",\"sensor_generation\":"<<e.sensor_generation<<",\"route\":"<<e.route<<",\"detail\":"<<e.detail<<",\"value\":"<<e.value<<",\"request_sequence\":"<<e.request_sequence<<",\"origin_ns\":"<<e.origin_ns<<",\"evaluated_ns\":"<<e.evaluated_ns<<",\"clock_deadline_ns\":"<<e.clock_deadline_ns<<",\"clock_error\":"<<e.clock_error<<",\"age_error\":"<<e.age_error<<",\"age_lower_ns\":"<<e.age_lower_ns<<",\"age_upper_ns\":"<<e.age_upper_ns<<",\"expiry_deadline_ns\":"<<e.expiry_deadline_ns<<",\"budget_ms\":"<<e.budget_ms;append_start_trace_json(f,e);f<<"}\n";}
 f<<"COMMAND_TRACE_STATUS {\"attempted\":"<<trace.attempted()<<",\"dropped\":"<<trace.dropped()<<"}\n";check(f.good(),"trace write failed");
}
void scenario(const std::string& ip,const std::filesystem::path& path,unsigned phase){
 std::filesystem::create_directories(path);auto oc=options(Role::listener,ip,hex(random_identity()),path/"sender.sqlite",phase!=3,phase);
 CommandEndpoint op(oc);std::vector<CommandTraceEvent> sender,receiver;
 auto drain=[](const std::shared_ptr<CommandTrace>& t,std::vector<CommandTraceEvent>& rows){CommandTraceEvent e;while(t->poll(e)){if(rows.size()>=2048)throw std::runtime_error("capture limit");rows.push_back(e);}};
 const auto listener_end=now()+10000000000ULL;while(!op.snapshot().transport.control_port){check(now()<listener_end,"listen deadline");std::this_thread::sleep_for(std::chrono::milliseconds(1));}
 auto rc=options(Role::caller,ip,oc.transport.passphrase,path/"receiver.sqlite",phase!=3,phase);rc.transport.control.port=op.snapshot().transport.control_port;rc.transport.sensor.port=op.snapshot().transport.sensor_port;CommandEndpoint robot(rc);
 auto until=[&](auto predicate,const char* label){const auto end=now()+10000000000ULL;while(true){drain(oc.transport.command_trace,sender);drain(rc.transport.command_trace,receiver);if(predicate())break;if(now()>=end)throw std::runtime_error(label);std::this_thread::sleep_for(std::chrono::milliseconds(1));}++checks;};
 until([&]{return op.snapshot().ready&&robot.snapshot().ready;},"readiness failed");const auto id=random_identity();until([&]{return op.execute(100,id,{100,5000,0,1},now())==SubmitResult::queued;},"submission failed");
 if(phase==1||phase==2){
  until([&]{return robot.snapshot().test_paused;},"barrier missing");uint64_t deadline=robot.snapshot().transport.clock_deadline_ns;
  if(phase==2){until([&]{for(const auto&e:receiver)if(e.point==CommandTracePoint::start_check&&e.request==id&&e.start_granted){deadline=e.grant_deadline_ns;return true;}return false;},"grant observation missing");}
  check(deadline>0,"missing fixture deadline");until([&]{return now()>=deadline+5000000;},"lease did not elapse");check(robot.resume_test_barrier(),"resume rejected");
 }
 const auto expected=phase==1||phase==2?CommandState::rejected:CommandState::succeeded;CommandEvent event;
 until([&]{while(op.poll(event))if(event.request_id==id&&event.entry&&event.entry->state==expected)return true;return false;},"terminal result missing");
 check(event.entry->reason==(expected==CommandState::rejected?CommandReason::context_lost:CommandReason::none),"wrong terminal reason");check(robot.snapshot().effects==(expected==CommandState::succeeded?1U:0U),"wrong effect count");
 op.request_stop();op.join();robot.request_stop();robot.join();drain(oc.transport.command_trace,sender);drain(rc.transport.command_trace,receiver);
 check(!oc.transport.command_trace->dropped()&&!rc.transport.command_trace->dropped(),"trace overflow");
 std::vector<CommandTraceEvent> starts;for(const auto&e:receiver)if(unsigned(e.point)>=40&&unsigned(e.point)<=44)starts.push_back(e);
 if(phase==3)check(starts.empty(),"disabled start tracing emitted events");
 else if(phase==1){bool denied=false,declined=false;for(const auto&e:starts){if(e.point==CommandTracePoint::start_check){check(!e.start_granted&&e.value!=0,"expired coordinator granted");denied=true;}if(e.point==CommandTracePoint::start_declined)declined=true;check(e.point!=CommandTracePoint::execute_submission&&e.point!=CommandTracePoint::worker_start,"coordinator denial submitted execute");}check(denied&&declined,"coordinator decline not observed");}
 else{bool worker=false;for(const auto&e:starts)if(e.point==CommandTracePoint::worker_start){worker=true;check(e.worker_observation_available&&e.consume_result==1&&e.second_gate_checked,"worker observations unavailable");check(e.handler_invoked==(phase==0),"wrong pre-handler branch");check((e.second_gate_ns>=e.second_gate_deadline_ns)==(phase==2),"wrong second gate deadline");}check(worker,"worker result missing");}
 write_trace(path/"operator.log",sender,*oc.transport.command_trace);write_trace(path/"robot.log",receiver,*rc.transport.command_trace);
 std::cout<<"CASE "<<phase<<" state="<<unsigned(event.entry->state)<<" reason="<<unsigned(event.entry->reason)<<" effects="<<robot.snapshot().effects<<" start_events="<<starts.size()<<"\n";
}
}
int main(int argc,char**argv){try{check(argc==2,"family required");auto root=std::filesystem::current_path()/("start-trace-"+std::to_string(getpid()));check(!std::filesystem::exists(root),"output exists");for(unsigned phase=0;phase<4;++phase)scenario(std::string(argv[1])=="ipv6"?"::1":"127.0.0.1",root/std::to_string(phase),phase);std::cout<<"PASS start tracing "<<argv[1]<<": "<<checks<<" checks\n";return 0;}catch(const std::exception&e){std::cerr<<"FAIL start tracing: "<<e.what()<<"\n";return 1;}}
