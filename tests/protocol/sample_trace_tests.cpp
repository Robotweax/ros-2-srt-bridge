#include <robotweax/srt_bridge/sample_trace.hpp>
#include <iostream>
#include <set>
#include <thread>
#include <vector>
using namespace robotweax::srt_bridge;
void check(bool value){if(!value)throw std::runtime_error("sample trace contract");}
int main(){
    SampleTrace queue;SampleTraceEvent event;
    for(unsigned n=0;n<queue.lane_capacity+3;++n){event.callback_sequence=n;queue.record(SampleTraceLane::ros,event);}
    for(unsigned n=0;n<queue.lane_capacity;++n)queue.record(SampleTraceLane::transport,{});
    unsigned count=0;std::set<std::uint64_t> ids;
    while(queue.poll(event)){check(ids.insert(event.sequence).second);++count;}
    check(count==queue.capacity&&queue.dropped()==3&&queue.attempted()==count+3);
    SampleTrace limited(3);for(unsigned n=0;n<5;++n)limited.record(SampleTraceLane::ros,{});
    count=0;while(limited.poll(event))++count;check(count==3&&limited.attempted()==5&&limited.exhausted());
    bool rejected=false;try{SampleTrace invalid(0);}catch(const std::invalid_argument&){rejected=true;}check(rejected);
    SampleTrace concurrent;std::atomic<unsigned> ack[2]{};std::vector<std::thread> producers;
    for(unsigned lane=0;lane<2;++lane)producers.emplace_back([&,lane]{
        for(unsigned n=1;n<=2000;++n){SampleTraceEvent e;e.route=lane;e.callback_sequence=n;concurrent.record(SampleTraceLane(lane),e);
            while(ack[lane].load()<n)std::this_thread::yield();}
    });
    count=0;ids.clear();while(count<4000){if(concurrent.poll(event)){
        check(event.route<2&&event.callback_sequence==ack[event.route].load()+1&&ids.insert(event.sequence).second);
        ack[event.route]=event.callback_sequence;++count;
    }else std::this_thread::yield();}
    for(auto& thread:producers)thread.join();
    check(concurrent.attempted()==4000&&!concurrent.dropped()&&!concurrent.exhausted());
    std::cout<<"PASS sample trace two SPSC lanes, overflow, budget and concurrent FIFO\n";
}
