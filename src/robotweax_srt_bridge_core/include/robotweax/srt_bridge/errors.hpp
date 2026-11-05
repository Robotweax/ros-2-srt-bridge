#pragma once
#include <robotweax/srt_bridge/wire.hpp>
#include <optional>
namespace robotweax::srt_bridge {
enum class ControlErrorCode : std::uint8_t {
    busy=1,conflict,not_found,invalid_request,clock_unqualified,start_expired,context_lost,capacity,storage
};
struct ControlError {
    ControlErrorCode code=ControlErrorCode::invalid_request;
    Kind request_kind=Kind::query;
    std::uint64_t request_sequence=0;
    std::uint32_t retry_after_ms=0;
    bool operator==(const ControlError&)const=default;
};
inline constexpr std::size_t control_error_payload_bytes=64;
enum class ErrorCodecError { none,invalid,malformed,output_too_small };
struct ErrorEncoding {
    ErrorCodecError error=ErrorCodecError::none;
    std::size_t bytes_written=0;
    explicit operator bool()const noexcept{return error==ErrorCodecError::none;}
};
// ERROR is a current-session diagnostic, never CommandStatus or a journal result.
bool valid_control_error(const ControlError&)noexcept;
std::optional<ControlError> decode_control_error(std::span<const std::byte> bytes);
ErrorEncoding encode_control_error(const ControlError&,std::span<std::byte> output);
}
