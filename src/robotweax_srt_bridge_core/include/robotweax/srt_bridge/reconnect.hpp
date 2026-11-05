#pragma once
#include <cstdint>
#include <optional>

namespace robotweax::srt_bridge {
enum class RetryState { idle, waiting, connecting, connected, exhausted, failed, cancelled };
enum class RetryOutcome { connected, transient_failure, permanent_failure };
enum class RetryError { none, invalid_state, stale_attempt, invalid_time, timeout, exhausted, permanent_failure, sequence_exhausted };
struct RetryAction {
    RetryError error=RetryError::none;
    bool connect=false,close=false;
    std::uint64_t attempt=0;
    std::optional<std::uint64_t> wake_ns{};
};
// Cancellable timer state, no sleeps or networking. One plan per channel.
// Seed is for reconnect decorrelation, not cryptographic identity generation.
class ReconnectPlan {
public:
    explicit ReconnectPlan(std::uint64_t seed):random_(seed){}
    RetryAction activate(std::uint64_t now);
    RetryAction connection_lost(std::uint64_t connection_id,std::uint64_t now);
    RetryAction poll(std::uint64_t now);
    RetryAction complete(std::uint64_t attempt,std::uint64_t now,RetryOutcome outcome);
    RetryAction cancel() noexcept;
    RetryAction permanent_failure() noexcept;
    RetryState state() const noexcept{return state_;}
private:
    RetryState state_=RetryState::idle;
    std::uint64_t random_,last_time_=0,campaign_deadline_=0,next_=0,attempt_deadline_=0;
    std::uint64_t base_=250000000,id_=0;
    bool advance(std::uint64_t now) noexcept;
    std::uint64_t delay() noexcept;
    RetryAction start(std::uint64_t now);
    RetryAction failed_attempt(std::uint64_t now);
};
}
