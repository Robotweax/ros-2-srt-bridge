#pragma once
#include <cstdint>
#include <limits>

namespace robotweax::srt_bridge_demo {
// Preserve phase across late timer callbacks. Skip missed slots rather than
// emitting catch-up bursts or drifting the next deadline by callback lateness.
inline bool periodic_due(std::uint64_t& next,std::uint64_t now,std::uint64_t period) noexcept {
    constexpr auto maximum=std::numeric_limits<std::uint64_t>::max();
    if(!period||next==maximum||now<next)return false;
    const auto advance=period-(now-next)%period;
    next=advance>maximum-now?maximum:now+advance;
    return true;
}
}
