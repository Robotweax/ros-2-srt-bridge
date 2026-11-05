#include <robotweax/srt_bridge/errors.hpp>
#include "errors_v1.pb.h"
#include <algorithm>
namespace robotweax::srt_bridge {
namespace {
namespace pb=::robotweax::srt_bridge::v1;
static_assert(unsigned(ControlErrorCode::busy)==pb::CONTROL_BUSY);
static_assert(unsigned(ControlErrorCode::conflict)==pb::CONTROL_CONFLICT);
static_assert(unsigned(ControlErrorCode::not_found)==pb::CONTROL_NOT_FOUND);
static_assert(unsigned(ControlErrorCode::invalid_request)==pb::CONTROL_INVALID_REQUEST);
static_assert(unsigned(ControlErrorCode::clock_unqualified)==pb::CONTROL_CLOCK_UNQUALIFIED);
static_assert(unsigned(ControlErrorCode::start_expired)==pb::CONTROL_START_EXPIRED);
static_assert(unsigned(ControlErrorCode::context_lost)==pb::CONTROL_CONTEXT_LOST);
static_assert(unsigned(ControlErrorCode::capacity)==pb::CONTROL_CAPACITY);
static_assert(unsigned(ControlErrorCode::storage)==pb::CONTROL_STORAGE);
bool varint(std::span<const std::byte> b,std::size_t& at,std::uint64_t& value){
    value=0;for(unsigned n=0;n<10&&at<b.size();++n){const auto c=std::to_integer<unsigned>(b[at++]);if(n==9&&c>1)return false;value|=std::uint64_t(c&127)<<(n*7);
        if(!(c&128))return !n||c!=0;}
    return false;
}
bool preflight(std::span<const std::byte> b){
    if(b.empty()||b.size()>control_error_payload_bytes)return false;
    std::size_t at=0;unsigned seen=0;
    while(at<b.size()){
        std::uint64_t key,value;if(!varint(b,at,key)||key<8||key>32||(key&7))return false;
        const auto field=unsigned(key>>3);if(seen&(1U<<field))return false;seen|=1U<<field;
        if(!varint(b,at,value)||(field!=3&&value>UINT32_MAX))return false;
    }
    return (seen&14)==14;
}
}
bool valid_control_error(const ControlError& error)noexcept{
    if(error.code<ControlErrorCode::busy||error.code>ControlErrorCode::storage||!error.request_sequence||
       (error.request_kind!=Kind::command&&error.request_kind!=Kind::query))return false;
    const bool backoff=error.code==ControlErrorCode::busy||error.code==ControlErrorCode::capacity;
    return backoff?(error.retry_after_ms>=1&&error.retry_after_ms<=5000):error.retry_after_ms==0;
}
std::optional<ControlError> decode_control_error(std::span<const std::byte> bytes){
    if(!preflight(bytes))return {};
    pb::ControlError p;if(!p.ParseFromArray(bytes.data(),bytes.size())||p.code()<1||p.code()>9||p.request_kind()>UINT16_MAX)return {};
    ControlError error{ControlErrorCode(p.code()),Kind(p.request_kind()),p.request_sequence(),p.retry_after_ms()};
    return valid_control_error(error)?std::optional(error):std::nullopt;
}
ErrorEncoding encode_control_error(const ControlError& error,std::span<std::byte> output){
    if(!valid_control_error(error))return {ErrorCodecError::invalid};
    pb::ControlError p;p.set_code(pb::ControlErrorCode(error.code));p.set_request_kind(unsigned(error.request_kind));p.set_request_sequence(error.request_sequence);p.set_retry_after_ms(error.retry_after_ms);
    const auto length=p.ByteSizeLong();if(length>control_error_payload_bytes)return {ErrorCodecError::malformed};
    if(output.size()<length)return {ErrorCodecError::output_too_small};
    std::array<std::byte,control_error_payload_bytes> bytes{};if(!p.SerializeToArray(bytes.data(),length))return {ErrorCodecError::malformed};
    std::copy_n(bytes.begin(),length,output.begin());return {ErrorCodecError::none,length};
}
}
