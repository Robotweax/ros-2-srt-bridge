#include <robotweax/srt_bridge/endpoint.hpp>
#include <robotweax/srt_bridge/sender_trace_json.hpp>
#include <robotweax/srt_bridge/probe_trace_json.hpp>
#include <chrono>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <sstream>
#include <thread>
#include <vector>
#include <unistd.h>
using namespace robotweax::srt_bridge;
namespace {
void check(bool ok,const char* message){if(!ok)throw std::runtime_error(message);}
uint64_t now(){return TransportOwner::monotonic_ns();}
std::string hex(Identity id){std::string s;constexpr char h[]="0123456789abcdef";for(auto b:id){auto n=std::to_integer<unsigned>(b);s+=h[n>>4];s+=h[n&15];}return s;}
EndpointOptions options(Role role,const std::string& ip,const std::string& key,const std::filesystem::path& path,bool enabled){
    Route route{100,RouteKind::command,Direction::listener_to_caller,QosMapping::request_status,true,4000,5000,0,1,"robotweax.srt_bridge.v1.SetMeasurementRateCommand",rate_command_schema_hash()};
    SessionConfig s{role,role==Role::caller?"robot":"operator",role==Role::caller?"operator":"robot",random_identity(),role==Role::caller?1U:2U,*make_manifest(std::span(&route,1)).value,{1000,1000000,5000000000ULL,100000000}};
    EndpointOptions o{{s,{ip,0},{ip,0},key},WorkerOptions{}};o.transport.command_trace=std::make_shared<CommandTrace>();o.transport.sender_diagnostics=enabled;o.transport.probe_diagnostics=enabled;
    o.worker.executable=WORKER_EXECUTABLE;o.worker.journal.path=path.string();o.worker.journal.local_peer_id=s.local_peer_id;o.worker.journal.remote_peer_id=s.expected_peer_id;o.worker.journal.process_epoch=s.local_epoch;
    o.worker.journal.side=role==Role::listener?JournalSide::sender:JournalSide::receiver;o.worker.simulated_rate_handler=role==Role::caller;return o;
}
void write(const std::filesystem::path& path,const std::vector<CommandTraceEvent>& rows,const CommandTrace& trace){
    std::ofstream f(path);for(const auto& e:rows){
        f<<"COMMAND_TRACE {\"sequence\":"<<e.sequence<<",\"monotonic_ns\":"<<e.monotonic_ns<<",\"point\":"<<unsigned(e.point)<<",\"reason\":"<<unsigned(e.reason)
         <<",\"request\":\""<<hex(e.request)<<"\",\"session\":\""<<hex(e.session)<<"\",\"owner_epoch\":\""<<hex(e.owner_epoch)<<"\",\"entry_owner_epoch\":\""<<hex(e.entry_owner_epoch)
         <<"\",\"control_generation\":"<<e.control_generation<<",\"sensor_generation\":"<<e.sensor_generation<<",\"route\":"<<e.route<<",\"value\":"<<e.value<<",\"detail\":"<<e.detail
         <<",\"request_sequence\":"<<e.request_sequence<<",\"origin_ns\":"<<e.origin_ns<<",\"evaluated_ns\":"<<e.evaluated_ns<<",\"age_error\":"<<e.age_error<<",\"clock_error\":"<<e.clock_error<<",\"clock_deadline_ns\":"<<e.clock_deadline_ns;
        append_sender_trace_json(f,e);append_probe_trace_json(f,e);f<<"}\n";
    }
    f<<"COMMAND_TRACE_STATUS {\"attempted\":"<<trace.attempted()<<",\"dropped\":"<<trace.dropped()<<"}\n";check(f.good(),"trace write failed");
}
void scenario(const std::string& ip,const std::filesystem::path& path,bool enabled){
    std::filesystem::create_directories(path);auto oc=options(Role::listener,ip,hex(random_identity()),path/"sender.sqlite",enabled);
    if(enabled){auto bad=oc.transport;bad.sender_diagnostics=false;bad.command_trace.reset();bool refused=false;try{TransportOwner invalid(bad);}catch(const std::invalid_argument&){refused=true;}check(refused,"missing trace accepted");}
    CommandEndpoint op(oc);std::vector<CommandTraceEvent> rows,peer_rows;std::shared_ptr<CommandTrace> peer_trace;
    auto drain=[&]{CommandTraceEvent e;while(oc.transport.command_trace->poll(e)){check(rows.size()<2048,"trace capture bound");rows.push_back(e);}if(peer_trace)while(peer_trace->poll(e)){check(peer_rows.size()<2048,"peer trace capture bound");peer_rows.push_back(e);}};
    auto until=[&](auto predicate,const char* label){const auto end=now()+10000000000ULL;while(true){drain();if(predicate())break;check(now()<end,label);std::this_thread::sleep_for(std::chrono::milliseconds(1));}};
    until([&]{return op.snapshot().transport.control_port!=0;},"listen failed");
    auto rc=options(Role::caller,ip,oc.transport.passphrase,path/"receiver.sqlite",false);rc.transport.probe_diagnostics=enabled;peer_trace=rc.transport.command_trace;rc.transport.control.port=op.snapshot().transport.control_port;rc.transport.sensor.port=op.snapshot().transport.sensor_port;CommandEndpoint robot(rc);
    until([&]{return op.snapshot().ready&&robot.snapshot().ready&&op.snapshot().transport.clock_qualified&&robot.snapshot().transport.clock_qualified;},"qualified readiness failed");
    const auto id=random_identity();const auto origin=now();
    until([&]{return op.execute(100,id,{100,5000,0,1},origin)==SubmitResult::queued;},"submit failed");
    CommandEvent event;until([&]{while(op.poll(event))if(event.request_id==id&&event.entry&&event.entry->state==CommandState::succeeded)return true;return false;},"success missing");
    if(enabled){auto accepted=[](const auto& v){unsigned n=0;for(const auto& e:v)if(e.point==CommandTracePoint::probe_admission&&e.detail==10&&e.probe_mapper_submitted&&e.clock_error==0)++n;return n;};until([&]{return accepted(rows)>=2&&accepted(peer_rows)>=2;},"reciprocal probe renewals missing");}
    check(robot.snapshot().effects==1,"effect count changed");op.request_stop();op.join();robot.request_stop();robot.join();drain();
    unsigned releases=0,journals=0,emissions=0,handoffs=0;
    for(const auto& e:rows){
        if(e.request==id&&e.point==CommandTracePoint::provider_sent)++handoffs;
        if(unsigned(e.point)<45||unsigned(e.point)>48)continue;
        check(enabled&&e.request==id&&e.owner_epoch==oc.transport.session.local_epoch,"sender diagnostic provenance");
        if(e.point==CommandTracePoint::sender_pending_release){++releases;check(e.value==4&&e.origin_ns==origin&&e.command_deadline_ns==origin+5000000000ULL,"release changed original context");}
        if(e.point==CommandTracePoint::sender_journal){++journals;check(e.worker_token!=0,"worker token missing");}
        if(e.point==CommandTracePoint::sender_event){++emissions;check(e.journal_entry_available&&e.terminal_state!=0,"event entry missing");}
    }
    check(handoffs==1,"SDK handoff count changed");check(enabled?(releases==1&&journals>=2&&emissions>=2):(releases+journals+emissions==0),"sender trace coverage");
    check(oc.transport.command_trace->dropped()==0&&rows.size()==oc.transport.command_trace->attempted(),"loss in calibration");
    for(const auto* v:{&rows,&peer_rows}){unsigned n=0;for(const auto& e:*v)if(unsigned(e.point)>=50&&unsigned(e.point)<=54)++n;check(enabled?n>=8:n==0,"probe trace enable/disable coverage");}
    check(rc.transport.command_trace->dropped()==0,"peer trace loss");
    write(path/"operator.log",rows,*oc.transport.command_trace);write(path/"robot.log",peer_rows,*rc.transport.command_trace);
    std::cout<<"PROBE_TRACING enabled="<<enabled<<" request="<<hex(id)<<" effects=1 releases="<<releases<<" journals="<<journals<<" emissions="<<emissions<<"\n";
}
}
int main(int argc,char** argv){try{check(argc==2,"family required");const std::string family=argv[1];check(family=="ipv4"||family=="ipv6","invalid family");const char* output=std::getenv("PROBE_TRACE_OUTPUT");
    const auto root=output?std::filesystem::path(output)/family:std::filesystem::path("/tmp")/("probe-tracing-"+std::to_string(getpid()));check(!std::filesystem::exists(root),"fixture output exists");
    const auto ip=family=="ipv4"?"127.0.0.1":"::1";scenario(ip,root/"enabled",true);scenario(ip,root/"disabled",false);
    if(!output)std::filesystem::remove_all(root);
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}}
