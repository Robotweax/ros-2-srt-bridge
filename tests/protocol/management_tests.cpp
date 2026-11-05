#include <robotweax/srt_bridge/management.hpp>
#include "management_v1.pb.h"
#include <algorithm>
#include <array>
#include <iostream>
#include <limits>
#include <random>
#include <stdexcept>
#include <vector>
using namespace robotweax::srt_bridge;
namespace pb = robotweax::srt_bridge::v1;
namespace {
std::size_t assertions = 0;
void check(bool condition, const char* message) {
    ++assertions;
    if (!condition) throw std::runtime_error(message);
}
Identity id(unsigned n) { Identity value{}; value[0] = static_cast<std::byte>(n); return value; }
Hello hello() { Digest digest{}; digest.fill(std::byte{0xab}); return {"lab-peer", digest, {1024, 4096, 8}}; }
std::vector<std::byte> encoded(const Management& value) {
    std::array<std::byte, 512> output;
    const auto result = encode_management(value, output);
    check(bool(result), "encode failed");
    return {output.begin(), output.begin() + result.bytes_written};
}
std::vector<std::byte> wire(std::initializer_list<unsigned> values) {
    std::vector<std::byte> result;
    for (auto v : values) result.push_back(static_cast<std::byte>(v));
    return result;
}
void examples() {
    const std::array<Management, 8> fixtures{hello(), Welcome{hello(), id(1), id(2)},
        Ready{ReadyPhase::control_ready, hello().routes_sha256}, Ready{ReadyPhase::sensor_bound, hello().routes_sha256, id(3)},
        Bind{id(1), id(2), id(3)}, TimeProbe{0}, TimeProbe{123456789}, TimeReply{123, 456, 789}};
    for (const auto& value : fixtures) {
        const auto bytes = encoded(value);
        const auto decoded = decode_management(kind_of(value), bytes);
        check(bool(decoded) && decoded.value == value, "roundtrip");
        std::array<std::byte, 512> out;
        out.fill(std::byte{0xa5}); const auto untouched = out;
        if (!bytes.empty()) {
            const auto too_short = encode_management(value, std::span(out).first(bytes.size() - 1));
            check(too_short.error == ManagementError::output_too_small && out == untouched, "encode failure changed destination");
        }
    }
    // Independent Protobuf golden: field 1 (varint) = 150.
    check(encoded(TimeProbe{150}) == wire({0x08, 0x96, 0x01}), "time probe golden");
    check(encoded(TimeReply{1, 2, 3}) == wire({0x08,1,0x10,2,0x18,3}), "time reply golden");
    auto maximum = hello(); maximum.peer_id = std::string(64, 'p');
    check(bool(decode_management(Kind::hello, encoded(maximum))), "64-byte peer ID rejected");
    maximum.peer_id = "\xc3\xa4-peer";
    check(bool(decode_management(Kind::hello, encoded(maximum))), "valid UTF-8 rejected");
    pb::Hello reference;
    const auto bytes = encoded(hello());
    check(reference.ParseFromArray(bytes.data(), bytes.size()), "generated parser rejected encoding");
    check(reference.peer_id() == "lab-peer" && reference.max_routes() == 8, "generated parser values");
    static_assert(static_cast<int>(Kind::hello) == pb::HELLO);
    static_assert(static_cast<int>(Kind::welcome) == pb::WELCOME);
    static_assert(static_cast<int>(Kind::ready) == pb::READY);
    static_assert(static_cast<int>(Kind::bind) == pb::BIND);
    static_assert(static_cast<int>(Kind::sample) == pb::SAMPLE);
    static_assert(static_cast<int>(Kind::command) == pb::COMMAND);
    static_assert(static_cast<int>(Kind::status) == pb::STATUS);
    static_assert(static_cast<int>(Kind::query) == pb::QUERY);
    static_assert(static_cast<int>(Kind::time_probe) == pb::TIME_PROBE);
    static_assert(static_cast<int>(Kind::time_reply) == pb::TIME_REPLY);
    static_assert(static_cast<int>(Kind::error) == pb::ERROR);
}
void invalid_fields() {
    auto h = hello();
    std::array<std::byte, 512> out;
    for (const auto& bad_id : {std::string{}, std::string(65, 'x'), std::string("\xc0\x80"),
          std::string("\xed\xa0\x80"), std::string("\xf4\x90\x80\x80"), std::string("x\0y",3),
          std::string("\xc2\x80"), std::string("\xe2\x82"), std::string("line\nbreak")}) {
        h.peer_id = bad_id;
        check(encode_management(h, out).error != ManagementError::none, "invalid ID encoded");
    }
    h = hello();
    for (auto limits : {Limits{1023,4096,8}, {1024,4095,8}, {1024,4096,0}, {1024,4096,9}}) {
        h.limits = limits;
        check(encode_management(h, out).error == ManagementError::invalid_limits, "invalid limits encoded");
    }
    check(encode_management(Bind{id(1),id(1)}, out).error == ManagementError::invalid_identity, "identical epochs");
    check(encode_management(Bind{id(1),id(2),{}}, out).error == ManagementError::invalid_identity, "missing binding nonce");
    auto legacy_bind = encoded(Bind{id(1),id(2),id(3)}); legacy_bind.resize(36);
    check(decode_management(Kind::bind, legacy_bind).error == ManagementError::field_size, "legacy uncorrelated BIND accepted");
    auto legacy_ack = encoded(Ready{ReadyPhase::control_ready,{}}); legacy_ack[1]=std::byte{2};
    check(decode_management(Kind::ready, legacy_ack).error == ManagementError::invalid_identity, "uncorrelated SENSOR ack accepted");
    check(encode_management(Bind{{},id(2)}, out).error == ManagementError::invalid_identity, "zero epoch");
    check(encode_management(Ready{static_cast<ReadyPhase>(3),{}}, out).error == ManagementError::invalid_phase, "unknown phase");
    check(encode_management(TimeReply{1,3,2}, out).error == ManagementError::invalid_time, "negative processing duration");
    check(encode_management(TimeProbe{std::numeric_limits<std::uint64_t>::max()}, out).error == ManagementError::invalid_time, "unrepresentable timestamp");
    struct Bad { Kind kind; std::vector<std::byte> bytes; ManagementError error; };
    const std::vector<Bad> invalid{
        {Kind::sample, {}, ManagementError::unsupported_kind},
        {Kind::time_probe, std::vector<std::byte>(513), ManagementError::oversize},
        {Kind::time_probe, wire({0x08,0x80}), ManagementError::malformed},
        {Kind::time_probe, wire({0x08,1,0x08,2}), ManagementError::duplicate_field},
        {Kind::time_probe, wire({0x10,1}), ManagementError::unknown_field},
        {Kind::time_probe, wire({0x0a,1,0}), ManagementError::malformed},
        {Kind::time_probe, wire({0}), ManagementError::malformed},
        {Kind::time_probe, wire({8,0xff,0xff,0xff,0xff,0xff,0xff,0xff,0xff,0xff,2}), ManagementError::malformed},
        {Kind::hello, {}, ManagementError::field_size},
        {Kind::hello, wire({0x0a,65}), ManagementError::malformed},
        {Kind::hello, wire({0x0a,2,0xc0,0x80}), ManagementError::invalid_utf8},
        {Kind::ready, wire({0x10,0}), ManagementError::malformed}
    };
    for (const auto& value : invalid)
        check(decode_management(value.kind, value.bytes).error == value.error, "malformed payload reason");
    auto long_id = wire({0x0a,65}); long_id.resize(67, std::byte{'x'});
    check(decode_management(Kind::hello, long_id).error == ManagementError::field_size, "oversize peer field allocated/accepted");
    auto bad_phase = encoded(Ready{ReadyPhase::control_ready,{}}); bad_phase[1] = std::byte{3};
    check(decode_management(Kind::ready, bad_phase).error == ManagementError::invalid_phase, "incoming unknown phase");
    check(decode_management(Kind::time_reply, wire({8,1,16,3,24,2})).error == ManagementError::invalid_time, "incoming backwards responder time");
    auto bad_bind = encoded(Bind{id(1),id(2),id(3)}); bad_bind[20] = std::byte{1};
    check(decode_management(Kind::bind, bad_bind).error == ManagementError::invalid_identity, "incoming repeated epochs");
    auto bytes = encoded(hello());
    // Peer ID is the first field in generated output; remove one byte from the hash.
    check(bytes[0] == std::byte{0x0a} && bytes[10] == std::byte{0x12}, "fixture layout");
    bytes[11] = std::byte{31}; bytes.erase(bytes.begin() + 12);
    check(decode_management(Kind::hello, bytes).error == ManagementError::field_size, "short digest accepted");
    // Properly bounded Protobuf fields can still violate semantic limits.
    pb::Hello p; p.set_peer_id("lab"); p.set_routes_sha256(std::string(32, 'd'));
    p.set_max_sensor_message_bytes(1023); p.set_max_control_message_bytes(4096); p.set_max_routes(8);
    const auto text = p.SerializeAsString();
    check(decode_management(Kind::hello, {reinterpret_cast<const std::byte*>(text.data()),text.size()}).error == ManagementError::invalid_limits, "peer limits accepted");
    // Field ordering is deliberately independent of Protobuf's serialization order.
    const auto normal = encoded(hello());
    bytes.assign(normal.begin() + 10, normal.end()); bytes.insert(bytes.end(), normal.begin(), normal.begin() + 10);
    check(decode_management(Kind::hello, bytes).value == Management{hello()}, "unordered fields rejected");
}
void mutations() {
    std::mt19937 random(0x50524f54);
    const std::array<Management, 6> fixtures{hello(), Welcome{hello(),id(1),id(2)},
        Ready{ReadyPhase::control_ready,{}}, Bind{id(1),id(2),id(3)}, TimeProbe{150}, TimeReply{1,2,3}};
    for (int i = 0; i < 20000; ++i) {
        const auto& original = fixtures[i % fixtures.size()];
        auto bytes = encoded(original);
        if (i % 3 == 0) bytes.resize(random() % 530);
        else for (int j = 0; j <= i % 4; ++j) bytes[random() % bytes.size()] = static_cast<std::byte>(random() & 255);
        const auto result = decode_management(kind_of(original), bytes);
        if (result) {
            const auto canonical = encoded(result.value);
            const auto again = decode_management(kind_of(original), canonical);
            check(bool(again) && again.value == result.value, "accepted mutation unstable");
        }
    }
}
}
int main() {
    try { examples(); invalid_fields(); mutations();
        std::cout << "PASS management contract: " << assertions << " assertions, 20000 mutations\n";
    } catch (const std::exception& e) { std::cerr << "FAIL: " << e.what() << '\n'; return 1; }
}
