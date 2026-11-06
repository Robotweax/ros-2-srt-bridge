#include <robotweax/srt_bridge/transport.hpp>
#include <algorithm>
#include <atomic>
#include <chrono>
#include <iostream>
#include <thread>
#include <vector>
#include <stdexcept>
#include <arpa/inet.h>
#include <poll.h>
#include <sys/socket.h>
#include <unistd.h>
#include <cerrno>
using namespace robotweax::srt_bridge;
namespace {
unsigned checks=0;
void check(bool ok,const char* text){++checks;if(!ok)throw std::runtime_error(text);}
template<class F> void until(F condition,const char* text,unsigned ms=7000){
    const auto deadline=TransportOwner::monotonic_ns()+std::uint64_t(ms)*1000000;
    do{if(condition()){++checks;return;}std::this_thread::sleep_for(std::chrono::milliseconds(2));}while(TransportOwner::monotonic_ns()<deadline);
    throw std::runtime_error(text);
}
RouteManifest manifest(){
    Route sample;sample.id=1;sample.type_name="sensor_msgs/msg/Imu";sample.type_hash="RIHS01_"+std::string(64,'a');
    Route command{100,RouteKind::command,Direction::listener_to_caller,QosMapping::request_status,true,4000,5000,0,1,
        "robotweax.srt_bridge.v1.SetMeasurementRateCommand",rate_command_schema_hash()};
    const std::array routes{sample,command};return *make_manifest(routes).value;
}
std::string secret(){std::string s;constexpr char hex[]="0123456789abcdef";for(auto b:random_identity()){auto v=std::to_integer<unsigned>(b);s+=hex[v>>4];s+=hex[v&15];}return s;}
TransportConfig config(Role role,const std::string& ip,const std::string& key){
    SessionConfig session{role,role==Role::caller?"robot":"operator",role==Role::caller?"operator":"robot",random_identity(),
        role==Role::caller?1U:2U,manifest(),{1000,1000000,5000000000ULL,100000000}};
    return {std::move(session),{ip,0},{ip,0},key};
}
// Test-owned loopback UDP gate: only the CONTROL path passes through it.
class ControlGate {
    int fd_=-1;unsigned family_;std::uint16_t server_port_,port_=0;
    sockaddr_storage server_{};socklen_t server_length_=0;
    std::atomic<bool> stop_{false};std::thread thread_;
    static std::uint16_t port(const sockaddr_storage& address){return ntohs(address.ss_family==AF_INET?
        reinterpret_cast<const sockaddr_in&>(address).sin_port:reinterpret_cast<const sockaddr_in6&>(address).sin6_port);}
    void run(){
        sockaddr_storage client{};socklen_t client_length=0;std::array<std::byte,65536> bytes{};
        while(!stop_.load()){
            pollfd descriptor{fd_,POLLIN,0};const int ready=::poll(&descriptor,1,5);
            if(ready<0){if(errno==EINTR)continue;failed=true;return;}if(!ready)continue;
            for(unsigned n=0;n<64;++n){sockaddr_storage source{};socklen_t length=sizeof(source);
                const auto count=recvfrom(fd_,bytes.data(),bytes.size(),MSG_DONTWAIT,reinterpret_cast<sockaddr*>(&source),&length);
                if(count<0){if(errno==EAGAIN||errno==EWOULDBLOCK)break;if(errno==EINTR)continue;failed=true;return;}
                const bool from_server=port(source)==server_port_;
                if(from_server){if(!client_length)continue;if(drop_reply.load()){++dropped;continue;}}
                else{client=source;client_length=length;}
                const auto& destination=from_server?client:server_;
                const auto size=from_server?client_length:server_length_;
                if(sendto(fd_,bytes.data(),count,0,reinterpret_cast<const sockaddr*>(&destination),size)!=count){failed=true;return;}
                if(from_server)++forwarded_reply;else ++forwarded_request;
            }
        }
    }
public:
    std::atomic<bool> drop_reply{false},failed{false};
    std::atomic<unsigned> dropped{0},forwarded_reply{0},forwarded_request{0};
    ControlGate(bool ipv6,std::uint16_t server_port):family_(ipv6?AF_INET6:AF_INET),server_port_(server_port){
        fd_=socket(family_,SOCK_DGRAM|SOCK_NONBLOCK|SOCK_CLOEXEC,0);if(fd_<0)throw std::runtime_error("gate socket failed");
        try{
            sockaddr_storage local{};socklen_t length;
            if(ipv6){auto& a=reinterpret_cast<sockaddr_in6&>(local);a.sin6_family=AF_INET6;a.sin6_addr=in6addr_loopback;length=sizeof(a);
                auto& server=reinterpret_cast<sockaddr_in6&>(server_);server=a;server.sin6_port=htons(server_port);}
            else{auto& a=reinterpret_cast<sockaddr_in&>(local);a.sin_family=AF_INET;a.sin_addr.s_addr=htonl(INADDR_LOOPBACK);length=sizeof(a);
                auto& server=reinterpret_cast<sockaddr_in&>(server_);server=a;server.sin_port=htons(server_port);}
            server_length_=length;
            if(bind(fd_,reinterpret_cast<const sockaddr*>(&local),length)||getsockname(fd_,reinterpret_cast<sockaddr*>(&local),&length))throw std::runtime_error("gate bind failed");
            port_=port(local);thread_=std::thread([this]{run();});
        }catch(...){close(fd_);throw;}
    }
    ~ControlGate(){stop_=true;if(thread_.joinable())thread_.join();close(fd_);}
    std::uint16_t listen_port()const{return port_;}
};
void ready(TransportOwner& a,TransportOwner& b){try{until([&]{return a.snapshot().state==SessionState::active&&b.snapshot().state==SessionState::active;},"session not active");}catch(...){for(auto* owner:{&a,&b}){const auto s=owner->snapshot();std::cerr<<"state="<<int(s.state)<<" fault="<<int(s.fault)<<" running="<<s.running<<" gen="<<s.context.control_generation<<","<<s.context.sensor_generation<<" retry="<<int(s.control_retry)<<","<<int(s.sensor_retry)<<" tx/rx/reject="<<s.sent<<","<<s.received<<","<<s.rejected<<"\n";}throw;}}
void stop(TransportOwner& owner){const auto begin=TransportOwner::monotonic_ns();owner.request_stop();owner.join();check(TransportOwner::monotonic_ns()-begin<5ULL*1000000000,"shutdown exceeded five seconds");check(!owner.snapshot().running&&owner.snapshot().state==SessionState::stopped,"not stopped");owner.join();}
// The advertised 200 Hz route must not be decimated by the owner's idle wait.
// A relative delivery gate leaves scheduling slack on the qualified Linux VM.
void cadence(TransportOwner& caller,TransportOwner& listener){
    std::atomic<unsigned> admitted{0};
    std::array<std::byte,8> payload{};
    const auto start=TransportOwner::monotonic_ns();
    std::thread producer([&]{
        const auto origin=std::chrono::steady_clock::now();
        for(unsigned n=0;n<100;++n){
            std::this_thread::sleep_until(origin+std::chrono::milliseconds(5*n));
            if(caller.submit_sample(caller.snapshot().context,1,payload,TransportOwner::monotonic_ns())==SubmitResult::queued)++admitted;
        }
    });
    unsigned delivered=0;TransportMessage sample;
    while(TransportOwner::monotonic_ns()-start<800000000ULL){
        if(listener.poll_sample(sample)&&listener.authorize_sample(sample))++delivered;
        std::this_thread::sleep_for(std::chrono::milliseconds(1));
    }
    producer.join();
    const auto source=caller.snapshot(),sink=listener.snapshot();
    check(source.sensor_submitted==source.sensor_ingress_pending+source.sensor_ingress_replaced+source.sensor_ingress_flushed+source.sensor_inputs,"sender mailbox accounting");
    check(source.sensor_inputs==source.sensor_input_rejected+source.sensor_outbound_pending+source.sensor_outbound_replaced+source.sensor_outbound_expired+source.sensor_outbound_flushed+source.sensor_sent,"sender paced queue accounting");
    check(sink.samples_received==sink.samples_rejected+sink.sensor_receive_pending+sink.sensor_receive_replaced+sink.sensor_receive_flushed+sink.sensor_polled+sink.sensor_poll_expired,"receiver mailbox accounting");
    std::cout<<"cadence admitted="<<admitted.load()<<" delivered="<<delivered<<'\n';
    check(admitted.load()>=80,"200 Hz producer could not enter bounded mailbox");
    check(delivered*10>=admitted.load()*8,"200 Hz route decimated by transport owner cadence");
}
void lifecycle(bool ipv6){
    const auto ip=ipv6?"::1":"127.0.0.1";const auto key=secret();auto listener_config=config(Role::listener,ip,key);
    auto listener=std::make_unique<TransportOwner>(listener_config);
    until([&]{return listener->snapshot().control_port&&listener->snapshot().sensor_port;},"listen failed");
    const auto bound=listener->snapshot();auto caller_config=config(Role::caller,ip,key);
    caller_config.control.port=bound.control_port;caller_config.sensor.port=bound.sensor_port;
    TransportOwner caller(caller_config);ready(caller,*listener);
    const auto old=caller.snapshot().context;check(old.session!=Identity{},"empty session");
    std::array<std::byte,8> payload{};payload[0]=std::byte{0x42};TransportMessage message;
    until([&]{auto result=caller.submit_sample(caller.snapshot().context,1,payload,TransportOwner::monotonic_ns());return result==SubmitResult::queued;},"sample submit failed");
    payload[0]=std::byte{0xff};
    until([&]{return listener->poll_sample(message);},"sample not delivered");
    check(message.payload[0]==std::byte{0x42}&&message.envelope.sequence==1,"payload not owned or wrong sequence");
    check(message.deadline_ns>TransportOwner::monotonic_ns()&&listener->authorize_sample(message),"sample stale/unqualified at publication");
    auto obsolete=message;++obsolete.context.sensor_generation;check(!listener->authorize_sample(obsolete),"obsolete sensor generation authorized");
    obsolete=message;++obsolete.publication_epoch;check(!listener->authorize_sample(obsolete),"obsolete publication epoch authorized");
    check(caller.submit_sample(old,1,payload,TransportOwner::monotonic_ns()-300000000)==SubmitResult::invalid,"expired ingress admitted");
    check(caller.submit_sample(old,1,payload,TransportOwner::monotonic_ns()+1000000000)==SubmitResult::invalid,"future ingress admitted");
    check(caller.submit_sample(old,999,payload,TransportOwner::monotonic_ns())==SubmitResult::invalid,"unknown route admitted");
    cadence(caller,*listener);
    const auto request=random_identity();
    until([&]{return listener->submit_query(listener->snapshot().context,100,request)==SubmitResult::queued;},"query enqueue failed");
    until([&]{return caller.poll_control(message);},"query not received");
    check(message.envelope.kind==Kind::query&&message.envelope.request_id==request&&message.size==0,"wrong query");
    RateCommand command{100,5000,0,1};CommandStatus status{CommandState::succeeded,CommandReason::none,command,command_hash(100,command),{100,1,true},3};
    until([&]{return caller.submit_status(message.context,100,request,status)==SubmitResult::queued;},"status enqueue failed");
    until([&]{return listener->poll_control(message);},"status not received");
    check(decode_command_status(100,message.body())==status,"wrong status");
    // Owner continues serving probes without application polling; source ingress
    // time must survive a deliberately late sample submission.
    const auto ingress=TransportOwner::monotonic_ns()-100000000;
    until([&]{return caller.submit_sample(caller.snapshot().context,1,payload,ingress)==SubmitResult::queued;},"late sample enqueue failed");
    until([&]{return listener->poll_sample(message);},"late sample not received");
    check(message.envelope.source_monotonic_ns==ingress,"mailbox renewed age");
    const auto before=listener->snapshot().received;
    until([&]{return caller.submit_sample(caller.snapshot().context,1,payload,TransportOwner::monotonic_ns())==SubmitResult::queued;},"expiry sample enqueue failed");
    until([&]{return listener->snapshot().received>before;},"expiry sample missing");
    std::this_thread::sleep_for(std::chrono::milliseconds(260));check(!listener->poll_sample(message)&&!listener->authorize_sample(message),"expired sample exposed");
    // Fill the receiver mailbox, leave additional queries buffered in SRT, then
    // drain every request in FIFO order. No application polling during fill.
    std::array<Identity,80> requests{};
    for(auto& id:requests){id=random_identity();until([&]{return listener->submit_query(listener->snapshot().context,100,id)==SubmitResult::queued;},"query flood enqueue failed");}
    until([&]{return caller.snapshot().control_received==64;},"CONTROL mailbox not bounded at 64");
    std::this_thread::sleep_for(std::chrono::milliseconds(60));check(caller.snapshot().control_received==64,"CONTROL overflowed");
    for(const auto& id:requests){until([&]{return caller.poll_control(message);},"query lost under backpressure");check(message.envelope.request_id==id,"CONTROL FIFO order lost");}
    check(!caller.poll_control(message),"duplicate CONTROL event");
    // Stay in this session beyond the five-second probe lifetime. Periodic
    // probes must renew qualification without application help or reconnect.
    const auto renewal_end=TransportOwner::monotonic_ns()+5200000000ULL;
    while(TransportOwner::monotonic_ns()<renewal_end){
        until([&]{return caller.submit_sample(caller.snapshot().context,1,payload,TransportOwner::monotonic_ns())==SubmitResult::queued;},"renewal sample enqueue failed");
        until([&]{return listener->poll_sample(message);},"periodic probe failed to renew clock");
        check(caller.snapshot().context==old,"clock renewal unexpectedly reconnected");
        std::this_thread::sleep_for(std::chrono::milliseconds(100));
    }
    // Recreate listener on exactly the same ports; caller reconnect plans own
    // both channel attempts. No test calls Session or SRT on the owner's behalf.
    const auto held=message;
    stop(*listener);check(!listener->authorize_sample(held),"held sample authorized after stop");listener.reset();listener_config.control.port=bound.control_port;listener_config.sensor.port=bound.sensor_port;
    listener_config.session.local_epoch=random_identity();listener=std::make_unique<TransportOwner>(listener_config);
    until([&]{return caller.snapshot().context.session!=old.session&&caller.snapshot().state==SessionState::active&&listener->snapshot().state==SessionState::active;},"full reconnect failed",12000);
    SubmitResult old_sample=SubmitResult::busy,old_status=SubmitResult::busy;
    until([&]{old_sample=caller.submit_sample(old,1,payload,TransportOwner::monotonic_ns());return old_sample!=SubmitResult::busy;},"old sample admission stayed busy");
    check(old_sample==SubmitResult::obsolete,"old sample work survived reconnect");
    until([&]{old_status=caller.submit_status(old,100,request,status);return old_status!=SubmitResult::busy;},"old status admission stayed busy");
    check(old_status==SubmitResult::obsolete,"old worker result survived reconnect");
    until([&]{return caller.submit_sample(caller.snapshot().context,1,payload,TransportOwner::monotonic_ns())==SubmitResult::queued;},"new session sample enqueue failed");
    until([&]{return listener->poll_sample(message);},"new session sample missing");check(message.envelope.sequence>2,"source sequence reset on reconnect");
    // Concurrent producers cannot grow mailbox storage or make callbacks wait on
    // the network. Stop while submitters are active; stop is idempotent.
    std::atomic<bool> producing{true};std::vector<std::thread> producers;
    for(unsigned n=0;n<4;++n)producers.emplace_back([&]{while(producing.load()){caller.submit_sample(caller.snapshot().context,1,payload,TransportOwner::monotonic_ns());}});
    std::this_thread::sleep_for(std::chrono::milliseconds(40));stop(caller);producing=false;for(auto& thread:producers)thread.join();
    check(caller.submit_sample(caller.snapshot().context,1,payload,TransportOwner::monotonic_ns())==SubmitResult::stopped,"post-stop sample accepted");
    stop(*listener);
    // Stop during a retry wait/connection to an absent listener.
    TransportOwner absent(caller_config);std::this_thread::sleep_for(std::chrono::milliseconds(350));stop(absent);
    auto mismatch=listener_config;mismatch.session.expected_peer_id="different-robot";
    TransportOwner refusing(mismatch);
    until([&]{return refusing.snapshot().control_port!=0;},"refusal listener failed");
    auto refused_config=caller_config;refused_config.control.port=refusing.snapshot().control_port;refused_config.sensor.port=refusing.snapshot().sensor_port;
    TransportOwner refused(refused_config);
    until([&]{return refusing.snapshot().state==SessionState::failed;},"peer mismatch not permanent");
    check(refusing.snapshot().fault==TransportFault::protocol,"peer rejection not diagnosed");
    std::this_thread::sleep_for(std::chrono::milliseconds(300));check(refusing.snapshot().state==SessionState::failed,"permanent error auto-reactivated");
    stop(refused);stop(refusing);
}

void one_way_control_silence(bool ipv6){
    const auto ip=ipv6?"::1":"127.0.0.1";const auto key=secret();
    auto lc=config(Role::listener,ip,key);TransportOwner listener(lc);
    until([&]{return listener.snapshot().control_port&&listener.snapshot().sensor_port;},"silence listener missing");
    ControlGate gate(ipv6,listener.snapshot().control_port);
    auto cc=config(Role::caller,ip,key);cc.control.port=gate.listen_port();cc.sensor.port=listener.snapshot().sensor_port;
    cc.command_trace=std::make_shared<CommandTrace>();TransportOwner caller(cc);ready(caller,listener);
    check(gate.forwarded_reply>0&&gate.forwarded_request>0&&!gate.failed,"gate did not forward handshake both ways");
    const auto reverse_before=gate.forwarded_request.load();const auto blocked=TransportOwner::monotonic_ns();gate.drop_reply=true;
    CommandTraceEvent event;bool control_lost=false,session_closed=false;std::uint64_t lost_at=0;
    until([&]{while(cc.command_trace->poll(event)){
        if(event.point==CommandTracePoint::link_lost&&event.detail==0){
            check(event.reason==CommandTraceReason::socket_state||event.reason==CommandTraceReason::epoll_error||event.reason==CommandTraceReason::receive_error,"one-way silence did not use provider loss path");
            control_lost=true;lost_at=event.monotonic_ns;
        }
        if(event.point==CommandTracePoint::session_action&&(event.detail&1)&&event.monotonic_ns>=blocked){
            check(event.value==unsigned(SessionError::none)&&event.reason==CommandTraceReason::session_decision,"one-way silence closed on a local protocol/clock error");session_closed=true;
        }
    }return control_lost&&session_closed;},"one-way CONTROL silence did not surface loss",10000);
    check(lost_at>=blocked+3000000000ULL,"provider loss was not an idle interval");
    check(gate.dropped>0&&gate.forwarded_request>reverse_before&&!gate.failed,"silence was not directional/observed");
    check(cc.command_trace->dropped()==0,"silence cause trace incomplete");
    stop(caller);stop(listener);
    std::cout<<"PASS one-way CONTROL silence: provider loss before session close; blocked_ms="<<(lost_at-blocked)/1000000<<", dropped="<<gate.dropped.load()<<", reverse_forwarded="<<gate.forwarded_request.load()-reverse_before<<"\n";
}

}
int main(int argc,char** argv){try{check(argc==2,"family required");lifecycle(std::string(argv[1])=="ipv6");one_way_control_silence(std::string(argv[1])=="ipv6");std::cout<<"PASS transport owner "<<argv[1]<<": "<<checks<<" checks\n";return 0;}catch(const std::exception& e){std::cerr<<"FAIL: "<<e.what()<<"\n";return 1;}}
