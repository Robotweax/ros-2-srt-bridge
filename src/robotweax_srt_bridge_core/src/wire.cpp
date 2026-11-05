#include <robotweax/srt_bridge/wire.hpp>
#include <algorithm>
#include <cstring>

namespace robotweax::srt_bridge {
namespace {
constexpr std::array<std::byte, 4> magic{std::byte{'R'}, std::byte{'W'}, std::byte{'S'}, std::byte{'B'}};
bool zero(const Identity& id) { return std::all_of(id.begin(), id.end(), [](auto b) { return b == std::byte{}; }); }
std::size_t limit(Channel channel) { return channel == Channel::sensor ? sensor_message_bytes : control_message_bytes; }
std::uint64_t read(std::span<const std::byte> bytes, std::size_t offset, std::size_t length) {
    std::uint64_t result = 0;
    for (std::size_t i = 0; i < length; ++i) result = (result << 8) | std::to_integer<unsigned>(bytes[offset + i]);
    return result;
}
void write(std::span<std::byte> bytes, std::size_t offset, std::size_t length, std::uint64_t value) {
    for (std::size_t i = length; i > 0; --i) {
        bytes[offset + i - 1] = static_cast<std::byte>(value & 255);
        value >>= 8;
    }
}
Identity identity(std::span<const std::byte> bytes, std::size_t offset) {
    Identity result;
    std::copy_n(bytes.begin() + offset, result.size(), result.begin());
    return result;
}
WireError validate(const Envelope& e, std::size_t payload_size, Channel channel,
                   std::span<const std::uint32_t> allowed_routes) {
    if (payload_size > limit(channel) - envelope_bytes) return WireError::oversize;
    const auto kind = static_cast<std::uint16_t>(e.kind);
    if (kind < 1 || kind > 11) return WireError::bad_kind;
    const bool sensor_kind = e.kind == Kind::sample || e.kind == Kind::bind;
    if (sensor_kind != (channel == Channel::sensor)) return WireError::wrong_channel;
    const bool application_kind = e.kind == Kind::sample || e.kind == Kind::command ||
        e.kind == Kind::status || e.kind == Kind::query || e.kind == Kind::error;
    if ((application_kind && e.route_id == 0) ||
        (!application_kind && e.route_id != 0)) return WireError::bad_route;
    if (e.route_id != 0 && std::find(allowed_routes.begin(), allowed_routes.end(), e.route_id) == allowed_routes.end())
        return WireError::bad_route;
    if ((channel == Channel::sensor && !zero(e.request_id)) ||
        ((e.kind == Kind::command || e.kind == Kind::status || e.kind == Kind::query || e.kind == Kind::error) && zero(e.request_id)))
        return WireError::bad_request_id;
    return WireError::none;
}
}
DecodeResult decode(std::span<const std::byte> bytes, Channel channel,
                    std::span<const std::uint32_t> allowed_routes) noexcept {
    auto failure = [](WireError error) { return DecodeResult{error, {}}; };
    if (bytes.size() < envelope_bytes) return failure(WireError::truncated);
    if (bytes.size() > limit(channel)) return failure(WireError::oversize);
    if (!std::equal(magic.begin(), magic.end(), bytes.begin())) return failure(WireError::bad_magic);
    if (read(bytes, 4, 2) != 1) return failure(WireError::bad_version);
    if (read(bytes, 8, 4) != 0) return failure(WireError::bad_flags);
    if (read(bytes, 76, 4) != 0) return failure(WireError::bad_reserved);
    if (read(bytes, 72, 4) != bytes.size() - envelope_bytes) return failure(WireError::bad_length);
    Envelope envelope;
    envelope.kind = static_cast<Kind>(read(bytes, 6, 2));
    envelope.route_id = static_cast<std::uint32_t>(read(bytes, 12, 4));
    envelope.session_id = identity(bytes, 16);
    envelope.source_epoch = identity(bytes, 32);
    envelope.sequence = read(bytes, 48, 8);
    envelope.source_monotonic_ns = read(bytes, 56, 8);
    envelope.clock_domain = static_cast<std::uint32_t>(read(bytes, 64, 4));
    envelope.valid_for_ms = static_cast<std::uint32_t>(read(bytes, 68, 4));
    envelope.request_id = identity(bytes, 80);
    const auto error = validate(envelope, bytes.size() - envelope_bytes, channel, allowed_routes);
    if (error != WireError::none) return failure(error);
    return {WireError::none, {envelope, bytes.subspan(envelope_bytes)}};
}
EncodeResult encode(const Envelope& envelope, std::span<const std::byte> payload,
                    Channel channel, std::span<const std::uint32_t> allowed_routes,
                    std::span<std::byte> output) noexcept {
    const auto error = validate(envelope, payload.size(), channel, allowed_routes);
    if (error != WireError::none) return {error, 0};
    const auto size = envelope_bytes + payload.size();
    if (output.size() < size) return {WireError::output_too_small, 0};
    // Move payload first so in-place encoding is safe when payload overlaps output.
    if (!payload.empty()) std::memmove(output.data() + envelope_bytes, payload.data(), payload.size());
    std::fill_n(output.begin(), envelope_bytes, std::byte{});
    std::copy(magic.begin(), magic.end(), output.begin());
    write(output, 4, 2, 1);
    write(output, 6, 2, static_cast<std::uint16_t>(envelope.kind));
    write(output, 12, 4, envelope.route_id);
    std::copy(envelope.session_id.begin(), envelope.session_id.end(), output.begin() + 16);
    std::copy(envelope.source_epoch.begin(), envelope.source_epoch.end(), output.begin() + 32);
    write(output, 48, 8, envelope.sequence);
    write(output, 56, 8, envelope.source_monotonic_ns);
    write(output, 64, 4, envelope.clock_domain);
    write(output, 68, 4, envelope.valid_for_ms);
    write(output, 72, 4, payload.size());
    std::copy(envelope.request_id.begin(), envelope.request_id.end(), output.begin() + 80);
    return {WireError::none, size};
}
}
