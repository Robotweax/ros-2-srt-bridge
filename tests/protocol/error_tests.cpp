#include <robotweax/srt_bridge/errors.hpp>
#include <robotweax/srt_bridge/session.hpp>
#include <robotweax/srt_bridge/commands.hpp>
#include <algorithm>
#include <iostream>
#include <random>
#include <vector>
using namespace robotweax::srt_bridge;
namespace {
unsigned checks=0;
void check(bool ok,const char* text){++checks;if(!ok)throw std::runtime_error(text);}
Identity id(unsigned n){Identity value{};value[0]=std::byte(n);return value;}
void codec(){
    check(rate_command_schema_hash()=="SHA256_5c6bd6e9a81dcc45aca4e17697441eceb280a454bfe72c784b2fcfca840cca98","ERROR changed existing command schema identity");
    ControlError error{ControlErrorCode::not_found,Kind::query,9,0};std::array<std::byte,64> bytes{};
    const std::array<std::byte,6> golden{std::byte{8},std::byte{3},std::byte{16},std::byte{8},std::byte{24},std::byte{9}};
    auto encoded=encode_control_error(error,bytes);check(encoded&&encoded.bytes_written==golden.size()&&std::equal(golden.begin(),golden.end(),bytes.begin()),"independent ERROR golden");
    check(decode_control_error(golden)==error,"ERROR decode golden");
    for(unsigned code=1;code<=9;++code){error={ControlErrorCode(code),Kind::command,UINT64_MAX,(code==1||code==8)?5000U:0U};encoded=encode_control_error(error,bytes);check(encoded&&decode_control_error(std::span(bytes).first(encoded.bytes_written))==error,"ERROR code/max sequence roundtrip");}
    for(std::size_t size=0;size<golden.size();++size)check(!decode_control_error(std::span(golden).first(size)),"truncated ERROR admitted");
    const std::vector<std::vector<unsigned>> bad{{8,0,16,8,24,9},{8,3,16,11,24,9},{8,3,16,8,24,0},{8,3,16,8,24,9,40,1},{8,3,16,8,24,9,8,3},{8,3,16,8,24,0x89,0},{8,1,16,6,24,1},{8,2,16,6,24,1,32,1},{8,3,16,0x86,0x80,4,24,9},{8,0x83,2,16,8,24,9},{8,3,16,8,24,255,255,255,255,255,255,255,255,255,2}};
    for(const auto& values:bad){std::vector<std::byte> data;for(auto value:values)data.push_back(std::byte(value));check(!decode_control_error(data),"invalid ERROR accepted");}
    std::array<std::byte,65> large{};check(!decode_control_error(large),"oversized ERROR admitted");
    bytes.fill(std::byte{0xa5});error.request_sequence=0;check(!encode_control_error(error,bytes)&&std::all_of(bytes.begin(),bytes.end(),[](auto v){return v==std::byte{0xa5};}),"failed encode mutated output");
    error={ControlErrorCode::not_found,Kind::query,9,0};check(!encode_control_error(error,std::span(bytes).first(3))&&bytes[0]==std::byte{0xa5},"short output mutated");
    std::mt19937 random(0x45525231);
    for(unsigned n=0;n<20000;++n){std::vector<std::byte> data(golden.begin(),golden.end());if(n%3==0){data.resize(random()%81);for(auto& b:data)b=std::byte(random());}else data[random()%data.size()]=std::byte(random());
        const auto decoded=decode_control_error(data);if(decoded){check(valid_control_error(*decoded),"mutation bypassed ERROR semantics");const auto result=encode_control_error(*decoded,bytes);check(result&&decode_control_error(std::span(bytes).first(result.bytes_written))==decoded,"ERROR mutation roundtrip");}++checks;}
}
SessionConfig config(Role role){Route command{100,RouteKind::command,Direction::listener_to_caller,QosMapping::request_status,true,4000,5000,0,1,"robotweax.srt_bridge.v1.SetMeasurementRateCommand",rate_command_schema_hash()};return {role,role==Role::caller?"robot":"operator",role==Role::caller?"operator":"robot",id(role==Role::caller?1:2),role==Role::caller?1U:2U,*make_manifest(std::span(&command,1)).value,{0,0,5000000000ULL,50000000}};}
void session(){Session caller(config(Role::caller)),listener(config(Role::listener));std::uint64_t now=1000000000;const auto next=[&]{return now+=10000;};
    const auto deliver=[&](Session& peer,SessionAction action,std::uint64_t generation){check(action.send.has_value(),"missing management");std::array<std::byte,512> bytes{};const auto result=encode_management(action.send->payload,bytes);check(bool(result),"management encode");return peer.receive({Channel::control,generation},{action.send->envelope,std::span(bytes).first(result.bytes_written)},next());};
    listener.control_connected(10,{Channel::control,true,true,true},next(),id(3));auto welcome=deliver(listener,caller.control_connected(1,{Channel::control,true,true,true},next()),10);deliver(caller,std::move(welcome),1);
    auto reply=deliver(listener,caller.begin_probe(next()),10);auto ready=deliver(caller,std::move(reply),1);deliver(listener,std::move(ready),10);
    reply=deliver(caller,listener.begin_probe(next()),1);ready=deliver(listener,std::move(reply),10);deliver(caller,std::move(ready),1);
    ControlError error{ControlErrorCode::not_found,Kind::query,1,0};std::array<std::byte,64> bytes{};const auto encoded=encode_control_error(error,bytes);const auto body=std::span(bytes).first(encoded.bytes_written);
    check(listener.make_control(Kind::error,100,id(4),body.size(),0,next()).action.error==SessionError::wrong_direction,"operator sent ERROR");
    auto made=caller.make_control(Kind::error,100,id(4),body.size(),0,next());check(made.envelope.has_value(),"caller ERROR not admitted");auto e=*made.envelope;
    check(listener.admit_control({Channel::control,10},{e,body},next()).envelope.has_value(),"valid ERROR rejected");
    check(listener.admit_control({Channel::control,10},{e,body},next()).action.error==SessionError::replay,"ERROR replay admitted");
    ++e.sequence;auto changed=e;changed.session_id=id(9);check(listener.admit_control({Channel::control,10},{changed,body},next()).action.error==SessionError::stale_session,"old-session ERROR admitted");
    changed=e;changed.source_epoch=id(9);check(listener.admit_control({Channel::control,10},{changed,body},next()).action.error==SessionError::epoch_mismatch,"wrong-epoch ERROR admitted");
    changed=e;++changed.clock_domain;check(listener.admit_control({Channel::control,10},{changed,body},next()).action.error==SessionError::domain_mismatch,"wrong-domain ERROR admitted");
    check(listener.admit_control({Channel::control,11},{e,body},next()).action.error==SessionError::obsolete_connection,"old-generation ERROR admitted");
    changed=e;changed.valid_for_ms=1;check(listener.admit_control({Channel::control,10},{changed,body},next()).action.error==SessionError::malformed,"ERROR carried execution TTL");
    check(caller.admit_control({Channel::control,1},{e,body},next()).action.error==SessionError::wrong_direction,"robot received ERROR");
    auto invalid=bytes;invalid[encoded.bytes_written-1]=std::byte{};check(listener.admit_control({Channel::control,10},{e,std::span(invalid).first(encoded.bytes_written)},next()).action.error==SessionError::malformed,"invalid ERROR body admitted");
    now+=5000000001ULL;caller.tick(next());listener.tick(next());made=caller.make_control(Kind::error,100,id(4),body.size(),0,next());check(made.envelope.has_value()&&listener.admit_control({Channel::control,10},{*made.envelope,body},next()).envelope.has_value(),"diagnostic wrongly requires fresh execution clock");
}
}
int main(){try{codec();session();std::cout<<"PASS error contract: "<<checks<<" checks\n";return 0;}catch(const std::exception& e){std::cerr<<"FAIL: "<<e.what()<<'\n';return 1;}}
