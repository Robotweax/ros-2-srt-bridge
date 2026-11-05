#include <robotweax/srt_bridge/management.hpp>
#include "management_v1.pb.h"
#include <algorithm>
#include <cstring>
#include <limits>
#include <type_traits>

namespace robotweax::srt_bridge {
namespace {
namespace pb = ::robotweax::srt_bridge::v1;
using Error = ManagementError;
bool zero(const Identity& id) {
    return std::all_of(id.begin(), id.end(), [](auto b) { return b == std::byte{}; });
}
// Strict RFC 3629: reject overlong forms, surrogates, controls and embedded NUL.
bool peer_utf8(std::string_view text) {
    std::size_t i = 0;
    while (i < text.size()) {
        const auto first = static_cast<unsigned char>(text[i++]);
        if (first < 0x80) { if (first < 0x20 || first == 0x7f) return false; continue; }
        unsigned count, value, minimum;
        if (first >= 0xc2 && first <= 0xdf) { count = 1; value = first & 31; minimum = 0x80; }
        else if (first >= 0xe0 && first <= 0xef) { count = 2; value = first & 15; minimum = 0x800; }
        else if (first >= 0xf0 && first <= 0xf4) { count = 3; value = first & 7; minimum = 0x10000; }
        else return false;
        if (text.size() - i < count) return false;
        for (unsigned j = 0; j < count; ++j) {
            const auto b = static_cast<unsigned char>(text[i++]);
            if ((b & 0xc0) != 0x80) return false;
            value = (value << 6) | (b & 63);
        }
        if (value < minimum || value > 0x10ffff || (value >= 0xd800 && value <= 0xdfff) ||
            (value >= 0x80 && value <= 0x9f)) return false;
    }
    return true;
}
Error valid(const Hello& h) {
    if (h.peer_id.empty() || h.peer_id.size() > 64) return Error::invalid_peer_id;
    if (!peer_utf8(h.peer_id)) return Error::invalid_utf8;
    if (h.limits.sensor_bytes != 1024 || h.limits.control_bytes != 4096 ||
        h.limits.routes == 0 || h.limits.routes > 8) return Error::invalid_limits;
    return Error::none;
}
Error valid(const Welcome& w) {
    if (const auto error = valid(w.parameters); error != Error::none) return error;
    if (zero(w.caller_epoch) || zero(w.listener_epoch) || w.caller_epoch == w.listener_epoch) return Error::invalid_identity;
    return Error::none;
}
Error valid(const Ready& r) {
    if (r.phase != ReadyPhase::control_ready && r.phase != ReadyPhase::sensor_bound) return Error::invalid_phase;
    return (r.phase == ReadyPhase::control_ready) == zero(r.sensor_binding_id) ? Error::none : Error::invalid_identity;
}
Error valid(const Bind& b) {
    return zero(b.caller_epoch) || zero(b.listener_epoch) || zero(b.sensor_binding_id) || b.caller_epoch == b.listener_epoch ? Error::invalid_identity : Error::none;
}
Error valid(const TimeProbe& t) {
    return t.initiator_send_ns > static_cast<std::uint64_t>(std::numeric_limits<std::int64_t>::max()) ? Error::invalid_time : Error::none;
}
Error valid(const TimeReply& t) {
    if (valid(TimeProbe{t.initiator_send_ns}) != Error::none ||
        valid(TimeProbe{t.responder_receive_ns}) != Error::none || valid(TimeProbe{t.responder_send_ns}) != Error::none ||
        t.responder_send_ns < t.responder_receive_ns) return Error::invalid_time;
    return Error::none;
}
bool varint(std::span<const std::byte> bytes, std::size_t& pos, std::uint64_t& value) {
    value = 0;
    for (unsigned i = 0; i < 10 && pos < bytes.size(); ++i) {
        const auto b = std::to_integer<unsigned>(bytes[pos++]);
        if (i == 9 && b > 1) return false;
        value |= static_cast<std::uint64_t>(b & 127) << (7 * i);
        if (!(b & 128)) return true;
    }
    return false;
}
struct Field { unsigned type = 0, minimum = 0, maximum = 0; };
Error preflight(Kind kind, std::span<const std::byte> bytes) {
    if (bytes.size() > management_payload_bytes) return Error::oversize;
    std::array<Field, 8> fields{};
    switch (kind) {
    case Kind::hello: fields = {{{}, {2,1,64}, {2,32,32}, {0,0,0}, {0,0,0}, {0,0,0}}}; break;
    case Kind::welcome: fields = {{{}, {2,1,64}, {2,32,32}, {2,16,16}, {2,16,16}, {0,0,0}, {0,0,0}, {0,0,0}}}; break;
    case Kind::ready: fields = {{{}, {0,0,0}, {2,32,32}, {2,16,16}}}; break;
    case Kind::bind: fields = {{{}, {2,16,16}, {2,16,16}, {2,16,16}}}; break;
    case Kind::time_probe: fields = {{{}, {0,0,0}}}; break;
    case Kind::time_reply: fields = {{{}, {0,0,0}, {0,0,0}, {0,0,0}}}; break;
    default: return Error::unsupported_kind;
    }
    const unsigned last = kind == Kind::hello ? 5 : kind == Kind::welcome ? 7 :
        kind == Kind::ready || kind == Kind::bind ? 3 : kind == Kind::time_probe ? 1 : 3;
    unsigned seen = 0;
    std::size_t pos = 0;
    while (pos < bytes.size()) {
        std::uint64_t key;
        if (!varint(bytes, pos, key) || key == 0 || key > 0xffffffffULL) return Error::malformed;
        const auto number = static_cast<unsigned>(key >> 3), type = static_cast<unsigned>(key & 7);
        if (number == 0 || number > last) return Error::unknown_field;
        if (seen & (1U << number)) return Error::duplicate_field;
        seen |= 1U << number;
        if (fields[number].type != type) return Error::malformed;
        std::uint64_t value;
        if (!varint(bytes, pos, value)) return Error::malformed;
        if (type == 0) {
            const bool time = kind == Kind::time_probe || kind == Kind::time_reply;
            if (value > (time ? static_cast<std::uint64_t>(std::numeric_limits<std::int64_t>::max()) : 0xffffffffULL))
                return time ? Error::invalid_time : Error::invalid_limits;
        } else {
            if (value > bytes.size() - pos) return Error::malformed;
            if (value < fields[number].minimum || value > fields[number].maximum) return Error::field_size;
            if (number == 1 && (kind == Kind::hello || kind == Kind::welcome) &&
                !peer_utf8({reinterpret_cast<const char*>(bytes.data() + pos), static_cast<std::size_t>(value)}))
                return Error::invalid_utf8;
            pos += static_cast<std::size_t>(value);
        }
    }
    // Proto3 scalar defaults are allowed (notably a zero monotonic timestamp).
    // Byte/string identities and digests must be explicitly present.
    const unsigned required = kind == Kind::hello ? 6 : kind == Kind::welcome ? 30 :
        kind == Kind::ready ? 4 : kind == Kind::bind ? 14 : 0;
    return (seen & required) == required ? Error::none : Error::field_size;
}
template<class Array> Array array(const std::string& text) {
    Array result{};
    std::memcpy(result.data(), text.data(), result.size()); // preflight checked exact lengths
    return result;
}
template<class Array> void bytes(std::string* output, const Array& value) {
    output->assign(reinterpret_cast<const char*>(value.data()), value.size());
}
template<class P> bool parse(P& message, std::span<const std::byte> payload) {
    return message.ParseFromArray(payload.data(), static_cast<int>(payload.size()));
}
Hello hello(const std::string& peer, const std::string& digest, unsigned sensor, unsigned control, unsigned routes) {
    return {peer, array<Digest>(digest), {sensor, control, routes}};
}
template<class P> void fill_hello(P& p, const Hello& h) {
    p.set_peer_id(h.peer_id); bytes(p.mutable_routes_sha256(), h.routes_sha256);
    p.set_max_sensor_message_bytes(h.limits.sensor_bytes);
    p.set_max_control_message_bytes(h.limits.control_bytes); p.set_max_routes(h.limits.routes);
}
template<class P> ManagementEncodeResult serialize(const P& message, std::span<std::byte> output) {
    const auto size = message.ByteSizeLong();
    if (size > management_payload_bytes) return {Error::oversize, 0};
    if (size > output.size()) return {Error::output_too_small, 0};
    std::array<std::byte, management_payload_bytes> temporary{};
    if (!message.SerializeToArray(temporary.data(), static_cast<int>(size))) return {Error::malformed, 0};
    std::copy_n(temporary.begin(), size, output.begin());
    return {Error::none, size};
}
}
Kind kind_of(const Management& m) noexcept {
    constexpr std::array kinds{Kind::hello, Kind::welcome, Kind::ready, Kind::bind, Kind::time_probe, Kind::time_reply};
    return m.index() < kinds.size() ? kinds[m.index()] : static_cast<Kind>(0);
}
ManagementResult decode_management(Kind kind, std::span<const std::byte> payload) {
    if (const auto error = preflight(kind, payload); error != Error::none) return {error, {}};
    Management result;
    switch (kind) {
    case Kind::hello: {
        pb::Hello p; if (!parse(p, payload)) return {Error::malformed, {}};
        result = hello(p.peer_id(), p.routes_sha256(), p.max_sensor_message_bytes(), p.max_control_message_bytes(), p.max_routes()); break;
    }
    case Kind::welcome: {
        pb::Welcome p; if (!parse(p, payload)) return {Error::malformed, {}};
        result = Welcome{hello(p.peer_id(), p.routes_sha256(), p.max_sensor_message_bytes(), p.max_control_message_bytes(), p.max_routes()),
                         array<Identity>(p.caller_epoch()), array<Identity>(p.listener_epoch())}; break;
    }
    case Kind::ready: {
        pb::Ready p; if (!parse(p, payload)) return {Error::malformed, {}};
        result = Ready{static_cast<ReadyPhase>(p.phase()), array<Digest>(p.routes_sha256()),
            p.sensor_binding_id().empty() ? Identity{} : array<Identity>(p.sensor_binding_id())}; break;
    }
    case Kind::bind: {
        pb::Bind p; if (!parse(p, payload)) return {Error::malformed, {}};
        result = Bind{array<Identity>(p.control_caller_epoch()), array<Identity>(p.control_listener_epoch()), array<Identity>(p.sensor_binding_id())}; break;
    }
    case Kind::time_probe: {
        pb::TimeProbe p; if (!parse(p, payload)) return {Error::malformed, {}};
        result = TimeProbe{p.initiator_send_ns()}; break;
    }
    case Kind::time_reply: {
        pb::TimeReply p; if (!parse(p, payload)) return {Error::malformed, {}};
        result = TimeReply{p.initiator_send_ns(), p.responder_receive_ns(), p.responder_send_ns()}; break;
    }
    default: return {Error::unsupported_kind, {}};
    }
    const auto error = std::visit([](const auto& value) { return valid(value); }, result);
    return error == Error::none ? ManagementResult{Error::none, std::move(result)} : ManagementResult{error, {}};
}
ManagementEncodeResult encode_management(const Management& m, std::span<std::byte> output) {
    if (m.valueless_by_exception()) return {Error::unsupported_kind, 0};
    const auto error = std::visit([](const auto& value) { return valid(value); }, m);
    if (error != Error::none) return {error, 0};
    return std::visit([output](const auto& value) -> ManagementEncodeResult {
        using T = std::decay_t<decltype(value)>;
        if constexpr (std::is_same_v<T, Hello>) {
            pb::Hello p; fill_hello(p, value); return serialize(p, output);
        } else if constexpr (std::is_same_v<T, Welcome>) {
            pb::Welcome p; fill_hello(p, value.parameters);
            bytes(p.mutable_caller_epoch(), value.caller_epoch); bytes(p.mutable_listener_epoch(), value.listener_epoch);
            return serialize(p, output);
        } else if constexpr (std::is_same_v<T, Ready>) {
            pb::Ready p; p.set_phase(static_cast<pb::Ready_Phase>(value.phase));
            bytes(p.mutable_routes_sha256(), value.routes_sha256);
            if (!zero(value.sensor_binding_id)) bytes(p.mutable_sensor_binding_id(), value.sensor_binding_id);
            return serialize(p, output);
        } else if constexpr (std::is_same_v<T, Bind>) {
            pb::Bind p; bytes(p.mutable_control_caller_epoch(), value.caller_epoch); bytes(p.mutable_control_listener_epoch(), value.listener_epoch);
            bytes(p.mutable_sensor_binding_id(), value.sensor_binding_id);
            return serialize(p, output);
        } else if constexpr (std::is_same_v<T, TimeProbe>) {
            pb::TimeProbe p; p.set_initiator_send_ns(value.initiator_send_ns); return serialize(p, output);
        } else {
            pb::TimeReply p; p.set_initiator_send_ns(value.initiator_send_ns);
            p.set_responder_receive_ns(value.responder_receive_ns); p.set_responder_send_ns(value.responder_send_ns);
            return serialize(p, output);
        }
    }, m);
}
}
