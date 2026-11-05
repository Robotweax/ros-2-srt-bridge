#include <robotweax/srt_bridge/clock.hpp>
#include <algorithm>
#include <limits>
#include <stdexcept>

namespace robotweax::srt_bridge {
namespace {
using I = std::int64_t;
constexpr I max = std::numeric_limits<I>::max();
constexpr I min = std::numeric_limits<I>::min();
bool add(I a, I b, I& out) {
    if ((b > 0 && a > max - b) || (b < 0 && a < min - b)) return false;
    out = a + b; return true;
}
bool sub(I a, I b, I& out) {
    if ((b > 0 && a < min + b) || (b < 0 && a > max + b)) return false;
    out = a - b; return true;
}
bool zero(const Identity& id) {
    return std::all_of(id.begin(), id.end(), [](auto b) { return b == std::byte{}; });
}
I drift(I elapsed, std::uint32_t ppm) {
    // elapsed is nonnegative. Split before multiplying to avoid overflow.
    return (elapsed / 1000000) * ppm + ((elapsed % 1000000) * ppm + 999999) / 1000000;
}
// Outward-rounded signed x * 1e6 / denominator; no floating point or int128.
bool scale(I x, std::uint32_t denominator, bool round_up, I& out) {
    if (x == min) return false;
    const auto magnitude = static_cast<std::uint64_t>(x < 0 ? -x : x);
    const auto q = magnitude / denominator;
    const auto rem = magnitude % denominator;
    if (q > static_cast<std::uint64_t>(max) / 1000000) return false;
    const auto fraction = rem * 1000000;
    auto value = q * 1000000 + fraction / denominator;
    const bool away_from_zero = x < 0 ? !round_up : round_up;
    if (away_from_zero && fraction % denominator) ++value;
    if (value > static_cast<std::uint64_t>(max)) return false;
    out = x < 0 ? -static_cast<I>(value) : static_cast<I>(value);
    return true;
}
}
ClockMapper::ClockMapper(ClockConfig config) : config_(config) {
    if (config.relative_drift_ppm > 10000 || config.timestamp_error_ns > 1000000000 ||
        config.max_probe_age_ns == 0 || config.max_probe_age_ns > 60000000000ULL ||
        config.max_offset_width_ns == 0 || config.max_offset_width_ns > 1000000000)
        throw std::invalid_argument("invalid ClockMapper bounds");
}
bool ClockMapper::reset(Identity local, Identity remote, std::uint32_t local_domain,
                        std::uint32_t remote_domain) noexcept {
    local_epoch_ = local; remote_epoch_ = remote;
    local_domain_ = local_domain; remote_domain_ = remote_domain;
    bound_ = !zero(local) && !zero(remote) && local != remote;
    observed_ = false; invalid_ = false; anchor_ = last_local_ = 0; offset_ = {};
    error_ = bound_ ? ClockError::unqualified : ClockError::epoch_mismatch;
    return bound_;
}
ClockError ClockMapper::invalidate(ClockError error) noexcept {
    invalid_ = true; error_ = error; return error;
}
ClockError ClockMapper::observe(const Probe& p) noexcept {
    if (invalid_) return error_;
    if (!bound_ || p.local_epoch != local_epoch_ || p.remote_epoch != remote_epoch_)
        return invalidate(ClockError::epoch_mismatch);
    if (p.local_domain != local_domain_ || p.remote_domain != remote_domain_)
        return invalidate(ClockError::domain_mismatch);
    for (auto t : {p.t1, p.t2, p.t3, p.t4})
        if (t > static_cast<std::uint64_t>(max)) return invalidate(ClockError::arithmetic_overflow);
    if (p.t4 < p.t1 || p.t3 < p.t2) return invalidate(ClockError::invalid_probe);
    if (observed_ && (p.t1 < static_cast<std::uint64_t>(anchor_) ||
        p.t4 < static_cast<std::uint64_t>(last_local_) || p.t4 <= static_cast<std::uint64_t>(anchor_)))
        return invalidate(ClockError::clock_regressed);
    const auto t1 = static_cast<I>(p.t1), t2 = static_cast<I>(p.t2);
    const auto t3 = static_cast<I>(p.t3), t4 = static_cast<I>(p.t4);
    I margin, round_trip;
    if (!add(t4 - t1, static_cast<I>(2 * config_.timestamp_error_ns), round_trip) ||
        !add(drift(round_trip, config_.relative_drift_ppm), static_cast<I>(2 * config_.timestamp_error_ns), margin))
        return invalidate(ClockError::arithmetic_overflow);
    Interval candidate;
    if (!sub(t3 - t4, margin, candidate.lower) || !add(t2 - t1, margin, candidate.upper))
        return invalidate(ClockError::arithmetic_overflow);
    if (candidate.lower > candidate.upper) return invalidate(ClockError::invalid_probe);
    if (observed_) {
        const I change = drift(t4 - anchor_, config_.relative_drift_ppm);
        I lower, upper;
        if (!sub(offset_.lower, change, lower) || !add(offset_.upper, change, upper))
            return invalidate(ClockError::arithmetic_overflow);
        candidate.lower = std::max(candidate.lower, lower);
        candidate.upper = std::min(candidate.upper, upper);
        if (candidate.lower > candidate.upper) return invalidate(ClockError::contradictory);
    }
    I width;
    if (!sub(candidate.upper, candidate.lower, width)) return invalidate(ClockError::arithmetic_overflow);
    offset_ = candidate; observed_ = true; anchor_ = last_local_ = t4;
    error_ = static_cast<std::uint64_t>(width) <= config_.max_offset_width_ns ? ClockError::none : ClockError::unqualified;
    return error_;
}
ClockError ClockMapper::check(std::uint64_t now) noexcept {
    if (invalid_) return error_;
    if (!observed_) return ClockError::unqualified;
    if (now > static_cast<std::uint64_t>(max)) return invalidate(ClockError::arithmetic_overflow);
    const auto n = static_cast<I>(now);
    if (n < last_local_) return invalidate(ClockError::clock_regressed);
    last_local_ = n;
    if (static_cast<std::uint64_t>(n - anchor_) > config_.max_probe_age_ns) return error_ = ClockError::expired;
    const I change = drift(n - anchor_, config_.relative_drift_ppm);
    I width;
    if (!sub(offset_.upper, offset_.lower, width) || !add(width, 2 * change, width))
        return invalidate(ClockError::arithmetic_overflow);
    return error_ = static_cast<std::uint64_t>(width) > config_.max_offset_width_ns ? ClockError::unqualified : ClockError::none;
}
AgeResult ClockMapper::age_of_remote(std::uint64_t remote, std::uint64_t now) noexcept {
    if (const auto error = check(now); error != ClockError::none) return {error, std::nullopt};
    if (remote > static_cast<std::uint64_t>(max)) return {invalidate(ClockError::arithmetic_overflow), std::nullopt};
    const auto n = static_cast<I>(now), r = static_cast<I>(remote);
    // Transform a remote event around the probe anchor using the rate bounds:
    // delta_remote = delta_local * (1 + relative drift). This handles events
    // both before and after the probe without assuming path symmetry.
    I low, high;
    const auto uncertainty = static_cast<I>(config_.timestamp_error_ns);
    if (!sub(r, anchor_, low) || !sub(low, offset_.upper, low) || !sub(low, uncertainty, low) ||
        !sub(r, anchor_, high) || !sub(high, offset_.lower, high) || !add(high, uncertainty, high))
        return {invalidate(ClockError::arithmetic_overflow), std::nullopt};
    const auto ppm = config_.relative_drift_ppm;
    if (!scale(low, low < 0 ? 1000000 - ppm : 1000000 + ppm, false, low) ||
        !scale(high, high < 0 ? 1000000 + ppm : 1000000 - ppm, true, high))
        return {invalidate(ClockError::arithmetic_overflow), std::nullopt};
    I local_low, local_high;
    if (!add(anchor_, low, local_low) || !add(anchor_, high, local_high))
        return {invalidate(ClockError::arithmetic_overflow), std::nullopt};
    Interval age;
    if (!sub(n, local_high, age.lower) || !sub(age.lower, uncertainty, age.lower) ||
        !sub(n, local_low, age.upper) || !add(age.upper, uncertainty, age.upper))
        return {invalidate(ClockError::arithmetic_overflow), std::nullopt};
    if (age.upper < 0) return {ClockError::future_sample, std::nullopt};
    age.lower = std::max<I>(0, age.lower); // Causality, not a substitute for an unknown clock.
    error_ = ClockError::none;
    return {ClockError::none, age};
}
std::optional<std::uint64_t> ClockMapper::qualification_deadline() const noexcept {
    if(invalid_||!observed_||error_!=ClockError::none)return std::nullopt;
    I width;if(!sub(offset_.upper,offset_.lower,width)||width<0||std::uint64_t(width)>config_.max_offset_width_ns)return std::nullopt;
    std::uint64_t low=0,high=config_.max_probe_age_ns;
    while(low<high){const auto mid=low+(high-low+1)/2;const auto change=drift(static_cast<I>(mid),config_.relative_drift_ppm);
        if(std::uint64_t(width+2*change)<=config_.max_offset_width_ns)low=mid;else high=mid-1;}
    const auto anchor=std::uint64_t(anchor_);return anchor>std::uint64_t(max)-low?std::uint64_t(max):anchor+low;
}
std::optional<Interval> ClockMapper::offset_at_probe() const noexcept {
    if (invalid_ || !observed_) return std::nullopt;
    return offset_;
}
}
