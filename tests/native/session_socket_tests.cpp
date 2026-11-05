#include <robotweax/srt_bridge/session.hpp>
#include <robotweax/srt_bridge/queues.hpp>
#include <robotweax/srt_bridge/bandwidth.hpp>
#include <robotweax/srt_bridge/journal.hpp>
#include <filesystem>
#include <unistd.h>
#include <srt/srt.h>
#include <arpa/inet.h>
#include <array>
#include <chrono>
#include <iostream>
#include <memory>
#include <stdexcept>
#include <thread>
using namespace robotweax::srt_bridge;
namespace {
using Clock=std::chrono::steady_clock;
void check(bool ok,const char* message) { if (!ok) throw std::runtime_error(message); }
void api(int value,const char* operation) { if(value==SRT_ERROR) throw std::runtime_error(std::string(operation)+": "+srt_getlasterror_str()); }
std::uint64_t now() { return std::chrono::duration_cast<std::chrono::nanoseconds>(Clock::now().time_since_epoch()).count(); }
template<class T> void set(SRTSOCKET s,SRT_SOCKOPT flag,T value) { api(srt_setsockflag(s,flag,&value,sizeof(value)),"set option"); }
template<class T> T get(SRTSOCKET s,SRT_SOCKOPT flag) { T value{};int size=sizeof(value);api(srt_getsockflag(s,flag,&value,&size),"get option");check(size==sizeof(value),"option size");return value; }
struct Runtime { Runtime(){api(srt_startup(),"startup");} ~Runtime(){srt_cleanup();} };
struct Socket {
    SRTSOCKET fd=srt_create_socket();
    Socket(){check(fd!=SRT_INVALID_SOCK,"create socket");}
    Socket(const Socket&)=delete; Socket& operator=(const Socket&)=delete;
    ~Socket(){if(fd!=SRT_INVALID_SOCK)srt_close(fd);}
    void close(){if(fd!=SRT_INVALID_SOCK){api(srt_close(fd),"close");fd=SRT_INVALID_SOCK;}}
};
int wait(SRTSOCKET s,int events,int timeout=2000) {
    const int id=srt_epoll_create(); check(id>=0,"epoll create"); events|=SRT_EPOLL_ERR;
    api(srt_epoll_add_usock(id,s,&events),"epoll add"); SRT_EPOLL_EVENT event{};
    const int count=srt_epoll_uwait(id,&event,1,timeout); const int saved_error=srt_getlasterror(nullptr);
    srt_epoll_release(id); (void)saved_error;
    api(count,"epoll wait"); check(!count||event.fd==s,"wrong event descriptor"); return count?event.events:0;
}
std::string secret() {
    std::string result; constexpr char hex[]="0123456789abcdef";
    for(int i=0;i<2;++i) for(auto byte:random_identity()) { auto v=std::to_integer<unsigned>(byte);result+=hex[v>>4];result+=hex[v&15]; }
    return result;
}
void configure(SRTSOCKET s,Channel profile,bool ipv6,const std::string& key) {
    set(s,SRTO_TRANSTYPE,profile==Channel::control?SRTT_CONTROL:SRTT_SENSOR);
    set(s,SRTO_MSS,ipv6?1280:1500); set(s,SRTO_CRYPTOMODE,2);set(s,SRTO_ENFORCEDENCRYPTION,true);
    set(s,SRTO_ROBOTWEAX_SESSIONAUTH,true);set(s,SRTO_PBKEYLEN,32);
    api(srt_setsockflag(s,SRTO_PASSPHRASE,key.data(),key.size()),"set test credential");
    set(s,SRTO_PAYLOADSIZE,1024);set(s,SRTO_FC,256);set(s,SRTO_SNDBUF,262144);set(s,SRTO_RCVBUF,262144);
    set(s,SRTO_UDP_SNDBUF,262144);set(s,SRTO_UDP_RCVBUF,262144);
    set(s,SRTO_CONNTIMEO,1000);set(s,SRTO_SNDSYN,false);set(s,SRTO_RCVSYN,false);set(s,SRTO_LINGER,linger{0,0});
}
struct SocketPair {
    Socket listener,caller,accepted;
    SocketPair(Channel channel,bool ipv6,const std::string& key) {
        configure(listener.fd,channel,ipv6,key);configure(caller.fd,channel,ipv6,key);
        sockaddr_storage address{};int length;
        if(ipv6){auto& a=reinterpret_cast<sockaddr_in6&>(address);a.sin6_family=AF_INET6;a.sin6_addr=in6addr_loopback;length=sizeof(a);}
        else {auto& a=reinterpret_cast<sockaddr_in&>(address);a.sin_family=AF_INET;a.sin_addr.s_addr=htonl(INADDR_LOOPBACK);length=sizeof(a);}
        api(srt_bind(listener.fd,reinterpret_cast<sockaddr*>(&address),length),"bind");
        api(srt_getsockname(listener.fd,reinterpret_cast<sockaddr*>(&address),&length),"getsockname");api(srt_listen(listener.fd,4),"listen");
        api(srt_connect(caller.fd,reinterpret_cast<sockaddr*>(&address),length),"connect");
        const auto ready=wait(caller.fd,SRT_EPOLL_OUT);check((ready&SRT_EPOLL_OUT)&&!(ready&SRT_EPOLL_ERR),"connect readiness");
        check(wait(listener.fd,SRT_EPOLL_IN)&SRT_EPOLL_IN,"accept readiness");accepted.close();
        accepted.fd=srt_accept(listener.fd,nullptr,nullptr);check(accepted.fd!=SRT_INVALID_SOCK,"accept");
    }
};
Security evidence(SRTSOCKET s,Channel channel) {
    check(get<SRT_TRANSTYPE>(s,SRTO_TRANSTYPE)==(channel==Channel::control?SRTT_CONTROL:SRTT_SENSOR),"profile downgrade");
    const auto deadline=Clock::now()+std::chrono::seconds(2);
    while(get<int>(s,SRTO_SNDKMSTATE)!=SRT_KM_S_SECURED||get<int>(s,SRTO_RCVKMSTATE)!=SRT_KM_S_SECURED){
        check(Clock::now()<deadline,"key confirmation deadline");std::this_thread::sleep_for(std::chrono::milliseconds(1));
    }
    return {channel,get<int>(s,SRTO_CRYPTOMODE)==2,get<bool>(s,SRTO_ROBOTWEAX_SESSIONAUTH),get<bool>(s,SRTO_ENFORCEDENCRYPTION)};
}
void send_bytes(SRTSOCKET s,std::span<const std::byte> bytes,Channel channel) {
    const auto deadline=Clock::now()+std::chrono::seconds(2);
    for(;;){const auto count=srt_sendmsg(s,reinterpret_cast<const char*>(bytes.data()),bytes.size(),channel==Channel::control?-1:250,0);
        if(count!=SRT_ERROR){check(count==static_cast<int>(bytes.size()),"partial message");return;}
        check(srt_getlasterror(nullptr)==SRT_EASYNCSND&&Clock::now()<deadline,"send failure/deadline");
        check(!(wait(s,SRT_EPOLL_OUT,100)&SRT_EPOLL_ERR),"send readiness error");}
}
void drain(OutboundQueues& queue,BandwidthBudget& budget,SRTSOCKET socket,Channel channel,bool binding=false){
    const auto deadline=Clock::now()+std::chrono::seconds(2);
    for(;;){
        const auto time=now();
        const auto* packet=channel==Channel::control?queue.control_front():(binding?queue.binding_front():queue.sensor_front(time));
        check(packet!=nullptr,"queued packet expired or disappeared");
        auto permit=budget.reserve(channel,packet->size,time);
        if(!permit){check(permit.error==BudgetError::rate_limited&&Clock::now()<deadline,"bandwidth admission/deadline");
            std::this_thread::sleep_for(std::chrono::milliseconds(1));continue;}
        const int ttl=channel==Channel::control?-1:(binding?200:sensor_ttl_ms(*packet,time));
        const int count=srt_sendmsg(socket,reinterpret_cast<const char*>(packet->bytes.data()),packet->size,ttl,0);
        const int error=count==SRT_ERROR?srt_getlasterror(nullptr):0;
        check(budget.finish(permit.id,count!=SRT_ERROR),"budget resolution");
        if(count!=SRT_ERROR){
            check(count==static_cast<int>(packet->size),"partial queued send");
            const auto route=packet->envelope.route_id;
            if(channel==Channel::control)queue.control_sent();else if(binding)queue.binding_sent();else queue.sensor_sent(route);
            return;
        }
        check(error==SRT_EASYNCSND&&Clock::now()<deadline,"queued send failure/deadline");
        check(!(wait(socket,SRT_EPOLL_OUT,100)&SRT_EPOLL_ERR),"queued send readiness");
    }
}
struct Frame { std::array<std::byte,4096> bytes{};std::size_t size=0; };
Frame receive_bytes(SRTSOCKET s) {
    Frame result;const auto deadline=Clock::now()+std::chrono::seconds(2);
    for(;;){const auto count=srt_recvmsg(s,reinterpret_cast<char*>(result.bytes.data()),result.bytes.size());
        if(count!=SRT_ERROR){result.size=count;return result;}
        check(srt_getlasterror(nullptr)==SRT_EASYNCRCV&&Clock::now()<deadline,"receive failure/deadline");
        check(!(wait(s,SRT_EPOLL_IN,100)&SRT_EPOLL_ERR),"receive readiness error");}
}
RouteManifest manifest() {
    Route route;route.id=1;route.type_name="sensor_msgs/msg/Imu";route.type_hash="RIHS01_"+std::string(64,'a');
    Route command{100,RouteKind::command,Direction::listener_to_caller,QosMapping::request_status,true,4000,5000,0,1,
        "robotweax.srt_bridge.v1.SetMeasurementRateCommand",rate_command_schema_hash()};
    const std::array routes{route,command};auto m=make_manifest(routes);check(bool(m),"manifest");return *m.value;
}
SessionConfig config(Role role) {
    return {role,role==Role::caller?"robot":"operator",role==Role::caller?"operator":"robot",random_identity(),
            role==Role::caller?1U:2U,manifest(),{0,0,5000000000ULL,50000000}};
}
struct Harness {
    bool ipv6;std::string key=secret();Session c{config(Role::caller)},l{config(Role::listener)};
    std::unique_ptr<SocketPair> control,sensor;
    std::uint64_t cg=0,lg=10,cs=0,ls=10;
    std::unique_ptr<OutboundQueues> cq=std::make_unique<OutboundQueues>(manifest()),lq=std::make_unique<OutboundQueues>(manifest());
    BandwidthBudget cb{{1000000,128000,131072,16384,65536},now()},lb{{1000000,128000,131072,16384,65536},now()};
    std::unique_ptr<CommandJournal> sender,receiver;
    Identity request{};std::uint32_t device_rate=200;std::uint64_t device_generation=0,effects=0;
    Envelope command_envelope{};RateCommand command{100,5000,0,1};
    explicit Harness(bool family):ipv6(family){}
    void journals(){
        auto directory=std::filesystem::current_path()/("native-journal-"+std::to_string(getpid()));
        for(unsigned suffix=0;std::filesystem::exists(directory);++suffix)directory=std::filesystem::current_path()/("native-journal-"+std::to_string(getpid())+"-"+std::to_string(suffix));
        JournalOptions s;s.path=(directory/"sender.sqlite").string();s.local_peer_id="operator";s.remote_peer_id="robot";s.side=JournalSide::sender;
        s.process_epoch=l.local_epoch();
        auto r=s;r.path=(directory/"receiver.sqlite").string();r.local_peer_id="robot";r.remote_peer_id="operator";r.side=JournalSide::receiver;
        r.process_epoch=c.local_epoch();
        sender=std::make_unique<CommandJournal>(s);receiver=std::make_unique<CommandJournal>(r);
    }
    SampleResult control_frame(bool from_caller,const Envelope& envelope,std::span<const std::byte> payload){
        auto& queue=from_caller?*cq:*lq;const Connection connection{Channel::control,from_caller?cg:lg};
        check(queue.control(connection,envelope,payload)==QueueError::none,"command/status queue");
        drain(queue,from_caller?cb:lb,from_caller?control->caller.fd:control->accepted.fd,Channel::control);
        auto frame=receive_bytes(from_caller?control->accepted.fd:control->caller.fd);
        const std::array<std::uint32_t,2> routes{1,100};const auto decoded=decode(std::span(frame.bytes).first(frame.size),Channel::control,routes);check(bool(decoded),"command frame decode");
        const auto result=(from_caller?l:c).admit_control({Channel::control,from_caller?lg:cg},decoded.message,now());
        check(result.envelope.has_value(),"CONTROL application gate");
        if(from_caller){auto status=decode_command_status(100,decoded.message.payload);check(status.has_value(),"status codec");
            check(sender->observe_remote(envelope.request_id,100,*status,now())==JournalError::none,"sender status persistence");}
        return result;
    }
    void send_status(const JournalEntry& entry){
        CommandStatus status{entry.state,entry.reason,entry.command,entry.payload_hash,entry.result,entry.revision};std::array<std::byte,256> bytes{};
        const auto encoded=encode_command_status(100,status,bytes);check(bool(encoded),"status encoding");
        auto frame=c.make_control(Kind::status,100,entry.request_id,encoded.bytes_written,0,now());check(frame.envelope.has_value(),"status envelope");
        control_frame(true,*frame.envelope,std::span(bytes).first(encoded.bytes_written));
    }
    void execute(){
        journals();request=random_identity();std::array<std::byte,256> bytes{};const auto encoded=encode_rate_command(command,bytes);check(bool(encoded),"command codec");
        const auto origin=now();auto frame=l.make_control(Kind::command,100,request,encoded.bytes_written,origin,origin);check(frame.envelope.has_value(),"command envelope");command_envelope=*frame.envelope;
        auto queued=sender->admit(request,100,command,{l.session_id(),command_envelope.source_epoch,origin,origin+5000000000ULL},now());
        check(queued&&queued.entry->state==CommandState::local_queued&&sender->sender_may_transmit(request,l.session_id(),now()),"send before durable local admission");
        auto gate=control_frame(false,command_envelope,std::span(bytes).first(encoded.bytes_written));
        const auto received=now();const auto remaining=5000000000ULL-static_cast<std::uint64_t>(gate.age.age_ns->upper);
        auto accepted=receiver->admit(request,100,command,{c.session_id(),command_envelope.source_epoch,origin,gate.evaluated_ns+remaining},received);
        check(accepted&&accepted.entry->state==CommandState::accepted,"receiver admission commit");send_status(*accepted.entry);
        auto before=c.check_command(command_envelope,now());check(before.envelope.has_value(),"pre-dispatch freshness");
        auto dispatch=receiver->begin_dispatch(request,c.session_id(),true,now());check(dispatch&&dispatch.entry->state==CommandState::dispatching,"dispatch commit");
        check(c.check_command(command_envelope,now()).envelope.has_value(),"post-commit freshness");
        check(device_generation==command.expected_generation,"generation precondition");device_rate=command.rate_hz;device_generation=command.new_generation;++effects;
        auto result=receiver->finish(request,CommandState::succeeded,CommandReason::none,{device_rate,device_generation,true},now());check(result&&result.entry->result.valid,"result commit");
        check(sender->get(request).entry->state==CommandState::accepted,"execution result leaked before acknowledgment");
        auto other=command;other.rate_hz=300;check(receiver->admit(request,100,other,result.entry->context,now()).error==JournalError::conflict&&effects==1,"conflict executed again");
        // Deliberately withhold the result until after CONTROL reconnect.
    }
    void reconcile(){
        check(!sender->sender_may_transmit(request,l.session_id(),now()),"reconnect replayed COMMAND");
        // Start budget is finite; a later QUERY must still recover committed results.
        std::this_thread::sleep_for(std::chrono::milliseconds(5100));
        check(!l.make_control(Kind::command,100,request,0,now(),now()).envelope,"unqualified clock admitted new COMMAND");
        auto query=l.make_control(Kind::query,100,request,0,0,now());check(query.envelope.has_value(),"query gated by execution expiry");
        control_frame(false,*query.envelope,{});auto stored=receiver->get(request);check(stored&&stored.entry->state==CommandState::succeeded,"committed result missing");send_status(*stored.entry);
        check(sender->get(request).entry->result==RateResult{100,1,true}&&effects==1&&device_rate==100&&device_generation==1,"reconciliation changed effect or result");
        check(receiver->begin_dispatch(request,c.session_id(),true,now()).error==JournalError::invalid_state,"completed ID dispatched again");
    }
    void apply(bool caller,const SessionAction& action,Identity old_session={}){
        auto& q=caller?*cq:*lq;const auto removed=q.apply(action);check(removed.count==0,"unexpected queued commands in socket harness");
        if(action.close_control&&sender&&receiver)check((caller?receiver:sender)->invalidate_session(old_session,now())==JournalError::none,"journal context invalidation");
    }
    SessionAction deliver(SessionAction action,bool from_caller) {
        check(action.error==SessionError::none&&action.send.has_value(),"missing management send");
        auto& out=*action.send;const bool is_control=out.connection.channel==Channel::control;
        check(out.connection.generation==(is_control?(from_caller?cg:lg):(from_caller?cs:ls)),"stale outbound socket generation");
        auto& sockets=*(is_control?control:sensor);
        std::array<std::byte,512> payload{};const auto packed=encode_management(out.payload,payload);check(bool(packed),"management encoding");
        const std::array<std::uint32_t,2> routes{1,100};auto& queue=from_caller?*cq:*lq;
        const auto admitted=is_control?queue.control(out.connection,out.envelope,std::span(payload).first(packed.bytes_written)):
            queue.binding(out.connection,out.envelope,std::span(payload).first(packed.bytes_written));
        check(admitted==QueueError::none,"management queue admission");
        drain(queue,from_caller?cb:lb,from_caller?sockets.caller.fd:sockets.accepted.fd,out.connection.channel,!is_control);
        auto received=receive_bytes(from_caller?sockets.accepted.fd:sockets.caller.fd);
        const auto parsed=decode(std::span(received.bytes).first(received.size),out.connection.channel,routes);check(bool(parsed),"wire decoding");
        return (from_caller?l:c).receive({out.connection.channel,is_control?(from_caller?lg:cg):(from_caller?ls:cs)},parsed.message,now());
    }
    void handshake() {
        control=std::make_unique<SocketPair>(Channel::control,ipv6,key);++cg;++lg;
        check(cq->open({Channel::control,cg})==QueueError::none&&lq->open({Channel::control,lg})==QueueError::none,"CONTROL queue binding");
        check(l.control_connected(lg,evidence(control->accepted.fd,Channel::control),now(),random_identity()).error==SessionError::none,"listener start");
        auto welcome=deliver(c.control_connected(cg,evidence(control->caller.fd,Channel::control),now()),true);
        check(deliver(std::move(welcome),false).error==SessionError::none,"WELCOME");
        auto reply=deliver(c.begin_probe(now()),true);auto ready=deliver(std::move(reply),false);check(deliver(std::move(ready),true).error==SessionError::none,"caller READY");
        reply=deliver(l.begin_probe(now()),false);ready=deliver(std::move(reply),true);check(deliver(std::move(ready),false).error==SessionError::none,"listener READY");
        check(c.state()==SessionState::control_active&&l.state()==SessionState::control_active,"CONTROL not active");
    }
    SessionAction bind() {
        sensor=std::make_unique<SocketPair>(Channel::sensor,ipv6,key);++cs;++ls;
        check(cq->open({Channel::sensor,cs})==QueueError::none&&lq->open({Channel::sensor,ls})==QueueError::none,"SENSOR queue binding");
        check(l.sensor_connected(ls,evidence(sensor->accepted.fd,Channel::sensor),now()).error==SessionError::none,"listener SENSOR");
        return deliver(c.sensor_connected(cs,evidence(sensor->caller.fd,Channel::sensor),now(),random_identity()),true);
    }
    Envelope sample(std::uint64_t expected) {
        const auto admitted=c.make_sample(1,4,now());check(admitted.envelope.has_value(),"sample creation");
        check(admitted.envelope->sequence==expected,"source sequence reset");
        publish(*admitted.envelope,true);return *admitted.envelope;
    }
    void publish(const Envelope& e,bool accept) {
        const std::array<std::byte,4> payload{std::byte{0xde},std::byte{0xad},std::byte{0xbe},std::byte{0xef}};
        const std::array<std::uint32_t,2> routes{1,100};std::array<std::byte,1024> bytes{};
        const auto packed=encode(e,payload,Channel::sensor,routes,bytes);check(bool(packed),"sample encoding");
        if(accept){check(cq->sensor({Channel::sensor,cs},e,payload,now())==QueueError::none,"sample queue admission");
            drain(*cq,cb,sensor->caller.fd,Channel::sensor);
        }else send_bytes(sensor->caller.fd,std::span(bytes).first(packed.bytes_written),Channel::sensor); // fault injection bypasses sender gate
        auto frame=receive_bytes(sensor->accepted.fd);const auto decoded=decode(std::span(frame.bytes).first(frame.size),Channel::sensor,routes);check(bool(decoded),"sample decode");
        const auto result=l.admit_sample({Channel::sensor,ls},decoded.message,now());
        if(accept){check(result.envelope&&result.age.within_budget(250000000),"freshness admission");
            check(std::equal(payload.begin(),payload.end(),decoded.message.payload.begin(),decoded.message.payload.end()),"sample payload");}
        else check(result.action.error==SessionError::stale_session&&!result.envelope,"old session was published");
    }
    void run() {
        handshake();auto old_ack=bind();
        const auto c_lost=c.sensor_lost(cs),l_lost=l.sensor_lost(ls);
        check(c_lost.flush_samples&&l_lost.flush_samples,"sensor loss flush");apply(true,c_lost);apply(false,l_lost);sensor.reset();
        auto fresh_ack=bind();check(deliver(std::move(old_ack),false).error==SessionError::binding_mismatch,"delayed acknowledgment confirmed new socket");
        check(deliver(std::move(fresh_ack),false).error==SessionError::none,"fresh acknowledgment");auto old_sample=sample(1);execute();
        // A queued sample that ages out must never enter SRT after backpressure/delay.
        auto expiring=c.make_sample(1,4,now());check(expiring.envelope.has_value(),"expiry fixture");
        const std::array<std::byte,4> stale_payload{};
        check(cq->sensor({Channel::sensor,cs},*expiring.envelope,stale_payload,now())==QueueError::none,"expiry queue");
        std::this_thread::sleep_for(std::chrono::milliseconds(260));
        check(!cq->sensor_front(now())&&cq->stats().sensor_expired==1,"stale queued sample entered SRT");
        apply(true,c.sensor_lost(cs));apply(false,l.sensor_lost(ls));sensor.reset();
        check(deliver(bind(),false).error==SessionError::none,"SENSOR rebind");sample(3);
        control->caller.close();check(wait(control->accepted.fd,SRT_EPOLL_IN)&SRT_EPOLL_ERR,"CONTROL loss not observed");
        const auto old_session=l.session_id();const auto lost=l.control_lost(lg);check(lost.close_sensor&&lost.flush_samples&&l.state()==SessionState::disconnected,"CONTROL loss did not invalidate SENSOR");
        apply(false,lost,old_session);apply(true,c.control_lost(cg),old_session);sensor.reset();control.reset();
        check(cq->control_count()==0&&lq->control_count()==0,"CONTROL invalidation kept queue entries");
        handshake();check(deliver(bind(),false).error==SessionError::none,"full reconnect bind");
        publish(old_sample,false);sample(4);reconcile();
        const auto closing=c.session_id();apply(true,c.stop(),closing);apply(false,l.stop(),closing);const auto start=Clock::now();sensor.reset();control.reset();
        check(Clock::now()-start<std::chrono::seconds(2),"socket shutdown budget");
    }
};
}
int main(int argc,char** argv) {
    try{check(argc==2,"usage: session_socket_tests ipv4|ipv6");const std::string family=argv[1];check(family=="ipv4"||family=="ipv6","family");
        Runtime runtime;Harness test(family=="ipv6");test.run();
        std::cout<<"PASS native session "<<family<<": mutual READY, correlated probes, delayed binding ACK, SENSOR/full reconnect, samples=3, queued sample expired, old session rejected, durable command effect=1, expired-budget QUERY recovered result\n";
    }catch(const std::exception& e){std::cerr<<"FAIL: "<<e.what()<<'\n';return 1;}
}
