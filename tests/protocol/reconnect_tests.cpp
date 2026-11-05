#include <robotweax/srt_bridge/reconnect.hpp>
#include <iostream>
#include <limits>
#include <stdexcept>
using namespace robotweax::srt_bridge;
namespace {
unsigned checks=0;void check(bool b,const char* m){++checks;if(!b)throw std::runtime_error(m);}
void contract(){
    ReconnectPlan plan(42);auto action=plan.activate(0);check(action.wake_ns&&*action.wake_ns>=250000000&&*action.wake_ns<=300000000,"initial jitter");
    check(plan.activate(0).error==RetryError::invalid_state,"active campaign restarted");
    check(!plan.poll(*action.wake_ns-1).connect,"early connect");
    action=plan.poll(*action.wake_ns);check(action.connect&&action.attempt==1,"first attempt");
    const auto first=action.attempt;
    check(!plan.poll(*action.wake_ns-1).connect,"parallel attempt");
    action=plan.complete(first,*action.wake_ns,RetryOutcome::connected);
    check(action.error==RetryError::timeout&&action.close,"late completion bypassed timeout");
    action=plan.poll(*action.wake_ns);check(action.connect&&action.attempt==2,"retry attempt");
    check(plan.complete(first,0,RetryOutcome::connected).error==RetryError::stale_attempt,"old completion poisoned new time");
    check(plan.cancel().close&&plan.state()==RetryState::cancelled,"cancel did not close pending socket");
    check(plan.complete(action.attempt,10000000000,RetryOutcome::connected).error==RetryError::stale_attempt,"cancelled attempt revived");
    check(!plan.poll(60000000000).connect,"cancelled timer fired");
    ReconnectPlan success(1);action=success.activate(0);action=success.poll(*action.wake_ns);
    check(success.complete(action.attempt,300000000,RetryOutcome::connected).error==RetryError::none&&success.state()==RetryState::connected,"successful attempt");
    check(success.connection_lost(99,0).error==RetryError::stale_attempt&&success.state()==RetryState::connected,"stale close killed current connection");
    action=success.connection_lost(1,1000000000);check(action.wake_ns.has_value(),"new loss did not start campaign");
    action=success.poll(*action.wake_ns);check(success.complete(action.attempt,1400000000,RetryOutcome::permanent_failure).error==RetryError::permanent_failure,"permanent failure");
    check(!success.poll(59000000000).connect&&success.state()==RetryState::failed,"permanent failure auto retried");
    // Every seed reaches the exact campaign cutoff without an attempt at/after it.
    for(unsigned seed=0;seed<1000;++seed){
        ReconnectPlan p(seed),same(seed);auto a=p.activate(0),copy=same.activate(0);check(a.wake_ns==copy.wake_ns,"seed reproducibility");
        std::uint64_t time=*a.wake_ns,previous=0;unsigned attempts=0;
        while(time<60000000000ULL){
            a=p.poll(time);check(a.connect&&a.attempt>previous,"attempt did not advance");previous=a.attempt;++attempts;
            a=p.complete(a.attempt,time,RetryOutcome::transient_failure);
            check(a.close&&a.wake_ns&&(*a.wake_ns>=time+250000000||*a.wake_ns==60000000000ULL),"retry delay missing");
            check(*a.wake_ns<=time+5000000000||*a.wake_ns==60000000000ULL,"jitter exceeded cap");time=*a.wake_ns;
        }
        a=p.poll(60000000000ULL);check(a.error==RetryError::exhausted&&!a.connect&&attempts<40,"campaign did not terminate");
        check(!p.poll(70000000000ULL).connect,"exhausted campaign restarted itself");
    }
    ReconnectPlan cutoff(5);action=cutoff.activate(0);action=cutoff.poll(*action.wake_ns);
    check(cutoff.poll(60000000000ULL).close&&cutoff.state()==RetryState::exhausted,"cutoff left socket alive");
    ReconnectPlan regression(1);action=regression.activate(100);action=regression.poll(*action.wake_ns);
    check(regression.complete(action.attempt,0,RetryOutcome::connected).error==RetryError::invalid_time,"clock regressed");
    ReconnectPlan huge(1);check(huge.activate(std::numeric_limits<std::uint64_t>::max()).error==RetryError::invalid_time,"deadline overflow");
}
}
int main(){try{contract();std::cout<<"PASS reconnect contract: "<<checks<<" checks, 1000 seeded campaigns\n";}
catch(const std::exception& e){std::cerr<<"FAIL: "<<e.what()<<'\n';return 1;}}
