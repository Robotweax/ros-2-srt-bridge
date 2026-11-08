// Development fixture only. Existing production endpoint + installed worker.
#include <robotweax/srt_bridge/endpoint.hpp>
#include <chrono>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <iomanip>
#include <set>
#include <sstream>
#include <thread>
#include <vector>
#include <csignal>
#include <unistd.h>
using namespace robotweax::srt_bridge;
namespace fs=std::filesystem;
namespace {
void require(bool ok,const char* s){if(!ok)throw std::runtime_error(s);}
std::uint64_t now(){return TransportOwner::monotonic_ns();}
template<class T> std::string hex(const T& b){std::string s;constexpr char h[]="0123456789abcdef";for(auto v:b){auto n=std::to_integer<unsigned>(v);s+=h[n>>4];s+=h[n&15];}return s;}
void write(const fs::path& path,const std::string& value){auto tmp=path;tmp+=".tmp";{std::ofstream o(tmp);o<<value<<'\n';o.flush();require(bool(o),"file write failed");}fs::rename(tmp,path);}
std::string snapshot(CommandEndpoint& e){auto s=e.snapshot();std::ostringstream o;o<<"{\"ns\":"<<now()<<",\"session\":\""<<hex(s.transport.context.session)<<"\",\"ready\":"<<s.ready<<",\"clock\":"<<s.transport.clock_qualified<<",\"paused\":"<<s.test_paused<<",\"effects\":"<<s.effects<<",\"generation\":"<<s.device.generation<<",\"rate_hz\":"<<s.device.rate_hz<<",\"commands_sent\":"<<s.commands_sent<<",\"queries_sent\":"<<s.queries_sent<<",\"fault\":"<<unsigned(s.fault)<<",\"worker_fault\":"<<unsigned(s.worker_fault)<<",\"running\":"<<s.running<<",\"worker\":"<<unsigned(s.worker)<<",\"transport_running\":"<<s.transport.running<<"}";return o.str();}
std::string entry(const CommandEvent& ev){std::ostringstream o;o<<"{\"ns\":"<<now()<<",\"error\":"<<unsigned(ev.error)<<",\"request\":\""<<hex(ev.request_id)<<'"';if(ev.entry){const auto& e=*ev.entry;o<<",\"state\":"<<unsigned(e.state)<<",\"reason\":"<<unsigned(e.reason)<<",\"revision\":"<<e.revision<<",\"result_valid\":"<<e.result.valid<<",\"result_generation\":"<<e.result.generation<<",\"origin_ns\":"<<e.context.source_monotonic_ns<<",\"deadline_ns\":"<<e.context.deadline_ns<<",\"payload_hash\":\""<<hex(e.payload_hash)<<'"';}o<<'}';return o.str();}
struct WorkerIdentity {pid_t pid;std::string start;bool operator==(const WorkerIdentity&)const=default;};
WorkerIdentity paused_worker(const std::string& executable){
 const auto deadline=now()+1000000000ULL;bool logged=false;
 while(now()<deadline){
  std::set<pid_t> children;for(const auto& task:fs::directory_iterator("/proc/self/task")){std::ifstream in(task.path()/"children");pid_t p;while(in>>p)children.insert(p);}
  std::vector<WorkerIdentity> matches;
  for(auto p:children){
   const auto root=fs::path("/proc")/std::to_string(p);std::ifstream args(root/"cmdline",std::ios::binary);std::vector<std::string> words;std::string word;while(std::getline(args,word,'\0'))words.push_back(word);
   bool worker=false;for(std::size_t i=0;i+1<words.size();++i)if(words[i]==executable&&words[i+1]=="--worker-ipc-v3")worker=true;
   std::ifstream in(root/"stat");std::string line;std::getline(in,line);const auto at=line.rfind(") ");if(at==std::string::npos)continue;
   std::istringstream fields(line.substr(at+2));char state;fields>>state;std::string start;for(unsigned i=1;i<=19;++i)fields>>start;
   std::error_code ec;const auto exe=fs::read_symlink(root/"exe",ec);
   if(!logged)std::cout<<"N4_CHILD {\"pid\":"<<p<<",\"worker_argv\":"<<worker<<",\"stopped\":"<<(state=='T')<<",\"exe_matches\":"<<(!ec&&exe==fs::path(executable))<<",\"kernel_exe\":"<<std::quoted(exe.string())<<",\"start_ticks\":\""<<start<<"\"}"<<std::endl;
   if(worker&&state=='T')matches.push_back({p,start});
  }
  logged=true;require(matches.size()<=1,"ambiguous owned stopped worker");if(matches.size()==1)return matches[0];
  std::this_thread::sleep_for(std::chrono::milliseconds(2));
 }
 throw std::runtime_error("no uniquely owned stopped worker after bounded readiness wait");
}
}
int main(int argc,char** argv){try{
 require(argc==6,"role run peer phase credential required");const std::string role=argv[1],phase=argv[4];const fs::path run=argv[2];const bool sender=role=="operator";require(sender||role=="robot","role");require(phase=="admission"||phase=="started"||phase=="committed","phase");
 std::ifstream keyfile(argv[5]);std::string key;std::getline(keyfile,key);require(key.size()>=10,"credential");
 Route route{100,RouteKind::command,Direction::listener_to_caller,QosMapping::request_status,true,4000,5000,0,1,"robotweax.srt_bridge.v1.SetMeasurementRateCommand",rate_command_schema_hash()};
 auto manifest=make_manifest(std::span(&route,1));require(bool(manifest),"manifest");auto epoch=random_identity();
 SessionConfig session{sender?Role::listener:Role::caller,sender?"operator":"robot",sender?"robot":"operator",epoch,sender?2U:1U,*manifest.value,{1000,1000000,5000000000ULL,200000000}};
 WorkerOptions worker;worker.executable="/workspace/install/bridge-m3/bin/robotweax-journal-worker";worker.journal.path=(run/(role+".sqlite")).string();worker.journal.local_peer_id=session.local_peer_id;worker.journal.remote_peer_id=session.expected_peer_id;worker.journal.process_epoch=epoch;worker.journal.side=sender?JournalSide::sender:JournalSide::receiver;worker.simulated_rate_handler=!sender;
 if(!sender){if(phase=="admission")worker.test_pause_at=JournalPoint::admission_before_commit;else if(phase=="started")worker.test_handler_pause=2;else worker.test_pause_at=JournalPoint::result_committed;}
 EndpointOptions options{{session,{sender?"0.0.0.0":argv[3],10080},{sender?"0.0.0.0":argv[3],10081},key},worker};options.operation_timeout_ns=20000000000ULL;options.transport.command_trace=std::make_shared<CommandTrace>();
 CommandEndpoint endpoint(options);std::uint64_t events=0,trace_count=0,provider_sends=0;bool final=false;CommandState state=CommandState::unknown;Identity id{};id[0]=std::byte{1};
 auto pump=[&]{CommandTraceEvent t;while(options.transport.command_trace->poll(t)){++trace_count;if(t.point==CommandTracePoint::provider_sent&&t.request==id)++provider_sends;std::cout<<"N4_TRACE {\"seq\":"<<t.sequence<<",\"ns\":"<<t.monotonic_ns<<",\"point\":"<<unsigned(t.point)<<",\"reason\":"<<unsigned(t.reason)<<",\"value\":"<<t.value<<",\"detail\":"<<t.detail<<",\"request\":\""<<hex(t.request)<<"\",\"session\":\""<<hex(t.session)<<"\",\"owner\":\""<<hex(t.owner_epoch)<<"\"}"<<std::endl;}CommandEvent e;while(endpoint.poll(e)){require(++events<=256,"event budget");std::cout<<"N4_EVENT "<<entry(e)<<std::endl;if(e.request_id==id&&e.error==JournalError::none&&e.entry){require(e.entry->context.deadline_ns==e.entry->context.source_monotonic_ns+5000000000ULL,"deadline changed");state=e.entry->state;if(state==CommandState::succeeded)require(e.entry->result==RateResult{100,1,true},"wrong successful device result");if(state==CommandState::succeeded||state==CommandState::failed||state==CommandState::rejected||state==CommandState::expired)final=true;}}};
 auto wait=[&](auto predicate,const char* message,unsigned seconds=35){auto end=now()+std::uint64_t(seconds)*1000000000;while(!predicate()){pump();require(now()<end,message);require(endpoint.snapshot().running||endpoint.snapshot().fault==EndpointFault::none,"endpoint stopped unexpectedly");std::this_thread::sleep_for(std::chrono::milliseconds(2));}pump();};
 wait([&]{auto s=endpoint.snapshot();return s.ready&&s.transport.clock_qualified;},"qualified readiness timeout");write(run/(role+"-ready.json"),"{\"owner\":\""+hex(epoch)+"\",\"snapshot\":"+snapshot(endpoint)+"}");
 if(sender){wait([&]{return fs::exists(run/"go");},"go timeout");const auto origin=now();wait([&]{auto s=endpoint.execute(100,id,{100,5000,0,1},origin);require(s==SubmitResult::queued||s==SubmitResult::busy,"execute rejected");return s==SubmitResult::queued;},"local submit busy",3);write(run/"submitted.json","{\"origin_ns\":"+std::to_string(origin)+",\"deadline_ns\":"+std::to_string(origin+5000000000ULL)+"}");
  wait([&]{return fs::exists(run/"restored");},"network restoration timeout");std::uint64_t next=0;wait([&]{if(!final&&now()>=next&&endpoint.snapshot().ready){if(endpoint.query(100,id)==SubmitResult::queued)next=now()+500000000ULL;}return final;},"query reconciliation timeout",25);
  write(run/"operator-outcome.json","{\"state\":"+std::to_string(unsigned(state))+",\"snapshot\":"+snapshot(endpoint)+"}");
 }else{wait([&]{return endpoint.snapshot().test_paused;},"phase barrier timeout");auto pid=paused_worker(worker.executable);write(run/"robot-barrier.json","{\"worker_pid\":"+std::to_string(pid.pid)+",\"snapshot\":"+snapshot(endpoint)+"}");wait([&]{return fs::exists(run/"resume");},"worker resume timeout",15);require(endpoint.snapshot().test_paused&&paused_worker(worker.executable)==pid,"worker barrier identity changed");const auto begin=now();require(kill(pid.pid,SIGCONT)==0,"owned worker resume failed");write(run/"resumed.json","{\"begin_ns\":"+std::to_string(begin)+",\"end_ns\":"+std::to_string(now())+"}");wait([&]{return fs::exists(run/"operator-outcome.json");},"sender outcome timeout",30);}
 wait([&]{return fs::exists(run/"settle");},"settle timeout");auto end=now()+2000000000ULL;wait([&]{return now()>=end;},"settle observation timeout",4);write(run/(role+"-result.json"),snapshot(endpoint));wait([&]{return fs::exists(run/"release");},"release timeout");
 const auto stop_begin=now();endpoint.request_stop();endpoint.join();pump();auto stopped=endpoint.snapshot();require(now()-stop_begin<5000000000ULL&&!stopped.running&&!stopped.transport.running&&stopped.worker==WorkerState::stopped,"unclean endpoint/worker stop");
 require(options.transport.command_trace->dropped()==0&&trace_count==options.transport.command_trace->attempted(),"trace loss");if(sender)require(stopped.commands_sent==1&&provider_sends==1,"accepted command replayed or missing SDK handoff");
 write(run/(role+"-stopped.json"),"{\"stop_begin_ns\":"+std::to_string(stop_begin)+",\"stop_end_ns\":"+std::to_string(now())+",\"trace_records\":"+std::to_string(trace_count)+",\"trace_attempted\":"+std::to_string(options.transport.command_trace->attempted())+",\"dropped\":0,\"provider_command_sends\":"+std::to_string(provider_sends)+",\"snapshot\":"+snapshot(endpoint)+"}");return 0;
 }catch(const std::exception& e){std::cerr<<"N4_FAIL "<<e.what()<<std::endl;return 1;}}
