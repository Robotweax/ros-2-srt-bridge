#include <robotweax/srt_bridge/commands.hpp>
#include "commands_v1.pb.h"
#include <google/protobuf/descriptor.pb.h>
#include <openssl/evp.h>
#include <algorithm>
#include <array>
#include <cstring>
#include <limits>
#include <stdexcept>

namespace robotweax::srt_bridge {
namespace {
constexpr std::uint64_t maximum=std::numeric_limits<std::int64_t>::max();
namespace pb=::robotweax::srt_bridge::v1;
static_assert(static_cast<int>(CommandState::local_queued)==pb::CMD_LOCAL_QUEUED);
static_assert(static_cast<int>(CommandState::accepted)==pb::CMD_ACCEPTED);
static_assert(static_cast<int>(CommandState::dispatching)==pb::CMD_DISPATCHING);
static_assert(static_cast<int>(CommandState::succeeded)==pb::CMD_SUCCEEDED);
static_assert(static_cast<int>(CommandState::failed)==pb::CMD_FAILED);
static_assert(static_cast<int>(CommandState::rejected)==pb::CMD_REJECTED);
static_assert(static_cast<int>(CommandState::expired)==pb::CMD_EXPIRED);
static_assert(static_cast<int>(CommandState::unknown)==pb::CMD_UNKNOWN);
static_assert(static_cast<int>(CommandReason::none)==pb::CMD_REASON_NONE);
static_assert(static_cast<int>(CommandReason::context_lost)==pb::CMD_CONTEXT_LOST);
static_assert(static_cast<int>(CommandReason::reconcile_required)==pb::CMD_RECONCILE_REQUIRED);
static_assert(static_cast<int>(CommandReason::start_deadline)==pb::CMD_START_DEADLINE);
static_assert(static_cast<int>(CommandReason::generation_conflict)==pb::CMD_GENERATION_CONFLICT);
static_assert(static_cast<int>(CommandReason::handler_failed)==pb::CMD_HANDLER_FAILED);
static_assert(static_cast<int>(CommandReason::effect_uncertain)==pb::CMD_EFFECT_UNCERTAIN);
bool varint(std::span<const std::byte> b,std::size_t& pos,std::uint64_t& v){
    v=0;for(unsigned i=0;i<10&&pos<b.size();++i){const auto c=std::to_integer<unsigned>(b[pos++]);if(i==9&&c>1)return false;v|=static_cast<std::uint64_t>(c&127)<<(i*7);if(!(c&128))return true;}return false;
}
bool preflight(std::span<const std::byte> b,bool status){
    if(b.size()>256)return false;
    std::size_t pos=0;unsigned seen=0;
    while(pos<b.size()){
        std::uint64_t key,value;if(!varint(b,pos,key)||!key||key>0xffffffffULL)return false;
        const auto field=static_cast<unsigned>(key>>3),type=static_cast<unsigned>(key&7);
        if(!field||field>(status?11U:4U)||(seen&(1U<<field)))return false;
        seen|=1U<<field;
        if(status&&field==3){if(type!=2||!varint(b,pos,value)||value!=32||value>b.size()-pos)return false;pos+=32;}
        else{if(type!=0||!varint(b,pos,value))return false;
            const bool wide=status?(field==4||field==6||field==7||field==11):(field==2||field==3);
            if(value>(wide?maximum:0xffffffffULL)||(status&&field==9&&value>1))return false;
        }
    }
    return !status||(seen&(1U<<3));
}
template<class P> CommandEncoding serialize(const P& p,std::span<std::byte> output){
    const auto n=p.ByteSizeLong();if(n>256)return {CommandCodecError::oversize};if(n>output.size())return {CommandCodecError::output_too_small};
    std::array<std::byte,256> b{};if(!p.SerializeToArray(b.data(),n))return {CommandCodecError::malformed};
    std::copy_n(b.begin(),n,output.begin());return {CommandCodecError::none,n};
}
}
bool valid_command(const RateCommand& c) noexcept{return c.rate_hz>=1&&c.rate_hz<=1000&&c.budget_ms>=1&&c.budget_ms<=60000&&c.expected_generation<maximum&&c.new_generation==c.expected_generation+1;}
std::string rate_command_schema_hash(){
    google::protobuf::FileDescriptorProto schema;pb::SetMeasurementRateCommand::descriptor()->file()->CopyTo(&schema);
    const auto encoded=schema.SerializeAsString();Digest digest{};unsigned n=digest.size();
    if(EVP_Digest(encoded.data(),encoded.size(),reinterpret_cast<unsigned char*>(digest.data()),&n,EVP_sha256(),nullptr)!=1||n!=digest.size())throw std::runtime_error("command schema hash failed");
    std::string value="SHA256_";constexpr char hex[]="0123456789abcdef";
    for(auto b:digest){const auto v=std::to_integer<unsigned>(b);value+=hex[v>>4];value+=hex[v&15];}return value;
}
Digest command_hash(std::uint32_t route,const RateCommand& c){
    if(!route||!valid_command(c))throw std::invalid_argument("invalid rate command");
    std::array<std::byte,32> bytes{};std::size_t at=0;
    const auto put=[&](std::uint64_t value,unsigned n){for(unsigned i=n;i>0;--i)bytes[at++]=static_cast<std::byte>((value>>((i-1)*8))&255);};
    put(0x52574331,4);put(route,4);put(c.rate_hz,4);put(c.budget_ms,4);put(c.expected_generation,8);put(c.new_generation,8);
    Digest hash{};unsigned n=hash.size();if(EVP_Digest(bytes.data(),bytes.size(),reinterpret_cast<unsigned char*>(hash.data()),&n,EVP_sha256(),nullptr)!=1||n!=hash.size())throw std::runtime_error("command hash failed");return hash;
}
bool valid_remote_status(std::uint32_t route,const CommandStatus& s){
    if(!route||!valid_command(s.command)||s.payload_hash!=command_hash(route,s.command)||s.state<CommandState::accepted||s.state>CommandState::unknown||s.reason>CommandReason::effect_uncertain)return false;
    if(s.state==CommandState::succeeded)return s.revision==3&&s.reason==CommandReason::none&&s.result.valid&&s.result.rate_hz==s.command.rate_hz&&s.result.generation==s.command.new_generation;
    if(s.result.valid||s.result.rate_hz||s.result.generation)return false;
    switch(s.state){
    case CommandState::accepted:return s.revision==1&&s.reason==CommandReason::none;
    case CommandState::dispatching:return s.revision==2&&s.reason==CommandReason::none;
    case CommandState::failed:return s.revision==3&&(s.reason==CommandReason::handler_failed||s.reason==CommandReason::generation_conflict);
    case CommandState::rejected:return (s.revision==2||s.revision==3)&&(s.reason==CommandReason::context_lost||s.reason==CommandReason::generation_conflict);
    case CommandState::expired:return s.revision>=1&&s.revision<=3&&s.reason==CommandReason::start_deadline;
    case CommandState::unknown:return s.revision==3&&(s.reason==CommandReason::context_lost||s.reason==CommandReason::effect_uncertain);
    default:return false;
    }
}
std::optional<RateCommand> decode_rate_command(std::span<const std::byte> bytes){
    if(!preflight(bytes,false))return {};
    pb::SetMeasurementRateCommand p;if(!p.ParseFromArray(bytes.data(),bytes.size()))return {};
    RateCommand c{p.rate_hz(),p.budget_ms(),p.expected_generation(),p.new_generation()};return valid_command(c)?std::optional(c):std::nullopt;
}
std::optional<CommandStatus> decode_command_status(std::uint32_t route,std::span<const std::byte> bytes){
    if(!preflight(bytes,true))return {};
    pb::CommandStatus p;if(!p.ParseFromArray(bytes.data(),bytes.size()))return {};
    CommandStatus s;s.state=static_cast<CommandState>(p.state());s.reason=static_cast<CommandReason>(p.reason());
    if(p.state()<2||p.state()>8||p.reason()<0||p.reason()>6)return {};
    s.command={p.rate_hz(),p.budget_ms(),p.expected_generation(),p.new_generation()};std::memcpy(s.payload_hash.data(),p.payload_hash().data(),32);
    s.revision=p.revision();s.result={p.result_rate_hz(),p.result_generation(),p.result_valid()};return valid_remote_status(route,s)?std::optional(s):std::nullopt;
}
CommandEncoding encode_rate_command(const RateCommand& c,std::span<std::byte> output){
    if(!valid_command(c))return {CommandCodecError::invalid};
    pb::SetMeasurementRateCommand p;
    p.set_rate_hz(c.rate_hz);p.set_budget_ms(c.budget_ms);p.set_expected_generation(c.expected_generation);p.set_new_generation(c.new_generation);return serialize(p,output);
}
CommandEncoding encode_command_status(std::uint32_t route,const CommandStatus& s,std::span<std::byte> output){
    if(!valid_remote_status(route,s))return {CommandCodecError::invalid};
    pb::CommandStatus p;
    p.set_state(static_cast<pb::CommandStateCode>(s.state));p.set_reason(static_cast<pb::CommandReasonCode>(s.reason));p.set_payload_hash(reinterpret_cast<const char*>(s.payload_hash.data()),s.payload_hash.size());p.set_revision(s.revision);
    p.set_rate_hz(s.command.rate_hz);p.set_budget_ms(s.command.budget_ms);p.set_expected_generation(s.command.expected_generation);p.set_new_generation(s.command.new_generation);
    p.set_result_valid(s.result.valid);p.set_result_rate_hz(s.result.rate_hz);p.set_result_generation(s.result.generation);return serialize(p,output);
}
bool valid_query(std::span<const std::byte> bytes) noexcept{return bytes.empty();}
}
