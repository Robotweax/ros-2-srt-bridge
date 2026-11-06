#include <robotweax/srt_bridge/command_trace.hpp>
#include <thread>
#include <vector>
#include <set>
#include <iostream>
#include <stdexcept>
using namespace robotweax::srt_bridge;
void check(bool b){if(!b)throw std::runtime_error("trace storage contract failed");}
int main(){
    CommandTrace trace;CommandTraceEvent event;
    for(unsigned n=0;n<CommandTrace::capacity+7;++n){event.monotonic_ns=n;trace.record(event);}
    check(trace.attempted()==CommandTrace::capacity+7&&trace.dropped()==7);
    for(unsigned n=0;n<CommandTrace::capacity;++n){check(trace.poll(event));check(event.monotonic_ns==n&&event.sequence==n+1);}
    check(!trace.poll(event));trace.record({});check(trace.poll(event));
    // Concurrent producers preserve exact accepted+dropped accounting, unique
    // sequence identities and fixed capacity even without an active consumer.
    CommandTrace concurrent;std::vector<std::thread> producers;
    for(unsigned n=0;n<4;++n)producers.emplace_back([&]{for(unsigned i=0;i<1000;++i)concurrent.record({});});
    for(auto& thread:producers)thread.join();
    std::set<std::uint64_t> sequences;unsigned count=0;
    while(concurrent.poll(event)){check(sequences.insert(event.sequence).second);++count;}
    check(count<=CommandTrace::capacity&&count+concurrent.dropped()==4000&&concurrent.attempted()==4000);
    std::cout<<"bounded trace overflow/concurrency accounting passed\n";
}
