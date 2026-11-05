#include <robotweax/srt_bridge/reconnect.hpp>
#include <algorithm>
#include <limits>

namespace robotweax::srt_bridge {
namespace {constexpr std::uint64_t initial=250000000,maximum=5000000000,campaign=60000000000,timeout=3000000000,
    max_time=std::numeric_limits<std::int64_t>::max();}
bool ReconnectPlan::advance(std::uint64_t now) noexcept {
    if(now<last_time_||now>max_time-campaign){state_=RetryState::failed;return false;}
    last_time_=now;return true;
}
std::uint64_t ReconnectPlan::delay() noexcept {
    // SplitMix64 decorrelation, defined unsigned wrap; deterministic across platforms.
    auto value=(random_+=0x9e3779b97f4a7c15ULL);
    value=(value^(value>>30))*0xbf58476d1ce4e5b9ULL;
    value=(value^(value>>27))*0x94d049bb133111ebULL;value^=value>>31;
    const auto low=std::max(initial,base_-base_/5),high=std::min(maximum,base_+base_/5);
    return low+value%(high-low+1);
}
RetryAction ReconnectPlan::start(std::uint64_t now){
    if(!advance(now))return {RetryError::invalid_time};
    base_=initial;campaign_deadline_=now+campaign;next_=now+delay();state_=RetryState::waiting;
    return {RetryError::none,false,false,0,next_};
}
RetryAction ReconnectPlan::activate(std::uint64_t now){
    if(state_==RetryState::waiting||state_==RetryState::connecting||state_==RetryState::connected)return {RetryError::invalid_state};
    return start(now);
}
RetryAction ReconnectPlan::connection_lost(std::uint64_t connection_id,std::uint64_t now){
    if(state_!=RetryState::connected||connection_id!=id_)return {RetryError::stale_attempt};
    return start(now);
}
RetryAction ReconnectPlan::failed_attempt(std::uint64_t now){
    if(now>=campaign_deadline_){state_=RetryState::exhausted;return {RetryError::exhausted,false,true,id_};}
    base_=std::min(maximum,base_*2);next_=std::min(campaign_deadline_,now+delay());state_=RetryState::waiting;
    return {RetryError::none,false,true,id_,next_};
}
RetryAction ReconnectPlan::poll(std::uint64_t now){
    if(state_!=RetryState::waiting&&state_!=RetryState::connecting)return {};
    const bool owned=state_==RetryState::connecting;
    if(!advance(now))return {RetryError::invalid_time,false,owned,id_};
    if(now>=campaign_deadline_){state_=RetryState::exhausted;return {RetryError::exhausted,false,owned,id_};}
    if(owned){
        if(now>=attempt_deadline_){auto action=failed_attempt(now);if(action.error==RetryError::none)action.error=RetryError::timeout;return action;}
        return {RetryError::none,false,false,id_,attempt_deadline_};
    }
    if(now<next_)return {RetryError::none,false,false,0,next_};
    if(id_==std::numeric_limits<std::uint64_t>::max()){state_=RetryState::failed;return {RetryError::sequence_exhausted};}
    ++id_;state_=RetryState::connecting;attempt_deadline_=std::min(campaign_deadline_,now+timeout);
    return {RetryError::none,true,false,id_,attempt_deadline_};
}
RetryAction ReconnectPlan::complete(std::uint64_t attempt,std::uint64_t now,RetryOutcome result){
    if(state_!=RetryState::connecting||attempt!=id_)return {RetryError::stale_attempt};
    if(!advance(now))return {RetryError::invalid_time,false,true,id_};
    if(now>=campaign_deadline_){state_=RetryState::exhausted;return {RetryError::exhausted,false,true,id_};}
    if(now>=attempt_deadline_){auto action=failed_attempt(now);if(action.error==RetryError::none)action.error=RetryError::timeout;return action;}
    if(result==RetryOutcome::connected){state_=RetryState::connected;return {RetryError::none,false,false,id_};}
    if(result==RetryOutcome::permanent_failure)return permanent_failure();
    if(result!=RetryOutcome::transient_failure)return permanent_failure();
    return failed_attempt(now);
}
RetryAction ReconnectPlan::cancel() noexcept {
    const bool owned=state_==RetryState::connecting||state_==RetryState::connected;
    state_=RetryState::cancelled;return {RetryError::none,false,owned,id_};
}
RetryAction ReconnectPlan::permanent_failure() noexcept {
    const bool owned=state_==RetryState::connecting||state_==RetryState::connected;
    state_=RetryState::failed;return {RetryError::permanent_failure,false,owned,id_};
}
}
