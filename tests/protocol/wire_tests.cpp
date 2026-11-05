#include <robotweax/srt_bridge/wire.hpp>
#include <algorithm>
#include <array>
#include <fstream>
#include <iostream>
#include <random>
#include <stdexcept>
#include <string>
#include <vector>
using namespace robotweax::srt_bridge;
namespace {
std::size_t assertions = 0;
void check(bool condition, const char* message) {
    ++assertions;
    if (!condition) throw std::runtime_error(message);
}
constexpr std::array<std::uint32_t, 3> routes{1, 2, 100};
Envelope fixture() {
    Envelope e;
    e.route_id = 1;
    for (std::size_t i = 0; i < 16; ++i) {
        e.session_id[i] = static_cast<std::byte>(i);
        e.source_epoch[i] = static_cast<std::byte>(i + 16);
    }
    e.sequence = 0x0102030405060708ULL;
    e.source_monotonic_ns = 0x1122334455667788ULL;
    e.clock_domain = 0x01020304;
    e.valid_for_ms = 250;
    return e;
}
std::vector<std::byte> golden() {
    std::ifstream file(GOLDEN_FILE);
    check(bool(file), "golden vector missing");
    std::vector<std::byte> bytes;
    std::string token;
    while (file >> token) bytes.push_back(static_cast<std::byte>(std::stoul(token, nullptr, 16)));
    check(bytes.size() == 100, "golden vector length");
    return bytes;
}
void golden_and_bounds() {
    const auto expected = golden();
    const auto decoded = decode(expected, Channel::sensor, routes);
    check(bool(decoded), "golden vector rejected");
    check(decoded.message.envelope == fixture(), "golden header mismatch");
    check(decoded.message.payload.size() == 4 && decoded.message.payload[0] == std::byte{0xde}, "golden payload");
    std::array<std::byte, 4096> output{};
    const auto result = encode(fixture(), decoded.message.payload, Channel::sensor, routes, output);
    check(bool(result) && result.bytes_written == expected.size(), "golden encoding failed");
    check(std::equal(expected.begin(), expected.end(), output.begin()), "golden encoding differs");
    for (std::size_t length = 0; length < envelope_bytes; ++length)
        check(decode(std::span(expected).first(length), Channel::sensor, routes).error == WireError::truncated, "truncated header accepted");
    for (const auto channel : {Channel::sensor, Channel::control}) {
        auto e = fixture();
        if (channel == Channel::control) { e.kind = Kind::command; e.route_id = 100; e.request_id[0] = std::byte{1}; }
        const auto max = channel == Channel::sensor ? sensor_message_bytes : control_message_bytes;
        std::vector<std::byte> payload(max - envelope_bytes, std::byte{0xff});
        const auto encoded = encode(e, payload, channel, routes, output);
        check(bool(encoded) && encoded.bytes_written == max, "maximum message rejected");
        check(bool(decode(std::span(output).first(max), channel, routes)), "maximum message decode");
        payload.push_back(std::byte{});
        auto untouched = output;
        check(encode(e, payload, channel, routes, output).error == WireError::oversize, "oversize encode accepted");
        check(output == untouched, "failed encode changed output");
        std::vector<std::byte> oversized(max + 1);
        check(decode(oversized, channel, routes).error == WireError::oversize, "oversize decode accepted");
    }
    output.fill(std::byte{0xa5});
    const auto before = output;
    check(encode(fixture(), {}, Channel::sensor, routes, std::span(output).first(95)).error == WireError::output_too_small, "short output accepted");
    check(output == before, "short output changed");
    std::copy(expected.begin(), expected.end(), output.begin());
    const auto in_place = encode(fixture(), std::span(output).subspan(96, 4), Channel::sensor, routes, output);
    check(bool(in_place) && std::equal(expected.begin(), expected.end(), output.begin()), "in-place encoding");
}
void rejection_cases() {
    const auto valid = golden();
    struct Mutation { std::size_t offset; unsigned value; WireError error; };
    for (const auto& m : {Mutation{0, 0, WireError::bad_magic}, {5, 2, WireError::bad_version},
        {7, 0, WireError::bad_kind}, {7, 12, WireError::bad_kind}, {8, 1, WireError::bad_flags},
        {79, 1, WireError::bad_reserved}, {75, 3, WireError::bad_length},
        {15, 0, WireError::bad_route}, {15, 3, WireError::bad_route}, {95, 1, WireError::bad_request_id}}) {
        auto bad = valid; bad[m.offset] = static_cast<std::byte>(m.value);
        const auto decoded = decode(bad, Channel::sensor, routes);
        check(decoded.error == m.error, "mutation returned wrong error");
        check(decoded.message.payload.empty(), "failed decode exposed payload");
    }
    check(decode(valid, Channel::control, routes).error == WireError::wrong_channel, "cross-channel sample");
    check(decode(valid, Channel::sensor, {}).error == WireError::bad_route, "empty allowlist admitted sample");
    for (unsigned k = 1; k <= 11; ++k) {
        Envelope e; e.kind = static_cast<Kind>(k);
        const bool sensor = e.kind == Kind::sample || e.kind == Kind::bind;
        const bool command = e.kind == Kind::command || e.kind == Kind::status || e.kind == Kind::query || e.kind == Kind::error;
        if (e.kind == Kind::sample || command) e.route_id = 1;
        if (command) e.request_id[0] = std::byte{1};
        std::array<std::byte, 96> output;
        const auto channel = sensor ? Channel::sensor : Channel::control;
        check(bool(encode(e, {}, channel, routes, output)), "defined kind rejected");
        check(bool(decode(output, channel, routes)), "defined kind decode rejected");
        check(decode(output, sensor ? Channel::control : Channel::sensor, routes).error == WireError::wrong_channel, "cross-channel kind accepted");
        if (sensor) {
            e.request_id[0] = std::byte{1};
            check(encode(e, {}, channel, routes, output).error == WireError::bad_request_id, "SENSOR request ID accepted");
            e.request_id = {};
        }
        if (command) {
            e.request_id = {};
            check(encode(e, {}, channel, routes, output).error == WireError::bad_request_id, "zero command ID accepted");
        }
    }
}
void deterministic_mutations() {
    const auto valid = golden();
    std::mt19937 random(0x52575342);
    std::array<std::byte, 4096> output;
    for (unsigned i = 0; i < 20000; ++i) {
        auto bytes = valid;
        if (i % 3 == 0) bytes.resize(random() % 4200);
        else for (unsigned j = 0; j <= i % 8; ++j) bytes[random() % bytes.size()] = static_cast<std::byte>(random() & 255);
        const auto decoded = decode(bytes, Channel::sensor, routes);
        if (decoded) {
            const auto encoded = encode(decoded.message.envelope, decoded.message.payload, Channel::sensor, routes, output);
            check(bool(encoded) && encoded.bytes_written == bytes.size(), "accepted mutation cannot encode");
            check(std::equal(bytes.begin(), bytes.end(), output.begin()), "accepted mutation is noncanonical");
        } else check(decoded.message.payload.empty(), "rejected mutation exposed bytes");
    }
}
}
int main() {
    try {
        golden_and_bounds(); rejection_cases(); deterministic_mutations();
        std::cout << "PASS wire contract: " << assertions << " assertions, 20000 deterministic mutations\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "FAIL: " << error.what() << '\n'; return 1;
    }
}
