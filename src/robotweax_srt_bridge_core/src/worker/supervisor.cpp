#include <robotweax/srt_bridge/worker.hpp>
#include "ipc.hpp"
#include "execution_pool.hpp"
#include <fcntl.h>
#include <sys/socket.h>
#include <sys/wait.h>
#include <spawn.h>
#include <signal.h>
#include <unistd.h>
#include <cerrno>
#include <chrono>
#include <thread>
#include <filesystem>

extern char** environ;
namespace robotweax::srt_bridge {
namespace {
std::uint64_t now(){return std::chrono::duration_cast<std::chrono::nanoseconds>(std::chrono::steady_clock::now().time_since_epoch()).count();}
void reap_later(pid_t pid)noexcept{
    // Only reachable if the kernel has not reaped a SIGKILLed child by the
    // bounded deadline (e.g. uninterruptible device I/O). No owner memory is held.
    try{std::thread([pid]{while(waitpid(pid,nullptr,0)<0&&errno==EINTR){}}).detach();}catch(...){/* Parent process can still reap SIGCHLD. */}
}
}
struct JournalWorker::Impl {
    WorkerOptions options;
    WorkerState state=WorkerState::starting;
    WorkerFault fault=WorkerFault::none;
    int socket=-1;pid_t pid=-1;
    std::shared_ptr<std::atomic<bool>> live=std::make_shared<std::atomic<bool>>(true);
    std::shared_ptr<execution_detail::Pool> execution;
    struct Pending {std::uint64_t token=0;WorkerRequest request{};std::shared_ptr<execution_detail::Record> dispatch{};};
    std::array<Pending,64> requests{};std::size_t count=0;
    std::uint64_t next=0,stop_started=0;
    bool stop_sent=false;
    explicit Impl(WorkerOptions o):options(std::move(o)){
        if(!std::filesystem::path(options.executable).is_absolute()||options.journal.test_hook||options.journal.test_context||options.journal.test_faults)
            throw std::invalid_argument("worker requires absolute executable and serializable options");
        const auto init=worker_ipc::initialize_frame(options);
        int pair[2];if(socketpair(AF_UNIX,SOCK_SEQPACKET|SOCK_CLOEXEC|SOCK_NONBLOCK,0,pair)<0)throw std::runtime_error("worker socketpair failed");
        try{execution=execution_detail::Pool::create(options.start_diagnostics);}catch(...){close(pair[0]);close(pair[1]);throw;}
        // Duplicate sources above all destination descriptors before spawn actions;
        // this is safe even when concurrent transport threads close/reuse fds.
        const int ipc_source=fcntl(pair[1],F_DUPFD_CLOEXEC,10);
        const int pool_source=fcntl(execution->fd(),F_DUPFD_CLOEXEC,10);
        if(ipc_source<0||pool_source<0){if(ipc_source>=0)close(ipc_source);if(pool_source>=0)close(pool_source);close(pair[0]);close(pair[1]);throw std::runtime_error("spawn descriptor duplication failed");}
        posix_spawn_file_actions_t actions;
        if(posix_spawn_file_actions_init(&actions)){close(ipc_source);close(pool_source);close(pair[0]);close(pair[1]);throw std::runtime_error("spawn actions failed");}
        int error=posix_spawn_file_actions_addclose(&actions,pair[0]);
        if(!error)error=posix_spawn_file_actions_addclose(&actions,pair[1]);
        if(!error)error=posix_spawn_file_actions_adddup2(&actions,ipc_source,3);
        if(!error)error=posix_spawn_file_actions_adddup2(&actions,pool_source,4);
        if(!error)error=posix_spawn_file_actions_addclosefrom_np(&actions,5);
        posix_spawnattr_t attr;const int attr_error=posix_spawnattr_init(&attr);
        if(!error)error=attr_error;
        if(!attr_error){sigset_t mask,defaults;sigemptyset(&mask);sigemptyset(&defaults);sigaddset(&defaults,SIGPIPE);
            if(!error)error=posix_spawnattr_setsigmask(&attr,&mask);
            if(!error)error=posix_spawnattr_setsigdefault(&attr,&defaults);
            if(!error)error=posix_spawnattr_setflags(&attr,POSIX_SPAWN_SETSIGMASK|POSIX_SPAWN_SETSIGDEF);}
        char mode[]="--worker-ipc-v3";char* argv[]={options.executable.data(),mode,nullptr};
        if(!error)error=posix_spawn(&pid,options.executable.c_str(),&actions,&attr,argv,environ);
        posix_spawn_file_actions_destroy(&actions);if(!attr_error)posix_spawnattr_destroy(&attr);
        close(ipc_source);close(pool_source);close(pair[1]);
        if(error){close(pair[0]);throw std::runtime_error("journal worker spawn failed");}
        socket=pair[0];
        if(send(socket,init.data(),init.size(),MSG_NOSIGNAL)!=static_cast<ssize_t>(init.size())){fail(WorkerFault::protocol);}
    }
    void fail(WorkerFault why)noexcept{live->store(false);if(execution)execution->revoke_all();state=WorkerState::failed;if(fault==WorkerFault::none)fault=why;if(pid>0)kill(pid,SIGKILL);}
    void inspect()noexcept{
        if(pid<=0)return;
        int status=0;const auto got=waitpid(pid,&status,WNOHANG);
        if(got==pid||(got<0&&errno==ECHILD)){
            pid=-1;live->store(false);execution->revoke_all();
            if(state==WorkerState::stopping)state=WorkerState::stopped;
            else if(state!=WorkerState::stopped){state=WorkerState::failed;if(fault==WorkerFault::none)fault=WorkerFault::exited;}
            count=0;requests={};
        }
    }
    bool receive(WorkerReply& reply){
        if(socket<0){inspect();return false;}
        worker_ipc::Frame frame{};const auto size=recv(socket,frame.data(),frame.size(),MSG_DONTWAIT|MSG_TRUNC);
        if(size<0){const bool closing=(state==WorkerState::stopping||state==WorkerState::stopped)&&(errno==ECONNRESET||errno==EPIPE);if(!closing&&errno!=EAGAIN&&errno!=EWOULDBLOCK&&errno!=EINTR)fail(WorkerFault::protocol);inspect();return false;}
        if(!size){inspect();if(pid>0&&state!=WorkerState::stopping)fail(WorkerFault::exited);return false;}
        if(size!=static_cast<ssize_t>(frame.size())){fail(WorkerFault::protocol);return false;}
        try{
            worker_ipc::Reader r(frame);
            if(r.operation==worker_ipc::ready){
                if((state!=WorkerState::starting&&state!=WorkerState::stopping)||r.token)throw std::runtime_error("unexpected worker ready");
                auto ready=worker_ipc::reply(r);
                if(ready.journal.error!=JournalError::none){fail(ready.journal.error==JournalError::invalid?WorkerFault::configuration:WorkerFault::storage);return false;}
                if(state==WorkerState::starting)state=WorkerState::ready;
                return false;
            }
            auto pending=std::find_if(requests.begin(),requests.end(),[&](const auto& q){return q.token&&q.token==r.token;});
            if(pending==requests.end())throw std::runtime_error("unexpected worker token");
            if(r.operation==worker_ipc::paused){reply={};reply.token=r.token;reply.operation=pending->request.operation;reply.test_paused=true;
                if(r.position<r.end){reply.test_handler_point=r.number(1);if(reply.test_handler_point<1||reply.test_handler_point>3)throw std::runtime_error("invalid handler barrier");reply.device=worker_ipc::result(r);reply.effects=r.number(8);}r.done();return true;}
            if(r.operation!=unsigned(pending->request.operation))throw std::runtime_error("unexpected worker operation");
            reply=worker_ipc::reply(r);
            if(reply.journal.entry){const auto& e=*reply.journal.entry;
                if((pending->request.operation!=WorkerOperation::invalidate_session&&e.request_id!=pending->request.request_id)||!valid_command(e.command)||e.payload_hash!=command_hash(e.route,e.command))throw std::runtime_error("invalid worker record");}
            const auto request=pending->request;const auto executed=pending->dispatch;*pending={};--count;
            if(executed){
                if(options.start_diagnostics)reply.start_observation=executed->pool->observation(*executed);
                executed->pool->revoke(*executed);
            }
            // The child may exit just after a committed result; that result is
            // still useful, but a dead/stopping worker cannot mint a send ticket.
            inspect();
            if(reply.journal&&reply.journal.inserted&&reply.operation==WorkerOperation::admit&&options.journal.side==JournalSide::sender&&state==WorkerState::ready&&live->load()){
                const auto& e=*reply.journal.entry;
                if(e.state==CommandState::local_queued&&e.owner_epoch==options.journal.process_epoch&&e.request_id==request.request_id&&e.route==request.route&&e.command==request.command&&
                   e.context.session==request.context.session&&e.context.source_epoch==request.context.source_epoch&&e.context.source_monotonic_ns==request.context.source_monotonic_ns&&e.context.deadline_ns==request.context.deadline_ns){
                    auto proof=std::make_shared<DurableCommandTicket::Proof>();proof->entry=e;proof->local_peer=options.journal.local_peer_id;proof->remote_peer=options.journal.remote_peer_id;proof->live=live;
                    reply.ticket=DurableCommandTicket(std::move(proof));
                }
            }
            if(reply.journal&&reply.operation==WorkerOperation::begin_dispatch&&options.journal.side==JournalSide::receiver&&state==WorkerState::ready&&live->load()){
                const auto& e=*reply.journal.entry;
                if(e.state==CommandState::dispatching&&e.owner_epoch==options.journal.process_epoch){auto record=execution->allocate(e,options.journal.local_peer_id,options.journal.remote_peer_id,live);if(record)reply.dispatch=DispatchTicket(std::move(record));}
            }
            if(reply.journal.error==JournalError::storage||reply.journal.error==JournalError::corrupt)fail(WorkerFault::storage);
            return true;
        }catch(...){fail(WorkerFault::protocol);return false;}
    }
    void stop()noexcept{
        live->store(false);execution->revoke_all();
        if(state==WorkerState::stopped)return;
        if(!stop_started)stop_started=now();
        state=WorkerState::stopping;
        if(!stop_sent&&socket>=0){worker_ipc::Writer w;const auto frame=w.finish(worker_ipc::stop,0);stop_sent=send(socket,frame.data(),frame.size(),MSG_NOSIGNAL)==static_cast<ssize_t>(frame.size());}
        inspect();
    }
    bool join(){
        stop();const auto kill_at=stop_started+2000000000ULL,end=stop_started+4000000000ULL;bool killed=false;
        while(pid>0&&now()<end){inspect();if(pid<=0)break;
            // Drain child replies so a normal child never waits for a full IPC
            // socket while trying to read STOP. Tickets remain revoked.
            WorkerReply ignored;receive(ignored);
            if(!killed&&now()>=kill_at){kill(pid,SIGKILL);killed=true;}
            std::this_thread::sleep_for(std::chrono::milliseconds(1));
        }
        inspect();if(pid>0){kill(pid,SIGKILL);fault=WorkerFault::shutdown_timeout;return false;}
        state=WorkerState::stopped;if(socket>=0){close(socket);socket=-1;}return true;
    }
    WorkerSubmission submit(const WorkerRequest& request,std::shared_ptr<execution_detail::Record> record={}){
    inspect();if(state==WorkerState::stopping||state==WorkerState::stopped)return {WorkerSubmit::stopped,0};
    if(state!=WorkerState::ready)return {WorkerSubmit::not_ready,0};
    if(unsigned(request.operation)<1||unsigned(request.operation)>11)return {WorkerSubmit::invalid,0};
    if(count==requests.size())return {WorkerSubmit::busy,0};
    if(next==UINT64_MAX)return {WorkerSubmit::invalid,0};
    const auto token=next+1;const auto frame=worker_ipc::encode(request,token);
    const auto sent=send(socket,frame.data(),frame.size(),MSG_NOSIGNAL|MSG_DONTWAIT);
    if(sent<0&&(errno==EAGAIN||errno==EWOULDBLOCK||errno==EINTR))return {WorkerSubmit::busy,0};
    if(sent!=static_cast<ssize_t>(frame.size())){fail(WorkerFault::protocol);return {WorkerSubmit::not_ready,0};}
    const auto at=std::find_if(requests.begin(),requests.end(),[](const auto& q){return !q.token;});
    *at={token,request,std::move(record)};++count;next=token;return {WorkerSubmit::queued,token};
    }
};
JournalWorker::JournalWorker(WorkerOptions options):impl_(std::make_unique<Impl>(std::move(options))){}
JournalWorker::~JournalWorker(){if(!impl_->join()&&impl_->pid>0){reap_later(impl_->pid);impl_->pid=-1;}if(impl_->socket>=0)close(impl_->socket);}
WorkerSubmission JournalWorker::submit(const WorkerRequest& request){
    if((request.operation==WorkerOperation::execute||request.operation==WorkerOperation::reconcile_sender)||request.grant_slot!=UINT32_MAX||request.grant_generation)return {WorkerSubmit::invalid,0};
    return impl_->submit(request);
}
WorkerSubmission JournalWorker::submit_reconcile(SenderSubmissionReceipt& receipt){
    const auto p=receipt.proof_;
    if(!p||p->live!=impl_->live||!p->live->load()||!p->claimed.load()||
       p->disposition.load(std::memory_order_acquire)!=SubmissionDisposition::abandoned||
       impl_->options.journal.side!=JournalSide::sender||p->entry.owner_epoch!=impl_->options.journal.process_epoch||
       p->local_peer!=impl_->options.journal.local_peer_id||p->remote_peer!=impl_->options.journal.remote_peer_id)return {WorkerSubmit::invalid,0};
    bool expected=false;if(!p->reconciliation_submitted.compare_exchange_strong(expected,true))return {WorkerSubmit::invalid,0};
    WorkerRequest q;q.operation=WorkerOperation::reconcile_sender;q.request_id=p->entry.request_id;q.route=p->entry.route;
    q.command=p->entry.command;q.context=p->entry.context;q.session=p->entry.context.session;
    const auto result=impl_->submit(q);
    if(result.result!=WorkerSubmit::queued)p->reconciliation_submitted.store(false);
    return result;
}
WorkerSubmission JournalWorker::submit_execute(DispatchTicket&& ticket){
    const auto record=ticket.record_;
    if(!record||record->pool!=impl_->execution||record->live!=impl_->live||record->submitted.load())return {WorkerSubmit::invalid,0};
    const auto state=record->pool->state(*record);
    if(!record->requested.load()||(state!=execution_detail::State::granted&&state!=execution_detail::State::revoked))return {WorkerSubmit::not_ready,0};
    WorkerRequest request;request.operation=WorkerOperation::execute;request.request_id=record->entry.request_id;request.grant_slot=record->slot;request.grant_generation=record->generation;
    const auto result=impl_->submit(request,record);
    if(result.result==WorkerSubmit::queued){record->submitted.store(true);ticket.record_.reset();}
    return result;
}
bool JournalWorker::poll(WorkerReply& reply){return impl_->receive(reply);}
bool JournalWorker::resume_test_barrier()noexcept{if(!impl_->options.test_pause_at&&!impl_->options.test_handler_pause)return false;return impl_->pid>0&&kill(impl_->pid,SIGCONT)==0;}
WorkerState JournalWorker::state()const noexcept{return impl_->state;}
WorkerFault JournalWorker::fault()const noexcept{return impl_->fault;}
std::size_t JournalWorker::pending()const noexcept{return impl_->count;}
void JournalWorker::request_stop()noexcept{impl_->stop();}
bool JournalWorker::join(){return impl_->join();}
}
