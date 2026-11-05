#pragma once
#include <array>
#include <algorithm>
#include <cstdint>
#include <limits>

namespace robotweax::ros_bridge {
// All authorized publications, including startup/reconnect. Buckets round the
// conservative age upper bound UP to milliseconds; no unbounded sample history.
class PublicationMetrics {
public:
    std::array<std::uint64_t,251> age_upper_ms{};
    std::uint64_t count=0,maximum_ns=0;
    bool observe(std::uint64_t upper_ns) noexcept {
        if(upper_ns>250000000 || count==std::numeric_limits<std::uint64_t>::max())return false;
        const auto bucket=(upper_ns+999999)/1000000;
        ++age_upper_ms[bucket];++count;maximum_ns=std::max(maximum_ns,upper_ns);return true;
    }
};
}
