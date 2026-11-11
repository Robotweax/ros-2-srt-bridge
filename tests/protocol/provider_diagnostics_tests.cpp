#include <robotweax/srt_bridge/provider_diagnostics.hpp>
#include <thread>
#include <iostream>
using namespace robotweax::srt_bridge;
void check(bool value){if(!value)throw std::runtime_error("provider diagnostics contract");}
int main(){
    ProviderDiagnostics queue;ProviderObservation o;
    for(unsigned n=0;n<queue.capacity+7;++n){o.begin_ns=n;queue.record(o);}
    check(queue.attempted()==queue.capacity+7&&queue.dropped()==7);
    for(unsigned n=0;n<queue.capacity;++n){check(queue.poll(o));check(o.sequence==n+1&&o.begin_ns==n);}
    check(!queue.poll(o));queue.record({});check(queue.poll(o)&&o.sequence==queue.capacity+8);
    ProviderDiagnostics budget(3);
    for(unsigned n=0;n<5;++n)budget.record({});
    check(budget.attempted()==3&&budget.exhausted()&&budget.dropped()==0);
    unsigned drained=0;while(budget.poll(o))++drained;check(drained==3);
    bool rejected=false;try{ProviderDiagnostics invalid(0);}catch(const std::invalid_argument&){rejected=true;}check(rejected);
    ProviderDiagnostics concurrent;std::atomic<unsigned> acknowledged{0};
    std::thread producer([&]{for(unsigned n=1;n<=10000;++n){ProviderObservation row;row.data_sent=n;concurrent.record(row);
        while(acknowledged.load()<n)std::this_thread::yield();}});
    for(unsigned n=1;n<=10000;++n){while(!concurrent.poll(o))std::this_thread::yield();check(o.sequence==n&&o.data_sent==n);acknowledged=n;}
    producer.join();check(concurrent.attempted()==10000&&concurrent.dropped()==0&&!concurrent.exhausted());
    std::cout<<"PASS provider bounded SPSC FIFO, overflow, budget and concurrent drain\n";
}
