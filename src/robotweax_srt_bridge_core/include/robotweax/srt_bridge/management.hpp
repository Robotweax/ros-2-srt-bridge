#pragma once
#include <robotweax/srt_bridge/wire.hpp>
#include <array>
#include <string>
#include <variant>

namespace robotweax::srt_bridge {
inline constexpr std::size_t management_payload_bytes = 512;
struct Limits {
    std::uint32_t sensor_bytes = 1024, control_bytes = 4096, routes = 8;
    bool operator==(const Limits&) const = default;
};
struct Hello {
    std::string peer_id;
    Digest routes_sha256{};
    Limits limits{};
    bool operator==(const Hello&) const = default;
};
struct Welcome {
    Hello parameters;
    Identity caller_epoch{}, listener_epoch{};
    bool operator==(const Welcome&) const = default;
};
enum class ReadyPhase { control_ready = 1, sensor_bound = 2 };
struct Ready {
    ReadyPhase phase = ReadyPhase::control_ready;
    Digest routes_sha256{};
    Identity sensor_binding_id{};
    bool operator==(const Ready&) const = default;
};
struct Bind {
    Identity caller_epoch{}, listener_epoch{}, sensor_binding_id{};
    bool operator==(const Bind&) const = default;
};
struct TimeProbe {
    std::uint64_t initiator_send_ns = 0;
    bool operator==(const TimeProbe&) const = default;
};
struct TimeReply {
    std::uint64_t initiator_send_ns = 0, responder_receive_ns = 0, responder_send_ns = 0;
    bool operator==(const TimeReply&) const = default;
};
using Management = std::variant<Hello, Welcome, Ready, Bind, TimeProbe, TimeReply>;
enum class ManagementError {
    none, unsupported_kind, oversize, malformed, unknown_field, duplicate_field,
    field_size, invalid_utf8, invalid_peer_id, invalid_limits, invalid_identity,
    invalid_phase, invalid_time, output_too_small
};
struct ManagementResult {
    ManagementError error = ManagementError::none;
    Management value{};
    explicit operator bool() const { return error == ManagementError::none; }
};
struct ManagementEncodeResult {
    ManagementError error = ManagementError::none;
    std::size_t bytes_written = 0;
    explicit operator bool() const { return error == ManagementError::none; }
};
Kind kind_of(const Management&) noexcept;
// Preflight validates field sizes, wire types, duplicates and UTF-8 before the
// generated Protobuf parser can allocate. Unknown v1 fields fail closed.
ManagementResult decode_management(Kind kind, std::span<const std::byte> payload);
ManagementEncodeResult encode_management(const Management& message, std::span<std::byte> output);
}
