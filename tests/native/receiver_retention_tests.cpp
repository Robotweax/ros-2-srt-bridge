#include "receiver_retention.hpp"
#include <iostream>
#include <stdexcept>
using namespace robotweax::srt_bridge;
void check(bool ok){if(!ok)throw std::runtime_error("receiver retention invariant failed");}
int main(){try{
    ReceiverRetention queue;TransportMessage m;m.envelope.kind=Kind::command;m.envelope.valid_for_ms=5000;m.envelope.source_monotonic_ns=42;m.envelope.sequence=7;m.size=1;m.payload[0]=std::byte{99};m.context.control_generation=1;
    for(unsigned n=0;n<56;++n){m.envelope.sequence=n+1;check(queue.push(m,100,0,0));}
    check(!queue.push(m,100,0,0)&&queue.size()==56);
    check(!queue.room(8,0)); // All64 control reservations occupied.
    for(unsigned n=0;n<56;++n){check(queue.front().message.envelope.sequence==n+1&&queue.front().message.envelope.source_monotonic_ns==42&&queue.front().message.payload[0]==std::byte{99});check(!queue.expired(5000000099ULL));check(queue.expired(5000000100ULL));queue.pop();}
    check(queue.size()==0);check(!queue.push(m,1,64,0));check(!queue.push(m,1,56,56));
    check(queue.push(m,100,55,55));check(!queue.room(55,55));
    auto c=m.context;++c.sensor_generation;check(queue.matches(c));++c.control_generation;check(!queue.matches(c));
    queue.pop();m.envelope.kind=Kind::query;check(!queue.push(m,100,0,0));m.envelope.kind=Kind::command;
    SampleResult gap;gap.action.error=SessionError::clock_unqualified;gap.age.error=ClockError::expired;check(ReceiverRetention::soft_gap(gap));
    gap.age.error=ClockError::unqualified;check(ReceiverRetention::soft_gap(gap));
    gap.age.error=ClockError::future_sample;check(!ReceiverRetention::soft_gap(gap));
    gap.age.error=ClockError::clock_regressed;check(!ReceiverRetention::soft_gap(gap));
    gap.action.error=SessionError::stale_sample;check(!ReceiverRetention::soft_gap(gap));
    std::cout<<"RECEIVER_RETENTION_CONTRACT {\"capacity\":56,\"total_capacity\":64,\"fifo_original_bytes_context\":true,\"resource_ceiling_not_renewed\":true,\"sensor_only_context_preserved\":true,\"future_hard_errors_excluded\":true}\n";
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}}
