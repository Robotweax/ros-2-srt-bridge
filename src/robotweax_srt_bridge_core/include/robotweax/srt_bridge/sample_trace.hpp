#pragma once
#include <robotweax/srt_bridge/wire.hpp>
#include <array>
#include <atomic>
#include <stdexcept>

namespace robotweax::srt_bridge {
enum class SampleTraceLane : unsigned { ros=0,transport=1 };
enum class SampleTracePoint : unsigned { admission=1,sdk_accepted=2,sdk_error=3 };
struct SampleTraceEvent {
    std::uint64_t sequence=0,begin_ns=0,end_ns=0,origin_ns=0;
    Identity owner_epoch{},session{};
    std::uint64_t control_generation=0,sensor_generation=0,envelope_sequence=0,callback_sequence=0;
    std::uint32_t route=0,bytes=0,stamp_nanosec=0;
    std::int32_t stamp_sec=0,message_number=0,initial_sequence=-1;
    std::int64_t socket=-1;
    unsigned point=0,result=0,kind=0;
    bool initial_sequence_available=false;
};
// Exactly one ROS executor producer, one transport owner producer, one consumer.
// Other submit_sample callers do not write the ROS lane. No callbacks, payloads,
// allocation, mutex acquisition or retry here. Cross-lane sequence is not causality.
class SampleTrace {
public:
    static constexpr std::size_t lane_capacity=128,capacity=2*lane_capacity;
    static constexpr std::uint64_t default_limit=75000;
    explicit SampleTrace(std::uint64_t limit=default_limit):limit_(limit){
        if(!limit||limit>default_limit)throw std::invalid_argument("sample trace limit");
    }
    void record(SampleTraceLane producer,SampleTraceEvent event){
        const auto next=attempted_.fetch_add(1);
        if(next>=limit_){exhausted_=true;return;}
        event.sequence=next+1;
        auto& lane=lanes_[static_cast<unsigned>(producer)];
        const auto tail=lane.tail.load(std::memory_order_relaxed);
        if(tail-lane.head.load(std::memory_order_acquire)>=lane_capacity){++dropped_;return;}
        lane.events[tail%lane_capacity]=event;lane.tail.store(tail+1,std::memory_order_release);
    }
    bool poll(SampleTraceEvent& event){
        for(unsigned n=0;n<2;++n){const auto index=(cursor_+n)%2;auto& lane=lanes_[index];
            const auto head=lane.head.load(std::memory_order_relaxed);
            if(head==lane.tail.load(std::memory_order_acquire))continue;
            event=lane.events[head%lane_capacity];lane.head.store(head+1,std::memory_order_release);cursor_=(index+1)%2;return true;
        }
        return false;
    }
    std::uint64_t attempted()const{return attempted_.load();}
    std::uint64_t dropped()const{return dropped_.load();}
    bool exhausted()const{return exhausted_.load();}
    std::uint64_t limit()const{return limit_;}
private:
    struct Lane {std::array<SampleTraceEvent,lane_capacity> events{};std::atomic<std::uint64_t> head{0},tail{0};};
    std::array<Lane,2> lanes_{};unsigned cursor_=0;
    const std::uint64_t limit_;
    std::atomic<std::uint64_t> attempted_{0},dropped_{0};std::atomic<bool> exhausted_{false};
};
}
