#include <robotweax/srt_bridge/session.hpp>
#include <robotweax/srt_bridge/journal.hpp>
#include <filesystem>
#include <iostream>
#include <stdexcept>
#include <unistd.h>
using namespace robotweax::srt_bridge;
namespace {
void check(bool ok,const char* message){if(!ok)throw std::runtime_error(message);}
Identity id(unsigned n){Identity value{};value[0]=std::byte(n);return value;}
SessionConfig config(Role role,bool short_clock){
    Route route{100,RouteKind::command,Direction::listener_to_caller,QosMapping::request_status,true,4000,5000,0,1,
        "robotweax.srt_bridge.v1.SetMeasurementRateCommand",rate_command_schema_hash()};
    return {role,role==Role::caller?"robot":"operator",role==Role::caller?"operator":"robot",id(role==Role::caller?1:2),
        role==Role::caller?1U:2U,*make_manifest(std::span(&route,1)).value,{0,0,short_clock?20000000ULL:5000000000ULL,50000000}};
}
struct Pair {
    Session receiver,sender;std::uint64_t time=1000000000;
    explicit Pair(bool short_clock):receiver(config(Role::caller,short_clock)),sender(config(Role::listener,false)){
        const Security security{Channel::control,true,true,true};
        sender.control_connected(11,security,next(),id(10));
        auto hello=receiver.control_connected(1,security,next());
        auto welcome=deliver(sender,hello,11);deliver(receiver,welcome,1);
        auto reply=deliver(sender,receiver.begin_probe(next()),11);auto ready=deliver(receiver,reply,1);deliver(sender,ready,11);
        reply=deliver(receiver,sender.begin_probe(next()),1);ready=deliver(sender,reply,11);deliver(receiver,ready,1);
        check(receiver.state()==SessionState::control_active&&sender.state()==SessionState::control_active,"control handshake failed");
    }
    std::uint64_t next(){return time+=1000000;}
    SessionAction deliver(Session& destination,const SessionAction& action,std::uint64_t generation){
        check(action.send.has_value(),"missing management message");std::array<std::byte,512> payload{};
        auto packed=encode_management(action.send->payload,payload);check(bool(packed),"management encode failed");
        return destination.receive({Channel::control,generation},{action.send->envelope,std::span(payload).first(packed.bytes_written)},next());
    }
};
JournalOptions options(const std::filesystem::path& root,const char* name,JournalSide side){
    JournalOptions o;o.path=(root/name).string();o.side=side;o.local_peer_id=side==JournalSide::sender?"operator":"robot";
    o.remote_peer_id=side==JournalSide::sender?"robot":"operator";o.process_epoch=id(side==JournalSide::sender?2:1);return o;
}
void run(const std::filesystem::path& root,const std::string& kind){
    Pair pair(kind=="expired");const auto request=id(30);const RateCommand command{100,5000,0,1};
    const auto source=pair.time+(kind=="future"?200000000:1000000);
    std::array<std::byte,256> payload{};auto encoded=encode_rate_command(command,payload);check(bool(encoded),"command encode failed");
    auto made=pair.sender.make_control(Kind::command,100,request,encoded.bytes_written,source,source);
    check(made.envelope.has_value(),"sender failed to make command");
    const auto received=pair.time+(kind=="expired"?40000000:2000000);
    auto decision=pair.receiver.admit_control({Channel::control,1},{*made.envelope,std::span(payload).first(encoded.bytes_written)},received);
    if(kind=="control"){
        check(decision.envelope&&decision.action.error==SessionError::none&&decision.age.error==ClockError::none,"positive admission control failed");
        std::cout<<"CLOCK_REJECTION_CONTRACT {\"case\":\"control\",\"admitted\":true}\n";return;
    }
    const auto expected=kind=="expired"?ClockError::expired:ClockError::future_sample;
    check(!decision.envelope&&decision.action.error==SessionError::clock_unqualified&&decision.age.error==expected,"rejection boundary mismatch");
    check(!decision.action.close_control&&!decision.action.close_sensor&&pair.receiver.state()==SessionState::control_active,"soft rejection closed context");
    check(pair.receiver.clock_state()==(kind=="expired"?ClockError::expired:ClockError::none),"clock state did not distinguish future age from expiry");
    auto duplicate=pair.receiver.admit_control({Channel::control,1},{*made.envelope,std::span(payload).first(encoded.bytes_written)},received+1000000);
    check(duplicate.action.error==SessionError::replay&&!duplicate.envelope,"rejected command did not consume receive watermark");
    auto query=pair.sender.make_control(Kind::query,100,request,0,0,source+1000000);check(query.envelope.has_value(),"query creation failed");
    check(pair.receiver.admit_control({Channel::control,1},{*query.envelope,{}},received+2000000).envelope.has_value(),"query incorrectly required clock freshness");
    auto so=options(root,"sender.sqlite",JournalSide::sender);auto ro=options(root,"receiver.sqlite",JournalSide::receiver);
    const CommandContext context{made.envelope->session_id,id(2),source,source+5000000000ULL};
    {
        CommandJournal sender(so),receiver(ro);auto intent=sender.admit(request,100,command,context,source);
        check(intent&&intent.entry->state==CommandState::local_queued,"sender intent not retained");
        check(receiver.get(request).error==JournalError::not_found,"negative fixture admitted receiver entry");
        auto retained=sender.get(request);check(retained.entry->state==CommandState::local_queued&&!retained.entry->result.valid,"NOT_FOUND invented outcome");
        auto repeated=sender.admit(request,100,command,{id(99),id(98),context.deadline_ns+1,context.deadline_ns+5000000001ULL},context.deadline_ns+1);
        check(!repeated.inserted&&repeated.entry->state==CommandState::local_queued&&repeated.entry->context.session==context.session&&repeated.entry->context.source_monotonic_ns==source&&repeated.entry->context.deadline_ns==context.deadline_ns,"elapsed budget/duplicate replaced original intent");
    }
    so.process_epoch=id(90);CommandJournal reopened(so);auto retained=reopened.get(request);
    check(retained.entry&&retained.entry->state==CommandState::unknown&&retained.entry->reason==CommandReason::reconcile_required&&!retained.entry->result.valid,"restart invented negative result");
    check(retained.entry->context.deadline_ns==context.deadline_ns&&!reopened.sender_may_transmit(request,context.session,source+1),"recovered uncertainty authorized transmit");
    std::cout<<"CLOCK_REJECTION_CONTRACT {\"case\":\""<<kind<<"\",\"session_error\":13,\"age_error\":"<<unsigned(expected)
        <<",\"clock_error\":"<<unsigned(pair.receiver.clock_state())<<",\"query_admitted\":true,\"duplicate_replay_rejected\":true,\"reopened_unknown\":true}\n";
}
}
int main(){try{
    auto root=std::filesystem::current_path()/("admission-rejection-"+std::to_string(getpid()));check(!std::filesystem::exists(root),"fixture output reuse refused");
    for(const auto& kind:{"control","expired","future"}){std::filesystem::create_directories(root/kind);run(root/kind,kind);}return 0;
}catch(const std::exception& error){std::cerr<<"FAIL: "<<error.what()<<'\n';return 1;}}
