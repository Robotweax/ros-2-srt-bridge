#include <robotweax/srt_bridge/routes.hpp>
#include <openssl/evp.h>
#include <algorithm>

namespace robotweax::srt_bridge {
namespace {
ManifestError validate(const Route& r) {
    if (!r.id) return ManifestError::invalid_route;
    if (r.type_name.empty() || r.type_name.size() > 128 ||
        !std::all_of(r.type_name.begin(), r.type_name.end(), [](unsigned char c) {
            return (c >= 'A' && c <= 'Z') || (c >= 'a' && c <= 'z') ||
                (c >= '0' && c <= '9') || c == '_' || c == '/' || c == '.';
        })) return ManifestError::invalid_type;
    const auto prefix = r.kind == RouteKind::sensor ? "RIHS01_" : "SHA256_";
    if (r.type_hash.size() != 71 || r.type_hash.substr(0, 7) != prefix ||
        !std::all_of(r.type_hash.begin() + 7, r.type_hash.end(), [](char c) {
            return (c >= '0' && c <= '9') || (c >= 'a' && c <= 'f');
        })) return ManifestError::invalid_hash;
    if (!r.max_payload_bytes || !r.budget_ms || r.budget_ms > 60000) return ManifestError::invalid_limits;
    if (r.kind == RouteKind::sensor) {
        if (r.direction != Direction::caller_to_listener || r.qos != QosMapping::best_effort_volatile_last1)
            return ManifestError::unsupported_policy;
        if (r.max_payload_bytes > 928 || !r.max_rate_hz || r.max_rate_hz > 1000 || r.max_inflight)
            return ManifestError::invalid_limits;
    } else if (r.kind == RouteKind::command) {
        if (r.direction != Direction::listener_to_caller || r.qos != QosMapping::request_status)
            return ManifestError::unsupported_policy;
        if (r.max_payload_bytes > 4000 || r.max_rate_hz || r.max_inflight != 1)
            return ManifestError::invalid_limits;
    } else return ManifestError::unsupported_policy;
    return ManifestError::none;
}
void integer(std::vector<std::byte>& output, std::uint32_t value, unsigned bytes) {
    for (unsigned i = bytes; i > 0; --i) output.push_back(static_cast<std::byte>((value >> ((i - 1) * 8)) & 255));
}
void text(std::vector<std::byte>& output, const std::string& value) {
    integer(output, value.size(), 2);
    for (unsigned char c : value) output.push_back(static_cast<std::byte>(c));
}
}
RouteManifest::RouteManifest(std::vector<Route> routes, std::vector<std::byte> canonical, Digest digest)
    : routes_(std::move(routes)), canonical_(std::move(canonical)), digest_(digest) {}
const Route* RouteManifest::find(std::uint32_t id) const noexcept {
    const auto it = std::lower_bound(routes_.begin(), routes_.end(), id,
        [](const Route& r, std::uint32_t value) { return r.id < value; });
    return it != routes_.end() && it->id == id ? &*it : nullptr;
}
ManifestResult make_manifest(std::span<const Route> input) {
    if (input.empty() || input.size() > 8) return {ManifestError::route_count, {}};
    for (const auto& route : input)
        if (auto error = validate(route); error != ManifestError::none) return {error, {}};
    std::vector<Route> routes(input.begin(), input.end());
    std::sort(routes.begin(), routes.end(), [](const Route& a, const Route& b) { return a.id < b.id; });
    for (std::size_t i = 1; i < routes.size(); ++i)
        if (routes[i-1].id == routes[i].id) return {ManifestError::duplicate_route, {}};
    std::vector<std::byte> canonical;
    canonical.reserve(2048); // validated maximum: 12 + 8 * (28 + 128 + 71) = 1828
    for (unsigned char c : std::string("RWRM")) canonical.push_back(static_cast<std::byte>(c));
    integer(canonical, 1, 2); integer(canonical, 0, 2); integer(canonical, routes.size(), 4);
    for (const auto& r : routes) {
        integer(canonical, r.id, 4);
        integer(canonical, static_cast<unsigned>(r.kind), 1);
        integer(canonical, static_cast<unsigned>(r.direction), 1);
        integer(canonical, static_cast<unsigned>(r.qos), 1);
        integer(canonical, r.enabled ? 1 : 0, 1);
        for (auto value : {r.max_payload_bytes, r.budget_ms, r.max_rate_hz, r.max_inflight}) integer(canonical, value, 4);
        text(canonical, r.type_name); text(canonical, r.type_hash);
    }
    Digest digest{}; unsigned size = digest.size();
    if (EVP_Digest(canonical.data(), canonical.size(), reinterpret_cast<unsigned char*>(digest.data()), &size, EVP_sha256(), nullptr) != 1 || size != digest.size())
        return {ManifestError::digest_failure, {}};
    return {ManifestError::none, RouteManifest{std::move(routes), std::move(canonical), digest}};
}
}
