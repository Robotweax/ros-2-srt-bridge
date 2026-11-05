#include <robotweax/srt_bridge/queues.hpp>
#include <algorithm>
#include <iostream>
#include <deque>
#include <random>
#include <stdexcept>
using namespace robotweax::srt_bridge;
namespace {
unsigned checks=0;void check(bool b,const char* m){++checks;if(!b)throw std::runtime_error(m);}
Identity id(unsigned n){Identity i{};i[0]=static_cast<std::byte>(n);return i;}
RouteManifest manifest(){
    Route a;a.id=1;a.type_name="Imu";a.type_hash="RIHS01_"+std::string(64,'a');
    Route b=a;b.id=2;
    Route c{100,RouteKind::command,Direction::listener_to_caller,QosMapping::request_status,true,4000,5000,0,1,"SetRate","SHA256_"+std::string(64,'b')};
    const std::array routes{a,b,c};return *make_manifest(routes).value;
}
Envelope envelope(Kind kind,std::uint32_t route,std::uint64_t sequence){
    Envelope e;e.kind=kind;e.route_id=route;e.sequence=sequence;e.source_epoch=id(1);e.session_id=id(10);
    if(kind==Kind::command||kind==Kind::status||kind==Kind::query)e.request_id=id(sequence%250+1);
    if(kind==Kind::sample)e.valid_for_ms=250;
    return e;
}
void contract(){
    OutboundQueues q(manifest());check(q.open({Channel::control,1})==QueueError::none&&q.open({Channel::sensor,1})==QueueError::none,"open");
    std::array<std::byte,4000> command{};
    for(unsigned n=0;n<56;++n)check(q.control({Channel::control,1},envelope(Kind::command,100,n+1),command)==QueueError::none,"COMMAND capacity");
    check(q.control_count()==56&&q.control_bytes()==229376,"COMMAND accounting");
    check(q.control({Channel::control,1},envelope(Kind::command,100,57),{})==QueueError::busy,"COMMAND stole reserved slot");
    for(unsigned n=0;n<8;++n)check(q.control({Channel::control,1},envelope(Kind::status,100,n+100),command)==QueueError::none,"status reserve unavailable");
    check(q.control_count()==64&&q.control_bytes()==262144,"total capacity");
    check(q.control({Channel::control,1},envelope(Kind::query,100,200),{})==QueueError::busy,"overfull CONTROL");
    for(unsigned n=0;n<56;++n){check(q.control_front()->envelope.sequence==n+1,"CONTROL reordered");q.control_sent();}
    for(unsigned n=0;n<8;++n){check(q.control_front()->envelope.sequence==n+100,"status reordered");q.control_sent();}
    check(!q.control_front()&&q.control_bytes()==0,"CONTROL drain");
    std::array<std::byte,4> sample{std::byte{1}};auto e=envelope(Kind::sample,1,1);
    check(q.sensor({Channel::sensor,1},e,sample,0)==QueueError::none,"first sample");
    e.sequence=2;sample[0]=std::byte{2};check(q.sensor({Channel::sensor,1},e,sample,0)==QueueError::none,"replace sample");
    e.sequence=1;check(q.sensor({Channel::sensor,1},e,sample,0)==QueueError::out_of_order,"old ingress replaced newest");
    e.route_id=2;e.sequence=1;check(q.sensor({Channel::sensor,1},e,sample,0)==QueueError::none,"second route");
    const auto* front=q.sensor_front(1000000);check(front&&front->envelope.route_id==1&&front->envelope.sequence==2,"latest-only");
    check(front->bytes[96]==std::byte{2}&&sensor_ttl_ms(*front,1000000)==249,"payload ownership / TTL");
    q.sensor_sent(1);check(q.sensor_front(1000000)->envelope.route_id==2,"route fairness");
    check(!q.sensor_front(249000001)&&q.stats().sensor_expired==1,"sub-ms budget sent");
    e=envelope(Kind::sample,1,3);e.source_monotonic_ns=250000000;
    check(q.sensor({Channel::sensor,1},e,sample,250000000)==QueueError::none,"queue before loss");
    std::array<std::byte,512> bytes{};const auto encoded=encode_management(Bind{id(1),id(2),id(3)},bytes);
    check(q.binding({Channel::sensor,1},envelope(Kind::bind,0,1),std::span(bytes).first(encoded.bytes_written))==QueueError::none,"BIND queue");
    SessionAction loss;loss.close_sensor=true;loss.flush_samples=true;
    check(q.apply(loss).count==0&&!q.binding_front()&&!q.sensor_front(250000000),"SENSOR loss flush");
    check(q.open({Channel::sensor,1})==QueueError::obsolete_connection&&q.open({Channel::sensor,2})==QueueError::none,"generation reuse");
    check(q.sensor({Channel::sensor,1},e,sample,0)==QueueError::obsolete_connection,"old socket affected new clock");
    check(q.control({Channel::control,1},envelope(Kind::command,100,1),{})==QueueError::none,"queued command");
    loss.close_control=true;const auto removed=q.apply(loss);check(removed.count==1&&removed.ids[0]==id(2),"unresolved command ID lost");
    check(q.control_count()==0&&q.open({Channel::control,2})==QueueError::none,"CONTROL loss cleanup");
    q.stop();check(q.open({Channel::control,3})==QueueError::stopped,"stop revived queue");
    check(q.stats().sensor_replaced==1&&q.stats().sensor_flushed==1,"drop counters");
}
void rate_gate(){
    OutboundQueues q(manifest());q.open({Channel::control,1});q.open({Channel::sensor,1});
    std::array<std::byte,4> payload{};auto e=envelope(Kind::sample,1,1);
    check(q.sensor({Channel::sensor,1},e,payload,0)==QueueError::none&&q.sensor_front(0),"rate initial burst");
    q.sensor_sent(1);e.sequence=2;e.source_monotonic_ns=1;
    check(q.sensor({Channel::sensor,1},e,payload,1)==QueueError::none&&!q.sensor_front(4999999),"route exceeded 200 Hz");
    check(q.sensor_front(5000000)!=nullptr,"rate boundary delayed");q.sensor_sent(1);
    SessionAction lost;lost.close_sensor=true;q.apply(lost);q.open({Channel::sensor,2});
    e.sequence=3;e.source_monotonic_ns=5000001;
    check(q.sensor({Channel::sensor,2},e,payload,5000001)==QueueError::none&&!q.sensor_front(5000001),"rebind bypassed rate gate");
    check(q.sensor_front(10000000)!=nullptr,"rate gate did not recover");
}
void overload_trace(){
    OutboundQueues q(manifest());q.open({Channel::control,1});q.open({Channel::sensor,1});
    struct Expected{std::uint64_t seq;std::size_t size;bool command;};
    std::deque<Expected> expected;std::size_t bytes=0,commands=0,command_bytes=0;
    std::array<std::byte,4000> payload{};std::mt19937 random(0x51554555);
    for(std::uint64_t n=1;n<=50000;++n){
        if(random()%4==0){
            if(!expected.empty()){
                const auto value=expected.front();check(q.control_front()->envelope.sequence==value.seq,"trace FIFO");
                q.control_sent();bytes-=value.size;if(value.command){--commands;command_bytes-=value.size;}expected.pop_front();
            }
        }else{
            const bool command=random()%3!=0;const auto size=random()%4001;
            const bool room=expected.size()<64&&bytes+96+size<=262144&&(!command||(commands<56&&command_bytes+96+size<=229376));
            const auto result=q.control({Channel::control,1},envelope(command?Kind::command:Kind::status,100,n),std::span(payload).first(size));
            check((result==QueueError::none)==room,"trace admission did not match capacity");
            if(room){expected.push_back({n,size+96,command});bytes+=size+96;if(command){++commands;command_bytes+=size+96;}}
        }
        check(q.control_count()==expected.size()&&q.control_bytes()==bytes,"trace accounting");
        auto e=envelope(Kind::sample,1,n);e.source_monotonic_ns=n*1000000;
        check(q.sensor({Channel::sensor,1},e,std::span(payload).first(4),e.source_monotonic_ns)==QueueError::none,"overload latest ingress");
        check(q.sensor_front(e.source_monotonic_ns)->envelope.sequence==n,"overload kept old sample");
    }
    check(q.stats().sensor_replaced==49999,"overload storage grew instead of replacing");
    q.stop();check(!q.control_front()&&!q.sensor_front(50000000000ULL),"trace stop left packets");
}

}
int main(){try{contract();rate_gate();overload_trace();std::cout<<"PASS queues contract: "<<checks<<" checks, fixed storage="<<sizeof(OutboundQueues)<<" bytes\n";}
catch(const std::exception& e){std::cerr<<"FAIL: "<<e.what()<<'\n';return 1;}}
