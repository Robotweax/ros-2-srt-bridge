#pragma once
#include <robotweax/srt_bridge/wire.hpp>
#include <cstdint>

namespace robotweax::srt_bridge {
struct BandwidthConfig {
    std::uint64_t total_bytes_per_second,control_reserved_bytes_per_second;
    std::uint64_t burst_bytes,control_reserved_burst_bytes,sensor_burst_bytes;
};
enum class BudgetError { none, busy, invalid_time, oversize, impossible, rate_limited, sequence_exhausted };
struct BudgetPermit {
    BudgetError error=BudgetError::none;
    std::uint64_t id=0,estimated_bytes=0,retry_at_ns=0;
    explicit operator bool() const noexcept{return error==BudgetError::none&&id!=0;}
};
// Estimated application admission only: actual SRT retransmissions, control
// datagrams and kernel buffering require separate measured wire accounting.
std::uint64_t estimated_wire_bytes(Channel channel,std::size_t encoded_bytes) noexcept;
class BandwidthBudget {
public:
    BandwidthBudget(BandwidthConfig config,std::uint64_t now);
    BudgetPermit reserve(Channel channel,std::size_t encoded_bytes,std::uint64_t now);
    // Consume on SRT acceptance; otherwise refund exactly once. No second permit
    // can be issued until the current nonblocking send attempt is resolved.
    bool finish(std::uint64_t permit,bool accepted_by_srt) noexcept;
    std::uint64_t available_total_bytes() const noexcept{return total_/1000000000;}
private:
    BandwidthConfig config_;
    std::uint64_t total_,sensor_,last_time_,next_id_=0,pending_id_=0,pending_cost_=0;
    Channel pending_channel_=Channel::control;
    bool invalid_=false;
};
}
