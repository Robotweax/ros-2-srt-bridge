// Counterfactual recorded-time checks against the unchanged production Pool.
// Does not send commands, invoke handlers, install binaries or alter policy.
#include "../../src/robotweax_srt_bridge_core/src/worker/execution_pool.hpp"
#include <charconv>
#include <iostream>
#include <stdexcept>
#include <string_view>
using namespace robotweax::srt_bridge;
using namespace robotweax::srt_bridge::execution_detail;
namespace {
void require(bool ok,const char* msg){if(!ok)throw std::runtime_error(msg);}
uint64_t number(const char* text){std::string_view s(text);uint64_t n=0;auto r=std::from_chars(s.data(),s.data()+s.size(),n);require(r.ec==std::errc{}&&r.ptr==s.data()+s.size()&&n,"positive uint64 required");return n;}
const char* name(Start s){switch(s){case Start::started:return "started";case Start::expired:return "expired";case Start::revoked:return "revoked";case Start::invalid:return "invalid";}return "unavailable";}
struct Fixture {
 std::shared_ptr<Pool> pool=Pool::create();std::shared_ptr<Record> record;
 Fixture(uint64_t command_deadline,uint64_t grant_deadline){JournalEntry e;e.request_id[0]=std::byte{34};e.payload_hash[0]=std::byte{42};e.route=100;e.command={200,5000,33,34};e.context.deadline_ns=command_deadline;record=pool->allocate(e,"synthetic-robot","synthetic-operator",std::make_shared<std::atomic<bool>>(true));require(bool(record),"allocation");require(pool->grant(*record,grant_deadline),"grant");}
 Start consume(uint64_t time){return pool->consume(record->slot,record->generation,record->entry.request_id,record->entry.payload_hash,time);}
 ~Fixture(){if(pool->state(*record)==State::running)pool->complete(record->slot,record->generation);}
};
}
int main(int argc,char**argv){try{
 require(argc==5,"usage: start_fence_probe COMMAND_DEADLINE OBSERVED_CLOCK_DEADLINE DISPATCH FINISH");const auto command=number(argv[1]),lease=number(argv[2]),dispatch=number(argv[3]),finish=number(argv[4]);require(lease>1&&lease<dispatch&&dispatch<finish&&finish<command,"recorded clock-lapse scenario required");
 bool first=true;unsigned checks=0;std::cout<<"{\"scope\":\"counterfactual supplied timestamps; not historical grant or live command replay\",\"cases\":[";
 auto emit=[&](const char* label,Start result,Start expected,uint64_t time){require(result==expected,"pool result mismatch");++checks;if(!first)std::cout<<",";first=false;std::cout<<"{\"case\":\""<<label<<"\",\"pool_result\":\""<<name(result)<<"\",\"evaluated_ns\":"<<time<<",\"original_budget_elapsed\":"<<(time>=command?"true":"false")<<"}";};
 {Fixture f(command,lease);emit("one_ns_before_observed_lease",f.consume(lease-1),Start::started,lease-1);}
 {Fixture f(command,lease);emit("at_observed_lease",f.consume(lease),Start::expired,lease);}
 {Fixture f(command,lease);emit("historical_dispatch_with_unrenewed_lease",f.consume(dispatch),Start::expired,dispatch);}
 {Fixture f(command,lease);f.pool->revoke(*f.record);emit("revoked_before_lease",f.consume(lease-1),Start::revoked,lease-1);}
 {Fixture f(command,lease);auto h=f.record->entry.payload_hash;h[1]=std::byte{1};emit("invalid_payload_identity",f.pool->consume(f.record->slot,f.record->generation,f.record->entry.request_id,h,lease-1),Start::invalid,lease-1);}
 {Fixture f(command,command);emit("fresh_replacement_grant_at_same_dispatch",f.consume(dispatch),Start::started,dispatch);}
 {Fixture f(command,lease);emit("consume_before_lease_second_gate_after",f.consume(lease-1),Start::started,lease-1);require(dispatch>=f.pool->deadline(*f.record),"second pre-handler gate did not expire");++checks;}
 {Fixture f(command,command);emit("at_original_command_deadline",f.consume(command),Start::expired,command);}
 std::cout<<"],\"second_gate_expired_while_original_budget_live\":true,\"checks\":"<<checks<<",\"passed\":true}\n";return 0;
 }catch(const std::exception&e){std::cerr<<e.what()<<"\n";return 1;}}
