#include <robotweax/srt_bridge/handler.hpp>
#include "ipc.hpp"
#include "execution_pool.hpp"
#include <sys/socket.h>
#include <signal.h>
#include <fcntl.h>
#include <unistd.h>
#include <cerrno>
#include <cstring>
#include <chrono>
namespace bridge=robotweax::srt_bridge;
namespace ipc=bridge::worker_ipc;
namespace {
constexpr int socket_fd=3;
void send(const ipc::Frame& frame){ssize_t count;do{count=::send(socket_fd,frame.data(),frame.size(),MSG_NOSIGNAL);}while(count<0&&errno==EINTR);if(count!=ssize_t(frame.size()))throw std::runtime_error("worker IPC send");}
std::optional<ipc::Frame> receive(){ipc::Frame frame{};ssize_t count;do{count=recv(socket_fd,frame.data(),frame.size(),MSG_TRUNC);}while(count<0&&errno==EINTR);if(!count)return {};if(count!=ssize_t(frame.size()))throw std::runtime_error("worker IPC receive");return frame;}
struct Barrier {std::optional<bridge::JournalPoint> point;std::uint64_t token=0;};
void hook(bridge::JournalPoint point,void* context){auto& barrier=*static_cast<Barrier*>(context);if(barrier.point&&*barrier.point==point){ipc::Writer w;send(w.finish(ipc::paused,barrier.token));raise(SIGSTOP);}}
}
int bridge::run_journal_worker(int argc,char** argv,RateHandlerBackend* external){
    if(argc!=2||std::strcmp(argv[1],"--worker-ipc-v3"))return 64;
    int type=0;socklen_t length=sizeof(type);if(getsockopt(socket_fd,SOL_SOCKET,SO_TYPE,&type,&length)||type!=SOCK_SEQPACKET)return 64;
    const auto flags=fcntl(socket_fd,F_GETFL);if(flags<0||fcntl(socket_fd,F_SETFL,flags&~O_NONBLOCK))return 64;
    try{
        auto execution=bridge::execution_detail::Pool::map(4);
        auto first=receive();if(!first)return 65;ipc::Reader init(*first);auto options=ipc::options(init);
        if((options.external_rate_handler&&options.simulated_rate_handler)||(options.external_rate_handler&&!external)){
            bridge::JournalResult failed;failed.error=bridge::JournalError::invalid;send(ipc::encode_reply(ipc::ready,0,failed));return 78;
        }
        if(options.external_rate_handler){try{external->initialize();}catch(...){bridge::JournalResult failed;failed.error=bridge::JournalError::invalid;send(ipc::encode_reply(ipc::ready,0,failed));return 78;}}
        Barrier barrier{options.test_pause_at,0};bridge::JournalFaults faults;
        if(options.test_pause_at){options.journal.test_hook=hook;options.journal.test_context=&barrier;}
        if(options.test_faults)options.journal.test_faults=&faults;
        std::unique_ptr<bridge::CommandJournal> journal;
        try{journal=std::make_unique<bridge::CommandJournal>(options.journal);}catch(...){bridge::JournalResult failed;failed.error=bridge::JournalError::storage;send(ipc::encode_reply(ipc::ready,0,failed));return 70;}
        if(options.test_faults)faults=*options.test_faults;
        send(ipc::encode_reply(ipc::ready,0,{}));
        std::uint32_t device_rate=200;std::uint64_t device_generation=0,effects=0;
        auto monotonic=[](){return std::uint64_t(std::chrono::duration_cast<std::chrono::nanoseconds>(std::chrono::steady_clock::now().time_since_epoch()).count());};
        const auto snapshot=[&](){return options.external_rate_handler?external->snapshot():options.simulated_rate_handler?bridge::HandlerSnapshot{{device_rate,device_generation,true},effects}:bridge::HandlerSnapshot{};};
        auto pause_handler=[&](unsigned point){if(options.test_handler_pause==point){ipc::Writer w;w.number(point,1);const auto state=snapshot();ipc::result(w,state.device);w.number(state.effects,8);send(w.finish(ipc::paused,barrier.token));raise(SIGSTOP);}};
        while(auto frame=receive()){
            ipc::Reader reader(*frame);if(reader.operation==ipc::stop){if(reader.token)return 65;reader.done();return 0;}
            const auto token=reader.token;const auto request=ipc::request(reader);barrier.token=token;bridge::JournalResult result;bool may_transmit=false;
            const auto operation_now=std::uint64_t(std::chrono::duration_cast<std::chrono::nanoseconds>(std::chrono::steady_clock::now().time_since_epoch()).count());
            using Op=bridge::WorkerOperation;
            switch(request.operation){
                case Op::admit:result=journal->admit(request.request_id,request.route,request.command,request.context,operation_now);break;
                case Op::get:result=journal->get(request.request_id);break;
                case Op::begin_dispatch:result=journal->begin_dispatch(request.request_id,request.session,request.clock_qualified,operation_now);break;
                case Op::finish:result=journal->finish(request.request_id,request.state,request.reason,request.result,operation_now);break;
                case Op::invalidate_session:result.error=journal->invalidate_session(request.session,operation_now);break;
                case Op::observe_remote:result.error=journal->observe_remote(request.request_id,request.route,request.remote_status,operation_now);break;
                case Op::decline:result=journal->decline(request.request_id,request.state,request.reason,operation_now);break;
                case Op::handler_snapshot:if(!options.simulated_rate_handler&&!options.external_rate_handler)result.error=bridge::JournalError::invalid_state;break;
                case Op::execute:{
                    result=journal->get(request.request_id);
                    if((!options.simulated_rate_handler&&!options.external_rate_handler)||options.journal.side!=bridge::JournalSide::receiver||!result||result.entry->state!=bridge::CommandState::dispatching||result.entry->owner_epoch!=options.journal.process_epoch){result.error=bridge::JournalError::invalid_state;break;}
                    const auto entry=*result.entry;pause_handler(1);
                    const auto start=execution->consume(request.grant_slot,request.grant_generation,entry.request_id,entry.payload_hash,monotonic());
                    if(start!=bridge::execution_detail::Start::started){
                        const bool expired=monotonic()>=entry.context.deadline_ns;
                        result=journal->finish(entry.request_id,expired?bridge::CommandState::expired:bridge::CommandState::rejected,expired?bridge::CommandReason::start_deadline:bridge::CommandReason::context_lost,{},monotonic());break;
                    }
                    pause_handler(2);
                    if(monotonic()>=execution->deadline(request.grant_slot,request.grant_generation)){
                        const bool expired=monotonic()>=entry.context.deadline_ns;
                        result=journal->finish(entry.request_id,expired?bridge::CommandState::expired:bridge::CommandState::rejected,expired?bridge::CommandReason::start_deadline:bridge::CommandReason::context_lost,{},monotonic());
                    }
                    else if(options.external_rate_handler){
                        bridge::HandlerOutcome outcome;
                        try{outcome=external->execute(entry,execution->deadline(request.grant_slot,request.grant_generation));}catch(...){outcome={};}
                        const bridge::CommandStatus proposed{outcome.state,outcome.reason,entry.command,entry.payload_hash,outcome.result,3};
                        if(outcome.state==bridge::CommandState::local_queued||outcome.state==bridge::CommandState::accepted||outcome.state==bridge::CommandState::dispatching||!bridge::valid_remote_status(entry.route,proposed))outcome={};
                        if(outcome.state==bridge::CommandState::succeeded)pause_handler(3);
                        result=journal->finish(entry.request_id,outcome.state,outcome.reason,outcome.result,monotonic());
                    }
                    else if(device_generation!=entry.command.expected_generation)result=journal->finish(entry.request_id,bridge::CommandState::failed,bridge::CommandReason::generation_conflict,{},monotonic());
                    else{
                        device_rate=entry.command.rate_hz;device_generation=entry.command.new_generation;++effects;pause_handler(3);
                        result=journal->finish(entry.request_id,bridge::CommandState::succeeded,bridge::CommandReason::none,{device_rate,device_generation,true},monotonic());
                    }
                    execution->complete(request.grant_slot,request.grant_generation);break;
                }
                case Op::sender_may_transmit:may_transmit=journal->sender_may_transmit(request.request_id,request.session,operation_now);result.error=journal->healthy()?bridge::JournalError::none:bridge::JournalError::storage;break;
            }
            const auto state=snapshot();send(ipc::encode_reply(unsigned(request.operation),token,result,may_transmit,state.device,state.effects));
        }
        return 0;
    }catch(...){return 65;}
}
