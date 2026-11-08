#pragma once
#include <robotweax/srt_bridge/transport.hpp>
#include <limits>

namespace robotweax::srt_bridge {
// Transport-owner only. Ready inbox + retained frames share the logical64/56
// budget. A local resource ceiling never replaces the immutable source budget.
class ReceiverRetention {
public:
    static constexpr std::size_t control_capacity=64,command_capacity=56;
    struct Held {TransportMessage message{};std::uint64_t until_ns=0;};
    static bool soft_gap(const SampleResult& result){return !result.envelope&&result.action.error==SessionError::clock_unqualified&&
        (result.age.error==ClockError::expired||result.age.error==ClockError::unqualified);}
    static std::optional<std::uint64_t> expiry_deadline(const Envelope& envelope,const SampleResult& result){
        if(envelope.kind!=Kind::command||!envelope.valid_for_ms||result.envelope||result.action.error!=SessionError::stale_sample||
           result.age.error!=ClockError::none||!result.age.age_ns||!result.evaluated_ns)return {};
        const auto age=*result.age.age_ns;const auto budget=std::uint64_t(envelope.valid_for_ms)*1000000;
        if(age.lower<0||age.lower>age.upper||std::uint64_t(age.lower)<=budget)return {};
        const auto over=std::uint64_t(age.lower)-budget;
        if(over>=result.evaluated_ns)return {};
        return result.evaluated_ns-over; // Latest possible past deadline; expiry-only, never execution.
    }
    static bool ambiguous(const Envelope& envelope,const SampleResult& result){
        if(envelope.kind!=Kind::command||result.envelope||result.action.error!=SessionError::stale_sample||result.age.error!=ClockError::none||!result.age.age_ns)return false;
        const auto age=*result.age.age_ns;const auto budget=std::uint64_t(envelope.valid_for_ms)*1000000;
        return age.lower<=age.upper&&age.upper>=0&&age.lower<=std::int64_t(budget)&&std::uint64_t(age.upper)>budget;
    }
    bool room(std::size_t ready,std::size_t commands)const{
        return ready<control_capacity&&commands<=ready&&commands<command_capacity&&size_<command_capacity&&
            ready+size_<control_capacity&&commands+size_<command_capacity;
    }
    bool push(const TransportMessage& message,std::uint64_t now,std::size_t ready,std::size_t commands){
        const auto duration=std::uint64_t(message.envelope.valid_for_ms)*1000000;
        if(!room(ready,commands)||message.envelope.kind!=Kind::command||!duration||message.size>message.payload.size()||now>std::numeric_limits<std::uint64_t>::max()-duration)return false;
        entries_[(head_+size_)%entries_.size()]={message,now+duration};++size_;return true;
    }
    std::size_t size()const{return size_;}
    const Held& front()const{return entries_[head_];} // Requires size()>0.
    bool expired(std::uint64_t now)const{return size_&&now>=front().until_ns;}
    bool matches(const TransportContext& context)const{return size_&&front().message.context.session==context.session&&front().message.context.control_generation==context.control_generation;}
    void pop(){if(size_){entries_[head_]={};head_=(head_+1)%entries_.size();--size_;}}
private:
    std::array<Held,command_capacity> entries_{};std::size_t head_=0,size_=0;
};
}
