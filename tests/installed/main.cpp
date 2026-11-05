#include <robotweax/srt_bridge/endpoint.hpp>
#include <chrono>
#include <filesystem>
#include <iostream>
#include <thread>
using namespace robotweax::srt_bridge;
namespace {
void require(bool ok){if(!ok)throw std::runtime_error("installed bridge consumer assertion");}
std::uint64_t now(){return TransportOwner::monotonic_ns();}
template<class F> void until(F test){const auto end=now()+8000000000ULL;while(!test()){require(now()<end);std::this_thread::sleep_for(std::chrono::milliseconds(1));}}
std::string secret(){std::string key;constexpr char hex[]="0123456789abcdef";for(auto b:random_identity()){auto v=std::to_integer<unsigned>(b);key+=hex[v>>4];key+=hex[v&15];}return key;}
EndpointOptions options(Role role,const std::string& key){
    Route route{100,RouteKind::command,Direction::listener_to_caller,QosMapping::request_status,true,4000,5000,0,1,"robotweax.srt_bridge.v1.SetMeasurementRateCommand",rate_command_schema_hash()};
    SessionConfig s{role,role==Role::caller?"robot":"operator",role==Role::caller?"operator":"robot",random_identity(),role==Role::caller?1U:2U,*make_manifest(std::span(&route,1)).value,{1000,1000000,5000000000ULL,100000000}};
    WorkerOptions w;w.executable=WORKER_EXECUTABLE;w.journal.path=(std::filesystem::current_path()/(role==Role::caller?"receiver.sqlite":"sender.sqlite")).string();w.journal.local_peer_id=s.local_peer_id;w.journal.remote_peer_id=s.expected_peer_id;w.journal.process_epoch=s.local_epoch;w.journal.side=role==Role::caller?JournalSide::receiver:JournalSide::sender;w.simulated_rate_handler=role==Role::caller;
    return {{std::move(s),{"127.0.0.1",0},{"127.0.0.1",0},key},w};
}
}
int main(){try{
    std::array<std::byte,64> body{};const ControlError diagnostic{ControlErrorCode::not_found,Kind::query,9,0};const auto encoded=encode_control_error(diagnostic,body);require(encoded&&decode_control_error(std::span(body).first(encoded.bytes_written))==diagnostic);
    const auto key=secret();auto operator_options=options(Role::listener,key);CommandEndpoint op(operator_options);until([&]{return op.snapshot().transport.control_port!=0;});
    auto receiver_options=options(Role::caller,key);receiver_options.transport.control.port=op.snapshot().transport.control_port;receiver_options.transport.sensor.port=op.snapshot().transport.sensor_port;CommandEndpoint robot(receiver_options);
    until([&]{return op.snapshot().ready&&robot.snapshot().ready;});const auto id=random_identity();const RateCommand command{100,5000,0,1};
    until([&]{return op.execute(100,id,command,now())==SubmitResult::queued;});CommandEvent event;
    const auto succeeded=[&]{while(op.poll(event))if(event.request_id==id&&event.entry&&event.entry->state==CommandState::succeeded)return true;return false;};until(succeeded);
    require(event.entry->result==RateResult{100,1,true}&&robot.snapshot().effects==1);
    until([&]{return op.execute(100,id,command,now())==SubmitResult::queued;});until(succeeded);require(op.snapshot().commands_sent==1&&robot.snapshot().effects==1);
    op.request_stop();robot.request_stop();op.join();robot.join();require(!op.snapshot().running&&!robot.snapshot().running&&op.snapshot().worker==WorkerState::stopped&&robot.snapshot().worker==WorkerState::stopped);
    std::cout<<"PASS installed bridge consumer: relocated targets/worker, durable command/status, duplicate suppression\n";return 0;
}catch(const std::exception& error){std::cerr<<"FAIL: "<<error.what()<<'\n';return 1;}}
