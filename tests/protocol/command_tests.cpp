#include <robotweax/srt_bridge/commands.hpp>
#include <array>
#include <iostream>
#include <fstream>
#include <random>
#include <vector>
#include <stdexcept>
using namespace robotweax::srt_bridge;
namespace {unsigned checks=0;void check(bool v,const char* m){++checks;if(!v)throw std::runtime_error(m);}}
int main(){try{
    RateCommand command{100,5000,0,1};std::array<std::byte,256> buffer{};
    auto encoded=encode_rate_command(command,buffer);check(bool(encoded),"command encode");check(decode_rate_command(std::span(buffer).first(encoded.bytes_written))==command,"command roundtrip");
    const std::array<std::byte,7> golden{std::byte{8},std::byte{100},std::byte{24},std::byte{1},std::byte{32},std::byte{0x88},std::byte{0x27}};
    check(encoded.bytes_written==golden.size()&&std::equal(golden.begin(),golden.end(),buffer.begin()),"independent protobuf golden");
    std::ifstream hashfile(std::string(GOLDEN_DIRECTORY)+"/set-rate-v1.sha256");std::vector<std::byte> hash;std::string token;
    while(hashfile>>token)hash.push_back(static_cast<std::byte>(std::stoul(token,nullptr,16)));
    const auto digest=command_hash(100,command);check(hash.size()==32&&std::equal(hash.begin(),hash.end(),digest.begin()),"independent command hash golden");
    auto changed=command;changed.new_generation=0;check(!encode_rate_command(changed,buffer),"generation wrap/mismatch");
    CommandStatus status{CommandState::succeeded,CommandReason::none,command,command_hash(100,command),{100,1,true},3};
    encoded=encode_command_status(100,status,buffer);check(bool(encoded)&&decode_command_status(100,std::span(buffer).first(encoded.bytes_written))==status,"status roundtrip");
    check(!decode_command_status(101,std::span(buffer).first(encoded.bytes_written)),"status route/hash mismatch");
    status.result.valid=false;check(!encode_command_status(100,status,buffer),"unproved success");
    const std::array<std::byte,4> duplicate{std::byte{8},std::byte{1},std::byte{8},std::byte{2}};
    check(!decode_rate_command(duplicate),"duplicate scalar fields");
    std::array<std::byte,257> oversize{};check(!decode_rate_command(oversize),"oversize protobuf");
    check(valid_query({})&&!valid_query(duplicate),"query payload");
    std::mt19937 random(0x434d4431);
    for(unsigned n=0;n<10000;++n){
        std::vector<std::byte> b(golden.begin(),golden.end());
        if(n%3==0)b.resize(random()%270);else b[random()%b.size()]=static_cast<std::byte>(random()&255);
        const auto decoded=decode_rate_command(b);
        if(decoded){check(decoded->rate_hz>=1&&decoded->rate_hz<=1000&&decoded->budget_ms>=1&&decoded->budget_ms<=60000&&decoded->new_generation==decoded->expected_generation+1,"accepted command violates contract");
            const auto serialized=encode_rate_command(*decoded,buffer);check(serialized&&decode_rate_command(std::span(buffer).first(serialized.bytes_written))==decoded,"mutation roundtrip");}
    }
    std::cout<<"PASS command contract: "<<checks<<" checks\n";
}catch(const std::exception& e){std::cerr<<"FAIL: "<<e.what()<<'\n';return 1;}}
