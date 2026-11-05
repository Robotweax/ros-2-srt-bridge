#pragma once
#include <robotweax/srt_bridge/wire.hpp>
#include <optional>
#include <string>
#include <vector>

namespace robotweax::srt_bridge {
enum class RouteKind : std::uint8_t { sensor = 1, command = 2 };
enum class Direction : std::uint8_t { caller_to_listener = 1, listener_to_caller = 2 };
enum class QosMapping : std::uint8_t { best_effort_volatile_last1 = 1, request_status = 2 };
struct Route {
    std::uint32_t id = 0;
    RouteKind kind = RouteKind::sensor;
    Direction direction = Direction::caller_to_listener;
    QosMapping qos = QosMapping::best_effort_volatile_last1;
    bool enabled = true;
    std::uint32_t max_payload_bytes = 928, budget_ms = 250, max_rate_hz = 200, max_inflight = 0;
    std::string type_name, type_hash;
    bool operator==(const Route&) const = default;
};
enum class ManifestError {
    none, route_count, duplicate_route, invalid_route, invalid_type, invalid_hash,
    unsupported_policy, invalid_limits, digest_failure
};
struct ManifestResult;
class RouteManifest {
public:
    const Digest& digest() const noexcept { return digest_; }
    std::span<const std::byte> canonical() const noexcept { return canonical_; }
    std::span<const Route> routes() const noexcept { return routes_; }
    const Route* find(std::uint32_t id) const noexcept;
private:
    RouteManifest(std::vector<Route> routes, std::vector<std::byte> canonical, Digest digest);
    std::vector<Route> routes_;
    std::vector<std::byte> canonical_;
    Digest digest_;
    friend ManifestResult make_manifest(std::span<const Route>);
};
struct ManifestResult {
    ManifestError error = ManifestError::none;
    std::optional<RouteManifest> value;
    explicit operator bool() const { return error == ManifestError::none && value.has_value(); }
};
// RWRM v1 canonical binary encoding sorts by ID; local topic names and local
// endpoint roles are deliberately not part of this shared wire contract.
ManifestResult make_manifest(std::span<const Route> routes);
}
