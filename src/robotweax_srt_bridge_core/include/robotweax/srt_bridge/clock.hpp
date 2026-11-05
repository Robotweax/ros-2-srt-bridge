#pragma once
#include <robotweax/srt_bridge/wire.hpp>
#include <cstdint>
#include <optional>

namespace robotweax::srt_bridge {
struct ClockConfig {
    // Explicit engineering assumptions, not measurements of either host's clock.
    std::uint32_t relative_drift_ppm;
    std::uint64_t timestamp_error_ns;
    std::uint64_t max_probe_age_ns;
    // Full width of the offset interval, rather than its half-width.
    std::uint64_t max_offset_width_ns;
};
struct Probe {
    Identity local_epoch{}, remote_epoch{};
    std::uint32_t local_domain = 0, remote_domain = 0;
    // Local endpoint initiates, regardless of its SRT Caller/Listener role.
    std::uint64_t t1 = 0, t2 = 0, t3 = 0, t4 = 0;
};
struct Interval {
    std::int64_t lower = 0, upper = 0;
    bool operator==(const Interval&) const = default;
};
enum class ClockError {
    none, unqualified, expired, epoch_mismatch, domain_mismatch, invalid_probe,
    clock_regressed, contradictory, arithmetic_overflow, future_sample
};
struct AgeResult {
    ClockError error = ClockError::unqualified;
    std::optional<Interval> age_ns;
    bool within_budget(std::uint64_t budget_ns) const noexcept {
        return error == ClockError::none && age_ns && age_ns->upper >= 0 &&
            static_cast<std::uint64_t>(age_ns->upper) <= budget_ns;
    }
};
// Single-owner state; caller correlates probes with its outstanding requests.
// An invalidating error is sticky until reset, which must also flush sample queues.
class ClockMapper {
public:
    explicit ClockMapper(ClockConfig config);
    bool reset(Identity local_epoch, Identity remote_epoch,
               std::uint32_t local_domain, std::uint32_t remote_domain) noexcept;
    ClockError observe(const Probe& probe) noexcept;
    ClockError check(std::uint64_t local_now_ns) noexcept;
    // Session/epoch/domain admission must precede this time-only calculation.
    AgeResult age_of_remote(std::uint64_t remote_ingress_ns,
                            std::uint64_t local_receive_ns) noexcept;
    // Conservative exclusive limit of current probe age and drift-width qualification.
    std::optional<std::uint64_t> qualification_deadline() const noexcept;
    std::optional<Interval> offset_at_probe() const noexcept;
    ClockError state() const noexcept { return error_; }
private:
    ClockConfig config_;
    Identity local_epoch_{}, remote_epoch_{};
    std::uint32_t local_domain_ = 0, remote_domain_ = 0;
    bool bound_ = false, observed_ = false, invalid_ = false;
    std::int64_t anchor_ = 0, last_local_ = 0;
    Interval offset_{}; // remote minus local, at local anchor_
    ClockError error_ = ClockError::unqualified;
    ClockError invalidate(ClockError error) noexcept;
};
}
