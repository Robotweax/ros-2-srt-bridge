#include <robotweax/srt_bridge/bandwidth.hpp>
#include <iostream>
#include <limits>
#include <stdexcept>
using namespace robotweax::srt_bridge;
namespace {
unsigned checks=0;void check(bool b,const char* m){++checks;if(!b)throw std::runtime_error(m);}
BandwidthConfig config(){return {64000,16000,16384,8832,7552};}
void contract(){
    check(estimated_wire_bytes(Channel::control,4096)==8832,"CONTROL estimate");
    check(estimated_wire_bytes(Channel::sensor,1024)==1391,"SENSOR estimate");
    BandwidthBudget b(config(),0);const auto initial=b.available_total_bytes();
    auto p=b.reserve(Channel::sensor,1024,0);check(bool(p),"initial burst");
    check(b.reserve(Channel::control,4096,0).error==BudgetError::busy,"overlapping permits");
    check(!b.finish(p.id+1,false),"wrong refund accepted");check(b.finish(p.id,false),"refund failed");
    check(b.available_total_bytes()==initial&&!b.finish(p.id,false),"refund minted credits");
    unsigned samples=0;
    while((p=b.reserve(Channel::sensor,1024,0))){check(b.finish(p.id,true),"sample commit");++samples;}
    check(samples>0&&p.error==BudgetError::rate_limited,"sensor burst was not bounded");
    check(b.available_total_bytes()>=8832,"sensor consumed reserved CONTROL credits");
    auto c=b.reserve(Channel::control,4096,0);check(bool(c)&&b.finish(c.id,true),"CONTROL starved behind sensors");
    p=b.reserve(Channel::sensor,1024,0);check(p.error==BudgetError::rate_limited&&p.retry_at_ns>0,"no retry time");
    const auto retry=p.retry_at_ns;
    check(b.reserve(Channel::sensor,1024,retry-1).error==BudgetError::rate_limited,"early fractional refill");
    p=b.reserve(Channel::sensor,1024,retry);check(bool(p)&&b.finish(p.id,true),"exact refill deadline failed");
    check(b.reserve(Channel::control,4097,retry).error==BudgetError::oversize,"oversize granted");
    check(b.reserve(Channel::sensor,1024,retry-1).error==BudgetError::invalid_time,"clock regression");
    check(b.reserve(Channel::control,96,retry+1000000000).error==BudgetError::invalid_time,"invalid clock recovered silently");
    // Long steady overload cannot exceed initial burst plus replenished estimate.
    BandwidthBudget stream(config(),0);std::uint64_t accepted=0;
    for(std::uint64_t time=0;time<=10000000000ULL;time+=1000000){
        const auto channel=time%100000000==0?Channel::control:Channel::sensor;
        auto permit=stream.reserve(channel,channel==Channel::control?4096:1024,time);
        if(permit){accepted+=permit.estimated_bytes;check(stream.finish(permit.id,true),"stream commit");}
        else check(permit.error==BudgetError::rate_limited,"unexpected overload result");
        check(accepted<=16384+(time/1000000)*64,"admission exceeded total budget");
    }
    for(auto bad:{BandwidthConfig{0,0,1,1,1},{64000,64000,16384,8832,7552},{64000,1,1,1,1},
                 {64000,1,std::numeric_limits<std::uint64_t>::max(),8832,7552}}){
        bool threw=false;try{BandwidthBudget invalid(bad,0);}catch(const std::invalid_argument&){threw=true;}check(threw,"invalid config");
    }
}
}
int main(){try{contract();std::cout<<"PASS bandwidth contract: "<<checks<<" checks, 10s synthetic overload\n";}
catch(const std::exception& e){std::cerr<<"FAIL: "<<e.what()<<'\n';return 1;}}
