#pragma once
#include <array>
#include <cstddef>
#include <cstdint>
#include <span>

namespace robotweax::srt_bridge {
inline constexpr std::size_t envelope_bytes = 96;
inline constexpr std::size_t sensor_message_bytes = 1024;
inline constexpr std::size_t control_message_bytes = 4096;
using Identity = std::array<std::byte, 16>;
using Digest = std::array<std::byte, 32>;
// Numeric values are frozen in proto/management_v1.proto.
enum class Kind : std::uint16_t {
    hello = 1, welcome, ready, bind, sample, command, status, query,
    time_probe, time_reply, error
};
enum class Channel { control, sensor };
enum class WireError {
    none, truncated, oversize, bad_magic, bad_version, bad_kind, bad_flags,
    bad_reserved, bad_length, wrong_channel, bad_route, bad_request_id, output_too_small
};
struct Envelope {
    Kind kind = Kind::sample;
    std::uint32_t route_id = 0;
    Identity session_id{};
    Identity source_epoch{};
    std::uint64_t sequence = 0;
    std::uint64_t source_monotonic_ns = 0;
    std::uint32_t clock_domain = 0;
    std::uint32_t valid_for_ms = 0;
    Identity request_id{};
    bool operator==(const Envelope&) const = default;
};
struct MessageView {
    Envelope envelope{};
    // Borrows the input buffer; does not outlive it. Never allocates peer-sized data.
    std::span<const std::byte> payload{};
};
struct DecodeResult {
    WireError error = WireError::none;
    MessageView message{};
    explicit operator bool() const { return error == WireError::none; }
};
struct EncodeResult {
    WireError error = WireError::none;
    std::size_t bytes_written = 0;
    explicit operator bool() const { return error == WireError::none; }
};
// Non-management routes must appear in the local allowlist. Session, epoch,
// freshness, type hashes and protobuf payloads are validated by the next layers.
DecodeResult decode(std::span<const std::byte> bytes, Channel channel,
                    std::span<const std::uint32_t> allowed_routes) noexcept;
// On failure the output is unchanged. The caller owns a bounded destination.
EncodeResult encode(const Envelope& envelope, std::span<const std::byte> payload,
                    Channel channel, std::span<const std::uint32_t> allowed_routes,
                    std::span<std::byte> output) noexcept;
}
