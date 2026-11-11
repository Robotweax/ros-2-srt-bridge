#pragma once
#include <robotweax/srt_bridge/commands.hpp>
#include <atomic>
#include <array>
#include <stdexcept>

namespace robotweax::srt_bridge {
// unavailable: 0 available, 1 no socket, 2 not ready, 3 statistics API failure.
// Only available fields are evidence; zero RTT need not be a latency estimate.
struct ProviderObservation {
    std::uint64_t sequence=0,begin_ns=0,end_ns=0,generation=0;
    Identity owner_epoch{},session{};
    std::int64_t socket=-1;
    unsigned channel=0; // 0 CONTROL, 1 SENSOR; streams have independent budgets.
    unsigned state_before=0,state_after=0,unavailable=1;
    int error=0,idle_timeout_ms=0;
    bool available=false,idle_timeout_available=false,before_close=false;
    std::int64_t data_sent=0,data_received=0,retransmitted=0;
    std::int64_t ack_sent=0,ack_received=0,nak_sent=0,nak_received=0,undecrypt=0;
    std::uint64_t bytes_sent=0,bytes_received=0;
    int send_buffer_packets=0,send_buffer_bytes=0,receive_buffer_packets=0,receive_buffer_bytes=0,flight_packets=0;
    double rtt_ms=0;
    // Pinned srt_bstats totals; aggregate drops are not reason-specific events.
    std::int64_t unique_sent=0,unique_received=0,sender_loss=0,receiver_loss=0,sender_drop=0,receiver_drop=0;
    std::int64_t sender_filter_extra=0,receiver_filter_extra=0,receiver_filter_supply=0,receiver_filter_loss=0;
    int flow_window_packets=0,congestion_window_packets=0;
};
// One transport producer and one external consumer. Independent of command
// trace storage. Full/record-budget losses remain explicit, never affect policy.
class ProviderDiagnostics {
public:
    static constexpr std::size_t capacity=128;
    static constexpr std::uint64_t default_limit=75000;
    explicit ProviderDiagnostics(std::uint64_t limit=default_limit):limit_(limit){
        if(!limit||limit>default_limit)throw std::invalid_argument("provider diagnostic limit");
    }
    void record(ProviderObservation observation){
        if(attempted_.load()>=limit_){exhausted_=true;return;}
        observation.sequence=++attempted_;
        const auto tail=tail_.load(std::memory_order_relaxed);
        if(tail-head_.load(std::memory_order_acquire)>=capacity){++dropped_;return;}
        rows_[tail%capacity]=observation;tail_.store(tail+1,std::memory_order_release);
    }
    bool poll(ProviderObservation& observation){
        const auto head=head_.load(std::memory_order_relaxed);
        if(head==tail_.load(std::memory_order_acquire))return false;
        observation=rows_[head%capacity];head_.store(head+1,std::memory_order_release);return true;
    }
    std::uint64_t attempted()const{return attempted_.load();}
    std::uint64_t dropped()const{return dropped_.load();}
    std::uint64_t limit()const{return limit_;}
    bool exhausted()const{return exhausted_.load();}
private:
    std::array<ProviderObservation,capacity> rows_{};
    const std::uint64_t limit_;
    std::atomic<std::uint64_t> head_{0},tail_{0},attempted_{0},dropped_{0};
    std::atomic<bool> exhausted_{false};
};
}
