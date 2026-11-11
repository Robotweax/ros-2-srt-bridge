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
    for(unsigned n=0;n<CommandTrace::lane_capacity+7;++n){event.monotonic_ns=n;trace.record(event);}
    check(trace.attempted()==CommandTrace::lane_capacity+7&&trace.dropped()==7);
    for(unsigned n=0;n<CommandTrace::lane_capacity;++n){check(trace.poll(event));check(event.monotonic_ns==n&&event.sequence==n+1);}
    check(!trace.poll(event));trace.record({});check(trace.poll(event));
    // A full coordinator lane cannot consume the transport lane's reservation.
    CommandTrace reserved;
    for(unsigned n=0;n<CommandTrace::lane_capacity+1;++n)reserved.record({});
    for(unsigned n=0;n<CommandTrace::lane_capacity;++n)reserved.record(CommandTraceProducer::transport,{});
    unsigned retained=0;while(reserved.poll(event))++retained;
    check(retained==CommandTrace::capacity&&reserved.dropped()==1);
    // Concurrent owner lanes and a draining consumer preserve per-lane FIFO,
    // unique global sequence IDs and exact accepted+overflow accounting.
    CommandTrace concurrent;std::atomic<unsigned> done{0};std::vector<std::thread> producers;
    for(unsigned lane=0;lane<2;++lane)producers.emplace_back([&,lane]{
        for(unsigned n=1;n<=20000;++n){CommandTraceEvent e;e.route=lane;e.value=n;concurrent.record(CommandTraceProducer(lane),e);}
        ++done;
    });
    std::set<std::uint64_t> sequences;unsigned last[2]={0,0};unsigned count=0;
    auto consume=[&]{check(event.route<2&&event.value>last[event.route]);last[event.route]=event.value;check(sequences.insert(event.sequence).second);++count;};
    while(done.load()!=2){if(concurrent.poll(event))consume();else std::this_thread::yield();}
    for(auto& thread:producers)thread.join();
    while(concurrent.poll(event))consume();
    check(count+concurrent.dropped()==40000&&concurrent.attempted()==40000);
    // Force concurrent drain with at most one outstanding event per lane.
    // Full lanes are impossible here: any loss is an actual storage failure.
    CommandTrace interleaved;std::atomic<unsigned> acknowledged[2]{};
    std::vector<std::thread> owners;
    for(unsigned lane=0;lane<2;++lane)owners.emplace_back([&,lane]{
        for(unsigned n=1;n<=1000;++n){CommandTraceEvent e;e.route=lane;e.value=n;interleaved.record(CommandTraceProducer(lane),e);
            while(acknowledged[lane].load()<n)std::this_thread::yield();
        }
    });
    unsigned drained=0;
    while(drained<2000){if(interleaved.poll(event)){
        check(event.route<2&&event.value==acknowledged[event.route].load()+1);
        acknowledged[event.route].store(event.value);++drained;
    }else std::this_thread::yield();}
    for(auto& owner:owners)owner.join();
    check(interleaved.attempted()==2000&&interleaved.dropped()==0);
    std::cout<<"bounded SPSC lanes, FIFO/overflow/concurrent drain accounting passed\n";
}
