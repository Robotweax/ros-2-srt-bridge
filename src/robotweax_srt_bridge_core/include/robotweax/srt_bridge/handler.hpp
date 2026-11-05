#pragma once
#include <robotweax/srt_bridge/journal.hpp>
namespace robotweax::srt_bridge {
struct HandlerSnapshot {RateResult device{};std::uint64_t effects=0;};
struct HandlerOutcome {
    CommandState state=CommandState::unknown;
    CommandReason reason=CommandReason::effect_uncertain;
    RateResult result{};
};
// Runs only in the supervised exec child, after atomic start authorization.
// deadline_ns is this host's monotonic start deadline, not a remote ROS clock.
// A sent request with an unobserved outcome must return UNKNOWN, never FAILED.
class RateHandlerBackend {
public:
    virtual ~RateHandlerBackend()=default;
    virtual void initialize()=0;
    virtual HandlerOutcome execute(const JournalEntry& entry,std::uint64_t deadline_ns)=0;
    virtual HandlerSnapshot snapshot()const noexcept=0;
};
// Reusable private worker protocol entry point; an external backend is enabled
// only when the parent explicitly requests external_rate_handler. No ROS in SDK.
int run_journal_worker(int argc,char** argv,RateHandlerBackend* external=nullptr);
}
