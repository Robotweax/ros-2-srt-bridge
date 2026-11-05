#include <robotweax/srt_bridge/bandwidth.hpp>
#include <algorithm>
#include <limits>
#include <stdexcept>

namespace robotweax::srt_bridge {
namespace {
constexpr std::uint64_t units=1000000000,max_time=std::numeric_limits<std::int64_t>::max();
std::uint64_t ceil_div(std::uint64_t value,std::uint64_t denominator){return value/denominator+(value%denominator!=0);}
void refill(std::uint64_t& credits,std::uint64_t capacity,std::uint64_t rate,std::uint64_t elapsed){
    const auto missing=capacity-credits;
    if(elapsed>=ceil_div(missing,rate))credits=capacity;else credits+=elapsed*rate;
}
}
std::uint64_t estimated_wire_bytes(Channel channel,std::size_t size) noexcept {
    if(size<envelope_bytes||(channel==Channel::control?size>4096:channel!=Channel::sensor||size>1024))return 0;
    if(channel==Channel::control)return 2*(size+80*((size+1023)/1024)); // data plus one nominal retry allowance
    return size+80+287; // IPv6/UDP/SRT/GCM plus 1/4 of maximum authenticated parity
}
BandwidthBudget::BandwidthBudget(BandwidthConfig config,std::uint64_t now):config_(config),
    total_(config.burst_bytes*units),sensor_(config.sensor_burst_bytes*units),last_time_(now){
    if(!config.total_bytes_per_second||config.total_bytes_per_second>1000000000||
       !config.control_reserved_bytes_per_second||config.control_reserved_bytes_per_second>=config.total_bytes_per_second||
       config.burst_bytes>4194304||config.sensor_burst_bytes>4194304||
       config.control_reserved_burst_bytes<estimated_wire_bytes(Channel::control,4096)||
       config.control_reserved_burst_bytes>config.burst_bytes||
       config.burst_bytes-config.control_reserved_burst_bytes<estimated_wire_bytes(Channel::sensor,1024)||
       config.sensor_burst_bytes<estimated_wire_bytes(Channel::sensor,1024)||now>max_time)
        throw std::invalid_argument("invalid bandwidth admission bounds");
}
BudgetPermit BandwidthBudget::reserve(Channel channel,std::size_t size,std::uint64_t now){
    if(invalid_||now<last_time_||now>max_time){invalid_=true;return {BudgetError::invalid_time};}
    if(pending_id_)return {BudgetError::busy};
    const auto elapsed=now-last_time_;last_time_=now;
    refill(total_,config_.burst_bytes*units,config_.total_bytes_per_second,elapsed);
    refill(sensor_,config_.sensor_burst_bytes*units,config_.total_bytes_per_second-config_.control_reserved_bytes_per_second,elapsed);
    const auto cost=estimated_wire_bytes(channel,size);if(!cost)return {BudgetError::oversize};
    const auto required=(cost+(channel==Channel::sensor?config_.control_reserved_burst_bytes:0))*units;
    if(required>config_.burst_bytes*units||(channel==Channel::sensor&&cost>config_.sensor_burst_bytes))return {BudgetError::impossible};
    std::uint64_t wait=total_>=required?0:ceil_div(required-total_,config_.total_bytes_per_second);
    if(channel==Channel::sensor&&sensor_<cost*units)wait=std::max(wait,ceil_div(cost*units-sensor_,config_.total_bytes_per_second-config_.control_reserved_bytes_per_second));
    if(wait){if(now>max_time-wait){invalid_=true;return {BudgetError::invalid_time};}return {BudgetError::rate_limited,0,cost,now+wait};}
    if(next_id_==std::numeric_limits<std::uint64_t>::max())return {BudgetError::sequence_exhausted};
    pending_id_=++next_id_;pending_cost_=cost*units;pending_channel_=channel;
    total_-=pending_cost_;if(channel==Channel::sensor)sensor_-=pending_cost_;
    return {BudgetError::none,pending_id_,cost,now};
}
bool BandwidthBudget::finish(std::uint64_t id,bool accepted) noexcept{
    if(!id||id!=pending_id_)return false;
    if(!accepted){total_+=pending_cost_;if(pending_channel_==Channel::sensor)sensor_+=pending_cost_;}
    pending_id_=pending_cost_=0;return true;
}
}
