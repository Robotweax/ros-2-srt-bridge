#include <robotweax/srt_bridge/routes.hpp>
#include <algorithm>
#include <array>
#include <fstream>
#include <iostream>
#include <stdexcept>
using namespace robotweax::srt_bridge;
namespace {
unsigned checks = 0;
void check(bool b, const char* message) { ++checks; if (!b) throw std::runtime_error(message); }
std::vector<std::byte> read_hex(const char* filename) {
    std::ifstream file(std::string(GOLDEN_DIRECTORY) + "/" + filename); check(bool(file), "golden missing");
    std::vector<std::byte> result; std::string value;
    while (file >> value) result.push_back(static_cast<std::byte>(std::stoul(value,nullptr,16)));
    return result;
}
std::array<Route,2> routes() {
    return {Route{1,RouteKind::sensor,Direction::caller_to_listener,QosMapping::best_effort_volatile_last1,true,
                928,250,200,0,"sensor_msgs/msg/Imu","RIHS01_"+std::string(64,'a')},
            Route{100,RouteKind::command,Direction::listener_to_caller,QosMapping::request_status,true,
                4000,5000,0,1,"SetMeasurementRate","SHA256_"+std::string(64,'b')}};
}
void contract() {
    auto input = routes(); auto result = make_manifest(input); check(bool(result), "valid routes rejected");
    const auto bytes = read_hex("routes-v1.hex"), hash = read_hex("routes-v1.sha256");
    check(std::equal(bytes.begin(),bytes.end(),result.value->canonical().begin(),result.value->canonical().end()), "canonical golden mismatch");
    check(std::equal(hash.begin(),hash.end(),result.value->digest().begin(),result.value->digest().end()), "digest golden mismatch");
    check(result.value->find(1) && !result.value->find(99), "route lookup");
    std::reverse(input.begin(),input.end()); const auto reordered = make_manifest(input);
    check(reordered.value->digest() == result.value->digest(), "route order changed hash");
    input = routes(); input[0].enabled = false;
    check(make_manifest(input).value->digest() != result.value->digest(), "permission excluded from contract");
    input = routes(); ++input[0].budget_ms;
    check(make_manifest(input).value->digest() != result.value->digest(), "budget excluded from contract");
    check(make_manifest({}).error == ManifestError::route_count, "empty manifest");
    std::array<Route,9> too_many; too_many.fill(routes()[0]);
    check(make_manifest(too_many).error == ManifestError::route_count, "unbounded route count");
    input = routes(); input[1].id = 1;
    check(make_manifest(input).error == ManifestError::duplicate_route, "duplicate ID");
    for (int fault = 0; fault < 12; ++fault) {
        input = routes();
        if (fault == 0) input[0].id = 0;
        if (fault == 1) input[0].type_name = "";
        if (fault == 2) input[0].type_name = std::string(129,'x');
        if (fault == 3) input[0].type_name = "type\nname";
        if (fault == 4) input[0].type_hash = "Imu";
        if (fault == 5) input[0].type_hash[7] = 'A';
        if (fault == 6) input[0].direction = Direction::listener_to_caller;
        if (fault == 7) input[0].max_payload_bytes = 929;
        if (fault == 8) input[0].budget_ms = 0;
        if (fault == 9) input[0].max_rate_hz = 1001;
        if (fault == 10) input[1].max_inflight = 2;
        if (fault == 11) input[1].qos = QosMapping::best_effort_volatile_last1;
        check(!make_manifest(input), "invalid wire contract accepted");
    }
}
}
int main() { try { contract(); std::cout << "PASS routes contract: " << checks << " checks\n"; }
    catch (const std::exception& e) { std::cerr << "FAIL: " << e.what() << '\n'; return 1; } }
