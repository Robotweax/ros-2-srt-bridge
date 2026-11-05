#include <robotweax/srt_bridge/transport.hpp>
#include <robotweax/srt_bridge/worker.hpp>
#include <chrono>
#include <filesystem>
#include <iostream>
#include <thread>
#include <unistd.h>
using namespace robotweax::srt_bridge;
namespace {
unsigned checks=0;
void check(bool ok,const char* text){++checks;if(!ok)throw std::runtime_error(text);}
std::uint64_t now(){return TransportOwner::monotonic_ns();}
template<class F> void until(F f,const char* text){const auto end=now()+7000000000ULL;while(!f()){if(now()>=end)throw std::runtime_error(text);std::this_thread::sleep_for(std::chrono::milliseconds(1));}++checks;}
std::string secret(){std::string s;constexpr char hex[]="0123456789abcdef";for(auto b:random_identity()){auto v=std::to_integer<unsigned>(b);s+=hex[v>>4];s+=hex[v&15];}return s;}
RouteManifest manifest(){Route command{100,RouteKind::command,Direction::listener_to_caller,QosMapping::request_status,true,4000,5000,0,1,"robotweax.srt_bridge.v1.SetMeasurementRateCommand",rate_command_schema_hash()};return *make_manifest(std::span(&command,1)).value;}
TransportConfig config(Role role,const std::string& ip,const std::string& key){SessionConfig s{role,role==Role::caller?"robot":"operator",role==Role::caller?"operator":"robot",random_identity(),role==Role::caller?1U:2U,manifest(),{1000,1000000,5000000000ULL,100000000}};return {std::move(s),{ip,0},{ip,0},key};}
void ready(JournalWorker& w){WorkerReply r;until([&]{w.poll(r);return w.state()==WorkerState::ready||w.state()==WorkerState::failed;},"worker not ready");check(w.state()==WorkerState::ready,"worker startup failed");}
WorkerReply rpc(JournalWorker& w,const WorkerRequest& q){WorkerSubmission s;until([&]{s=w.submit(q);return s.result!=WorkerSubmit::busy;},"worker request busy");check(s.result==WorkerSubmit::queued,"worker request rejected");WorkerReply r;until([&]{return w.poll(r);},"worker response missing");check(r.token==s.token,"wrong worker response");return r;}
WorkerOptions options(const std::filesystem::path& directory,const TransportConfig& c,JournalSide side){WorkerOptions w;w.executable=WORKER_EXECUTABLE;w.journal.path=(directory/(side==JournalSide::sender?"sender.sqlite":"receiver.sqlite")).string();w.journal.local_peer_id=c.session.local_peer_id;w.journal.remote_peer_id=c.session.expected_peer_id;w.journal.process_epoch=c.session.local_epoch;w.journal.side=side;return w;}
CommandCheck freshness(TransportOwner& robot,const TransportMessage& message,std::uint64_t token){until([&]{return robot.request_command_check(message.context,message.envelope,token)==SubmitResult::queued;},"owner check admission failed");CommandCheck check;until([&]{return robot.poll_command_check(check);},"owner check missing");if(check.token!=token)throw std::runtime_error("wrong check correlation");return check;}
void run(bool ipv6){
    const auto key=secret();const auto ip=ipv6?"::1":"127.0.0.1";
    auto operator_config=config(Role::listener,ip,key);TransportOwner op(operator_config);
    until([&]{return op.snapshot().control_port&&op.snapshot().sensor_port;},"operator listen failed");
    auto robot_config=config(Role::caller,ip,key);robot_config.control.port=op.snapshot().control_port;robot_config.sensor.port=op.snapshot().sensor_port;TransportOwner robot(robot_config);
    until([&]{return op.snapshot().state==SessionState::active&&robot.snapshot().state==SessionState::active;},"transport not active");
    auto directory=std::filesystem::current_path()/("worker-transport-"+std::to_string(getpid()));for(unsigned n=0;std::filesystem::exists(directory);++n)directory=std::filesystem::current_path()/("worker-transport-"+std::to_string(getpid())+"-"+std::to_string(n));
    const auto sender_options=options(directory,operator_config,JournalSide::sender),receiver_options=options(directory,robot_config,JournalSide::receiver);
    // Spawn after both SRT threads are already active; child inherits only its
    // IPC descriptor and standard streams, not the live transport descriptors.
    JournalWorker sender(sender_options),receiver(receiver_options);ready(sender);ready(receiver);
    // Freeze a separate sender journal after commit while both network owners
    // stay live. QUERY still progresses; stop must revoke and reap that child.
    auto blocked_options=sender_options;blocked_options.journal.path=(directory/"blocked.sqlite").string();blocked_options.test_pause_at=JournalPoint::admission_committed;
    JournalWorker blocked(blocked_options);ready(blocked);
    WorkerRequest blocked_request;blocked_request.operation=WorkerOperation::admit;blocked_request.request_id=random_identity();blocked_request.route=100;blocked_request.command={100,5000,0,1};
    const auto blocked_origin=now();blocked_request.context={op.snapshot().context.session,operator_config.session.local_epoch,blocked_origin,blocked_origin+5000000000ULL};
    auto paused=rpc(blocked,blocked_request);check(paused.test_paused&&!paused.ticket,"journal barrier did not pause");
    for(unsigned n=0;n<8;++n){const auto id=random_identity();until([&]{return op.submit_query(op.snapshot().context,100,id)==SubmitResult::queued;},"blocked journal stalled query enqueue");TransportMessage message;until([&]{return robot.poll_control(message);},"blocked journal stalled network I/O");check(message.envelope.request_id==id&&message.envelope.kind==Kind::query,"wrong blocked query");}
    const auto stopped_at=now();check(blocked.join()&&now()-stopped_at<5000000000ULL,"blocked journal exceeded shutdown deadline");
    check(robot.snapshot().state==SessionState::active&&op.snapshot().state==SessionState::active,"journal shutdown killed transport");
    blocked_options.test_pause_at.reset();JournalWorker blocked_recovery(blocked_options);ready(blocked_recovery);blocked_request.operation=WorkerOperation::get;
    check(rpc(blocked_recovery,blocked_request).journal.entry->state==CommandState::unknown,"unacknowledged sender commit replayed");check(blocked_recovery.join(),"blocked recovery did not stop");
    WorkerRequest request;request.operation=WorkerOperation::admit;request.request_id=random_identity();request.route=100;request.command={100,5000,0,1};
    const auto origin=now();request.context={op.snapshot().context.session,operator_config.session.local_epoch,origin,origin+5000000000ULL};
    auto admission=rpc(sender,request);check(admission.journal&&admission.ticket.has_value(),"sender did not commit ticket");
    auto duplicate=rpc(sender,request);check(duplicate.journal&&!duplicate.ticket,"duplicate got a send ticket");
    const auto context=op.snapshot().context;
    until([&]{return op.submit_command(context,std::move(*admission.ticket))==SubmitResult::queued;},"ticket not admitted");
    check(op.submit_command(context,std::move(*admission.ticket))==SubmitResult::invalid,"ticket reused");
    TransportMessage incoming;until([&]{return robot.poll_control(incoming);},"command not received");
    check(incoming.envelope.kind==Kind::command&&incoming.envelope.request_id==request.request_id&&decode_rate_command(incoming.body())==request.command,"wrong command payload");
    check(incoming.envelope.source_monotonic_ns==origin,"sender journal handoff renewed age");
    WorkerRequest receive=request;receive.context={incoming.envelope.session_id,incoming.envelope.source_epoch,origin,incoming.deadline_ns};
    auto accepted=rpc(receiver,receive);check(accepted.journal&&accepted.journal.entry->state==CommandState::accepted,"receiver not durable");
    const auto& e=*accepted.journal.entry;CommandStatus status{e.state,e.reason,e.command,e.payload_hash,e.result,e.revision};
    until([&]{return robot.submit_status(incoming.context,100,request.request_id,status)==SubmitResult::queued;},"ACCEPTED not queued");
    TransportMessage reply;until([&]{return op.poll_control(reply);},"ACCEPTED not received");
    WorkerRequest observe=request;observe.operation=WorkerOperation::observe_remote;observe.remote_status=*decode_command_status(100,reply.body());
    check(rpc(sender,observe).journal.error==JournalError::none,"sender did not persist peer status");
    const auto before=freshness(robot,incoming,1);check(before.fresh()&&before.deadline_ns<=incoming.deadline_ns+100000000,"pre-dispatch check not fresh");
    WorkerRequest dispatch=receive;dispatch.operation=WorkerOperation::begin_dispatch;dispatch.session=incoming.context.session;dispatch.clock_qualified=true;
    check(rpc(receiver,dispatch).journal.entry->state==CommandState::dispatching,"dispatch commit missing");
    const auto after=freshness(robot,incoming,2);check(after.fresh()&&after.evaluated_ns>=before.evaluated_ns,"post-commit check missing");
    for(std::uint64_t token=10;token<74;++token)until([&]{return robot.request_command_check(incoming.context,incoming.envelope,token)==SubmitResult::queued;},"check mailbox admission failed");
    check(robot.request_command_check(incoming.context,incoming.envelope,100)==SubmitResult::busy,"check mailbox exceeded 64");
    check(robot.request_command_check(incoming.context,incoming.envelope,10)==SubmitResult::invalid,"duplicate check token accepted");
    std::array<bool,64> observed{};
    for(unsigned n=0;n<64;++n){CommandCheck result;until([&]{return robot.poll_command_check(result);},"bounded check result missing");check(result.token>=10&&result.token<74&&!observed[result.token-10]&&result.fresh(),"check token lost/duplicated");observed[result.token-10]=true;}
    until([&]{return now()>=incoming.deadline_ns+1000000;},"command deadline did not elapse");
    const auto expired=freshness(robot,incoming,4);check(!expired.fresh()&&expired.error==SessionError::stale_sample,"post-commit expiry allowed handler start");
    // No handler is invoked from a point-in-time freshness reply. Drop the
    // session after DISPATCHING, then ensure the old work is rejected by owner.
    op.request_stop();op.join();until([&]{return robot.snapshot().context.session!=incoming.context.session;},"CONTROL loss not applied");
    check(robot.request_command_check(incoming.context,incoming.envelope,3)==SubmitResult::obsolete,"stale dispatch check accepted");
    check(receiver.join(),"receiver worker did not stop");
    JournalWorker recovered(receiver_options);ready(recovered);WorkerRequest get=receive;get.operation=WorkerOperation::get;
    auto recovered_entry=rpc(recovered,get);check(recovered_entry.journal.entry->state==CommandState::unknown,"in-flight dispatch replayed after recovery");
    check(recovered.join(),"recovered worker stop failed");
    // A committed but never submitted ticket is revoked immediately by stop.
    auto revoked=request;revoked.request_id=random_identity();revoked.context.source_monotonic_ns=now();revoked.context.deadline_ns=now()+5000000000ULL;auto ticket=rpc(sender,revoked);check(ticket.ticket.has_value(),"revocation fixture ticket missing");sender.request_stop();
    check(op.submit_command(context,std::move(*ticket.ticket))==SubmitResult::obsolete,"stopped worker ticket remained live");
    check(sender.join(),"sender worker stop failed");robot.request_stop();robot.join();
}
}
int main(int argc,char** argv){try{check(argc==2,"family required");run(std::string(argv[1])=="ipv6");std::cout<<"PASS worker transport "<<argv[1]<<": "<<checks<<" checks\n";return 0;}catch(const std::exception& e){std::cerr<<"FAIL: "<<e.what()<<"\n";return 1;}}
