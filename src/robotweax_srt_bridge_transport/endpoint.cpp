#include <robotweax/srt_bridge/endpoint.hpp>
#include <algorithm>
#include <atomic>
#include <chrono>
#include <mutex>
#include <thread>
#include <stdexcept>

namespace robotweax::srt_bridge {
namespace {
std::uint64_t now(){return TransportOwner::monotonic_ns();}
bool zero(Identity id){return id==Identity{};}
bool active(SessionState state){return state==SessionState::active||state==SessionState::control_active||state==SessionState::sensor_binding;}
bool terminal(const JournalEntry& e){return e.state!=CommandState::local_queued&&e.state!=CommandState::accepted&&e.state!=CommandState::dispatching&&
    !(e.state==CommandState::unknown&&e.reason==CommandReason::reconcile_required);}
CommandStatus status(const JournalEntry& e){return {e.state,e.reason,e.command,e.payload_hash,e.result,e.revision};}
ControlErrorCode code(JournalError error){switch(error){
    case JournalError::busy:return ControlErrorCode::busy;case JournalError::capacity:return ControlErrorCode::capacity;
    case JournalError::conflict:return ControlErrorCode::conflict;case JournalError::not_found:return ControlErrorCode::not_found;
    case JournalError::clock_unqualified:return ControlErrorCode::clock_unqualified;case JournalError::context_lost:return ControlErrorCode::context_lost;
    case JournalError::storage:case JournalError::corrupt:return ControlErrorCode::storage;default:return ControlErrorCode::invalid_request;}}
JournalError local_error(ControlErrorCode error){switch(error){
    case ControlErrorCode::busy:return JournalError::busy;case ControlErrorCode::capacity:return JournalError::capacity;
    case ControlErrorCode::conflict:return JournalError::conflict;case ControlErrorCode::not_found:return JournalError::not_found;
    case ControlErrorCode::clock_unqualified:return JournalError::clock_unqualified;case ControlErrorCode::context_lost:return JournalError::context_lost;
    case ControlErrorCode::storage:return JournalError::storage;default:return JournalError::invalid;}}

}
struct CommandEndpoint::Impl {
    enum class Stage { idle,rpc_submit,rpc_wait,send_command,send_status,send_error,precheck_submit,precheck_wait,start_submit,start_wait,execute_submit,event };
    enum class After { local_admit,local_get,peer_admit,peer_expire,peer_get,peer_observe,peer_observed_get,peer_error_get,dispatch,finish,decline,invalidate,abandoned };
    struct Task {bool execute=false;Identity id{};std::uint32_t route=0;RateCommand command{};std::uint64_t origin=0;TransportContext context{};};
    struct Track {bool used=false;Identity id{};std::uint32_t route=0;Identity queried_session{},suspended_session{};std::uint64_t next=0;};
    struct Job {
        Stage stage=Stage::idle;
        After after=After::local_get;
        Task task{};
        TransportMessage message{};
        CommandCheck start_check{};
        WorkerRequest request{};
        std::uint64_t worker_token=0,check_token=0,sent_ns=0;
        std::optional<JournalEntry> entry{};
        std::optional<DurableCommandTicket> sender_ticket{};
        std::optional<DispatchTicket> dispatch_ticket{};
        JournalError error=JournalError::none;
        std::optional<ControlError> outgoing_error{},received_error{};
        bool dispatch_after_status=false,notify_after_status=false;
    };
    EndpointOptions options;
    TransportOwner transport;
    const bool sender;
    std::atomic<bool> stopping{false},resume_test{false};
    std::thread thread;
    mutable std::mutex mutex;
    EndpointSnapshot shared{},current{};
    std::array<Task,64> input{};std::size_t input_head=0,input_count=0;
    std::optional<CommandEvent> shutdown_event{};
    std::array<CommandEvent,64> output{};std::size_t output_head=0,output_count=0;
    std::array<Track,64> tracks{};std::size_t track_cursor=0;
    std::array<Identity,64> lost{};std::size_t lost_head=0,lost_count=0;
    Identity last_session{};
    std::uint64_t next_check=0;
    Job job{};
    bool query_turn=false;
    static EndpointOptions validate(EndpointOptions o){
        const auto& j=o.worker.journal;const auto& s=o.transport.session;const bool sending=j.side==JournalSide::sender;
        if(j.local_peer_id!=s.local_peer_id||j.remote_peer_id!=s.expected_peer_id||j.process_epoch!=s.local_epoch||
           (sending!=(s.role==Role::listener))||(!sending&&!o.worker.simulated_rate_handler&&!o.worker.external_rate_handler)||
           (sending&&(o.worker.simulated_rate_handler||o.worker.external_rate_handler))||(o.worker.simulated_rate_handler&&o.worker.external_rate_handler)||o.operation_timeout_ns<1000000||o.operation_timeout_ns>60000000000ULL)
            throw std::invalid_argument("endpoint worker/transport binding or handler configuration mismatch");
        if(o.worker.start_diagnostics&&!o.transport.start_diagnostics)throw std::invalid_argument("worker start diagnostics require endpoint start trace");
        o.worker.start_diagnostics=o.transport.start_diagnostics;
        const auto schema=rate_command_schema_hash();
        for(const auto& route:s.manifest.routes())if(route.enabled&&route.kind==RouteKind::command&&
            (route.type_name!="robotweax.srt_bridge.v1.SetMeasurementRateCommand"||route.type_hash!=schema))throw std::invalid_argument("endpoint only supports declared rate-command schema");
        return o;
    }
    explicit Impl(EndpointOptions o):options(validate(std::move(o))),transport(options.transport),sender(options.worker.journal.side==JournalSide::sender){
        thread=std::thread([this]{run();});
    }
    ~Impl(){stopping=true;transport.request_stop();if(thread.joinable())thread.join();}
    void trace(CommandTracePoint point,CommandTraceReason reason=CommandTraceReason::none,unsigned value=0,Identity session={},Identity entry_owner={},unsigned detail=0,std::uint64_t request_sequence=0,std::uint64_t origin_ns=0){
        if(!options.transport.command_trace)return;
        const auto c=transport.snapshot().context;
        options.transport.command_trace->record(CommandTraceProducer::coordinator,{0,now(),point,reason,job.task.id,zero(session)?c.session:session,
            options.transport.session.local_epoch,c.control_generation,c.sensor_generation,job.task.route,value,entry_owner,detail,request_sequence,origin_ns});
    }
    void trace_start(CommandTracePoint point,unsigned value,std::uint64_t worker_token=0,const WorkerReply* reply=nullptr){
        if(!options.transport.start_diagnostics)return;
        CommandTraceEvent e{};const auto& c=job.message.context;const auto& check=job.start_check;
        e.monotonic_ns=now();e.point=point;e.value=value;e.request=job.task.id;e.route=job.task.route;e.session=c.session;
        e.owner_epoch=options.transport.session.local_epoch;e.entry_owner_epoch=job.entry?job.entry->owner_epoch:Identity{};
        e.control_generation=c.control_generation;e.sensor_generation=c.sensor_generation;e.detail=6;
        e.request_sequence=job.message.envelope.sequence;e.origin_ns=job.message.envelope.source_monotonic_ns;
        e.check_token=job.check_token;e.worker_token=worker_token;e.evaluated_ns=check.evaluated_ns;e.clock_deadline_ns=check.clock_deadline_ns;
        e.start_granted=check.start_granted;e.grant_slot=check.grant_slot;e.grant_generation=check.grant_generation;
        e.grant_deadline_ns=check.start_granted?check.deadline_ns:0;e.command_deadline_ns=job.entry?job.entry->context.deadline_ns:0;
        if(reply){
            if(reply->journal.entry){e.terminal_state=unsigned(reply->journal.entry->state);e.terminal_reason=unsigned(reply->journal.entry->reason);}
            if(reply->start_observation){const auto& o=*reply->start_observation;e.worker_observation_available=true;
                e.consume_ns=o.consume_ns;e.consume_deadline_ns=o.consume_deadline_ns;e.consume_result=o.consume_result;
                e.second_gate_ns=o.second_gate_ns;e.second_gate_deadline_ns=o.second_gate_deadline_ns;e.second_gate_checked=o.second_gate_checked;e.handler_invoked=o.handler_invoked;}
        }
        options.transport.command_trace->record(CommandTraceProducer::coordinator,e);
    }
    void trace_sender(CommandTracePoint point,const std::optional<JournalEntry>& entry,unsigned error,unsigned detail,std::uint64_t token=0){
        if(!sender||!options.transport.sender_diagnostics)return;
        CommandTraceEvent e{};e.monotonic_ns=now();e.point=point;e.value=error;e.detail=detail;e.worker_token=token;
        e.request=job.task.id;e.route=job.task.route;e.owner_epoch=options.transport.session.local_epoch;
        const auto c=current.transport.context;e.control_generation=c.control_generation;e.sensor_generation=c.sensor_generation;
        e.session=!zero(job.request.session)?job.request.session:!zero(job.message.context.session)?job.message.context.session:c.session;
        e.journal_entry_available=entry.has_value();
        if(entry){e.request=entry->request_id;e.route=entry->route;e.session=entry->context.session;e.entry_owner_epoch=entry->owner_epoch;
            e.origin_ns=entry->context.source_monotonic_ns;e.command_deadline_ns=entry->context.deadline_ns;
            e.terminal_state=unsigned(entry->state);e.terminal_reason=unsigned(entry->reason);e.journal_revision=entry->revision;}
        options.transport.command_trace->record(CommandTraceProducer::coordinator,e);
    }
    void fail(EndpointFault fault){if(current.fault==EndpointFault::none)current.fault=fault;stopping=true;transport.request_stop();}
    void publish(JournalWorker* worker){
        current.transport=transport.snapshot();
        if(worker){current.worker=worker->state();current.worker_fault=worker->fault();}
        current.ready=current.running&&!stopping.load()&&current.worker==WorkerState::ready&&active(current.transport.state);
        current.suspended=std::count_if(tracks.begin(),tracks.end(),[&](const auto& track){return track.used&&!zero(track.suspended_session)&&track.suspended_session==current.transport.context.session;});
        current.tracked=std::count_if(tracks.begin(),tracks.end(),[](const auto& track){return track.used;});
        std::lock_guard lock(mutex);current.queued=input_count;current.events=output_count;shared=current;
    }
    bool emit(){
        std::lock_guard lock(mutex);if(output_count==output.size())return false;
        const auto id=job.entry?job.entry->request_id:job.task.id;const auto route=job.entry?job.entry->route:job.task.route;
        output[(output_head+output_count++)%output.size()]={id,route,job.error,job.entry,job.received_error,job.received_error?job.message.context:TransportContext{}};
        trace_sender(CommandTracePoint::sender_event,job.entry,unsigned(job.error),job.received_error?unsigned(job.received_error->code):0);
        if(sender&&job.entry&&terminal(*job.entry))for(auto& track:tracks)if(track.used&&track.id==id)track={};
        job={};return true;
    }
    bool track(const JournalEntry& entry,bool explicit_request=false){
        if(terminal(entry))return true;
        auto found=std::find_if(tracks.begin(),tracks.end(),[&](const auto& value){return value.used&&value.id==entry.request_id;});
        if(found!=tracks.end()){if(explicit_request){found->suspended_session={};found->next=0;}else if(!zero(found->suspended_session)){found->suspended_session={};found->next=now()+1000000000ULL;}return true;}
        found=std::find_if(tracks.begin(),tracks.end(),[](const auto& value){return !value.used;});
        if(found==tracks.end())return false;
        *found={true,entry.request_id,entry.route,{},{},0};return true;
    }
    void rpc(WorkerRequest request,After after){job.request=request;job.after=after;job.worker_token=0;job.stage=Stage::rpc_submit;}
    WorkerRequest request(WorkerOperation op)const{
        WorkerRequest q;q.operation=op;q.request_id=job.task.id;q.route=job.task.route;return q;
    }
    void notify(JournalError error=JournalError::none){job.error=error;if(error!=JournalError::none)job.entry.reset();job.stage=Stage::event;}
    void send_error(JournalError error){
        const auto wire=code(error);const auto retry=wire==ControlErrorCode::busy?250U:wire==ControlErrorCode::capacity?1000U:0U;
        job.entry.reset();job.outgoing_error=ControlError{wire,job.message.envelope.kind,job.message.envelope.sequence,retry};job.stage=Stage::send_error;
    }
    void send_status(bool dispatch=false,bool notify=true){job.dispatch_after_status=dispatch;job.notify_after_status=notify;job.stage=Stage::send_status;}
    void check_stage(bool start){if(next_check==UINT64_MAX){fail(EndpointFault::capacity);return;}job.check_token=++next_check;job.stage=start?Stage::start_submit:Stage::precheck_submit;}
    void decline(SessionError error,bool committed){
        auto q=request(committed?WorkerOperation::finish:WorkerOperation::decline);
        const bool expired=error==SessionError::stale_sample;
        q.state=expired?CommandState::expired:CommandState::rejected;q.reason=expired?CommandReason::start_deadline:CommandReason::context_lost;
        if(committed)trace_start(CommandTracePoint::start_declined,unsigned(error));
        rpc(q,committed?After::finish:After::decline);
    }
    void context_changes(){
        const auto session=transport.snapshot().context.session;
        if(!zero(last_session)&&last_session!=session){
            trace(CommandTracePoint::session_changed,CommandTraceReason::session_changed,0,last_session);
            bool exists=false;for(std::size_t n=0;n<lost_count;++n)exists=exists||lost[(lost_head+n)%lost.size()]==last_session;
            if(!exists){if(lost_count==lost.size()){fail(EndpointFault::capacity);return;}lost[(lost_head+lost_count++)%lost.size()]=last_session;}
        }
        last_session=session;
    }
    void completion(WorkerReply reply){
        if(reply.token!=job.worker_token||job.stage!=Stage::rpc_wait){fail(EndpointFault::protocol);return;}
        if(reply.device.valid){current.device=reply.device;current.effects=reply.effects;}
        if(reply.test_paused){current.test_paused=true;return;}
        current.test_paused=false;
        if(reply.operation==WorkerOperation::execute)trace_start(CommandTracePoint::worker_start,unsigned(reply.journal.error),reply.token,&reply);
        job.worker_token=0;
        if(reply.journal.entry)job.entry=reply.journal.entry;
        const auto error=reply.journal.error;
        trace_sender(CommandTracePoint::sender_journal,reply.journal.entry,unsigned(error),unsigned(reply.operation),reply.token);
        if(job.after==After::peer_admit||job.after==After::peer_expire||job.after==After::peer_get)
            trace(CommandTracePoint::receiver_worker_result,CommandTraceReason::none,unsigned(error),job.message.context.session,
                job.entry?job.entry->owner_epoch:Identity{},unsigned(job.message.envelope.kind),job.message.envelope.sequence,job.message.envelope.source_monotonic_ns);
        if(reply.journal.entry&&reply.journal.entry->state==CommandState::unknown)
            trace(CommandTracePoint::worker_unknown,CommandTraceReason::none,unsigned(reply.journal.entry->reason),{},reply.journal.entry->owner_epoch);
        if(job.after==After::invalidate||job.after==After::abandoned)
            trace(CommandTracePoint::invalidate_completed,job.after==After::invalidate?CommandTraceReason::session_changed:CommandTraceReason::abandoned_submit,unsigned(error),job.request.session);
        if(error==JournalError::storage||error==JournalError::corrupt){notify(error);fail(EndpointFault::worker);return;}
        if(job.after==After::peer_error_get){
            if(job.entry&&job.entry->route!=job.task.route)job.entry.reset();
            if(job.entry&&(terminal(*job.entry)||(job.received_error->request_kind==Kind::command&&job.entry->revision>0))){job={};return;}
            for(auto& track:tracks)if(track.used&&track.id==job.task.id&&track.route==job.task.route)track.suspended_session=job.message.context.session;
            job.entry.reset();notify(local_error(job.received_error->code));return;
        }
        if(error!=JournalError::none){if(job.after==After::peer_admit||job.after==After::peer_expire||job.after==After::peer_get)send_error(error);else notify(error);return;}
        if(job.entry&&(job.after==After::local_get||job.after==After::peer_get||job.after==After::peer_observed_get)&&job.entry->route!=job.task.route){if(job.after==After::peer_get)send_error(JournalError::conflict);else notify(JournalError::conflict);return;}
        switch(job.after){
            case After::local_admit:
                trace(CommandTracePoint::sender_admission,CommandTraceReason::none,job.entry?unsigned(job.entry->state):0,{},job.entry?job.entry->owner_epoch:Identity{});
                if(!job.entry){fail(EndpointFault::protocol);break;}
                if(!track(*job.entry,true)){notify(JournalError::busy);break;}
                job.sender_ticket=std::move(reply.ticket);
                if(job.sender_ticket)job.stage=Stage::send_command;
                else notify(); // Duplicate/recovered intent is queried, never resent.
                break;
            case After::local_get:
            case After::peer_observed_get:
                if(!job.entry||!track(*job.entry,job.after==After::local_get)){notify(JournalError::busy);break;}
                notify();break;
            case After::peer_error_get:break; // Completed above without journal mutation.
            case After::peer_observe:rpc(request(WorkerOperation::get),After::peer_observed_get);break;
            case After::peer_admit:
                if(!job.entry){fail(EndpointFault::protocol);break;}
                send_status(reply.journal.inserted&&job.entry->state==CommandState::accepted,terminal(*job.entry));break;
            case After::peer_expire:
                if(!job.entry||(reply.journal.inserted&&(job.entry->state!=CommandState::expired||job.entry->reason!=CommandReason::start_deadline||job.entry->result.valid||job.entry->dispatched_ns))){fail(EndpointFault::protocol);break;}
                send_status(false,terminal(*job.entry));break; // Existing records remain authoritative; never dispatch.
            case After::peer_get:if(job.entry)send_status(false,false);else notify(JournalError::not_found);break;
            case After::dispatch:
                if(job.entry&&job.entry->state==CommandState::dispatching&&reply.dispatch){job.dispatch_ticket=std::move(reply.dispatch);check_stage(true);}
                else if(job.entry&&terminal(*job.entry))send_status();
                else decline(SessionError::obsolete_connection,true);
                break;
            case After::finish:
            case After::decline:if(job.entry)send_status();else notify(JournalError::invalid_state);break;
            case After::invalidate:job={};break;
            case After::abandoned:rpc(request(WorkerOperation::get),After::local_get);break;
        }
    }
    bool query_due(){
        const auto snapshot=transport.snapshot();if(!sender||!active(snapshot.state)||zero(snapshot.context.session))return false;
        for(std::size_t n=0;n<tracks.size();++n){const auto at=(track_cursor+n)%tracks.size();auto& value=tracks[at];
            if(!value.used||value.suspended_session==snapshot.context.session||(value.queried_session==snapshot.context.session&&now()<value.next))continue;
            const auto result=transport.submit_query(snapshot.context,value.route,value.id);
            if(result==SubmitResult::queued){value.queried_session=snapshot.context.session;value.next=now()+1000000000ULL;track_cursor=(at+1)%tracks.size();++current.queries_sent;return true;}
            if(result==SubmitResult::busy)return true;
        }
        return false;
    }
    void idle(){
        if(lost_count){auto q=request(WorkerOperation::invalidate_session);q.session=lost[lost_head];trace(CommandTracePoint::invalidate_requested,CommandTraceReason::session_changed,0,q.session);lost[lost_head]={};lost_head=(lost_head+1)%lost.size();--lost_count;rpc(q,After::invalidate);return;}
        TransportMessage message;
        if(transport.poll_control(message)){
            job.message=message;job.task.id=message.envelope.request_id;job.task.route=message.envelope.route_id;job.task.context=message.context;
            if(sender&&message.envelope.kind==Kind::status){auto decoded=decode_command_status(message.envelope.route_id,message.body());if(!decoded){fail(EndpointFault::protocol);return;}auto q=request(WorkerOperation::observe_remote);q.remote_status=*decoded;rpc(q,After::peer_observe);}
            else if(sender&&message.envelope.kind==Kind::error){auto decoded=decode_control_error(message.body());if(!decoded){fail(EndpointFault::protocol);return;}job.received_error=*decoded;++current.peer_errors;
                trace(CommandTracePoint::peer_error_received,CommandTraceReason::none,unsigned(decoded->code),message.context.session,{},unsigned(decoded->request_kind),decoded->request_sequence);
                rpc(request(WorkerOperation::get),After::peer_error_get);}
            else if(!sender&&message.envelope.kind==Kind::query)rpc(request(WorkerOperation::get),After::peer_get);
            else if(!sender&&message.envelope.kind==Kind::command){auto decoded=decode_rate_command(message.body());if(!decoded){fail(EndpointFault::protocol);return;}
                auto q=request(WorkerOperation::admit);q.command=*decoded;q.context={message.context.session,message.envelope.source_epoch,message.envelope.source_monotonic_ns,message.deadline_ns};if(message.expiry_only&&(!message.deadline_ns||message.deadline_ns>=message.evaluated_ns||message.deadline_ns>=now())){fail(EndpointFault::protocol);return;}
                rpc(q,message.expiry_only?After::peer_expire:After::peer_admit);}
            else fail(EndpointFault::protocol);
            return;
        }
        query_turn=!query_turn;if(query_turn&&query_due())return;
        Task task;bool found=false;
        {std::lock_guard lock(mutex);if(input_count){task=input[input_head];input[input_head]={};input_head=(input_head+1)%input.size();--input_count;found=true;}}
        if(found){
            job.task=task;
            if(task.execute){auto q=request(WorkerOperation::admit);q.command=task.command;q.context={task.context.session,options.worker.journal.process_epoch,task.origin,task.origin+std::uint64_t(task.command.budget_ms)*1000000};rpc(q,After::local_admit);}
            else rpc(request(WorkerOperation::get),After::local_get);
        }else query_due();
    }
    void advance(JournalWorker& worker){
        switch(job.stage){
            case Stage::idle:idle();break;
            case Stage::rpc_submit:{const auto submitted=worker.submit(job.request);
                if(submitted.result==WorkerSubmit::queued){job.worker_token=submitted.token;job.sent_ns=now();job.stage=Stage::rpc_wait;}
                else if(submitted.result!=WorkerSubmit::busy)fail(EndpointFault::worker);
                break;}
            case Stage::rpc_wait:if(now()-job.sent_ns>=options.operation_timeout_ns)fail(EndpointFault::timeout);break;
            case Stage::send_command:{
                const auto result=transport.submit_command(job.task.context,std::move(*job.sender_ticket));
                if(result==SubmitResult::busy)break;
                trace(CommandTracePoint::submit_result,CommandTraceReason::none,unsigned(result),job.task.context.session);
                if(result==SubmitResult::queued){++current.commands_sent;notify();}
                else{auto q=request(WorkerOperation::invalidate_session);q.session=job.task.context.session;trace(CommandTracePoint::invalidate_requested,CommandTraceReason::abandoned_submit,unsigned(result),q.session);rpc(q,After::abandoned);}break;}
            case Stage::send_status:{
                if(!job.entry){fail(EndpointFault::protocol);break;}
                const bool withhold=options.test_withhold_final_status&&job.message.envelope.kind==Kind::command&&terminal(*job.entry);
                const auto result=withhold?SubmitResult::queued:transport.submit_status(job.message.context,job.entry->route,job.entry->request_id,status(*job.entry));
                if(result==SubmitResult::busy)break;
                if(job.dispatch_after_status)check_stage(false);
                else if(job.notify_after_status)notify();else job={};
                break;}
            case Stage::send_error:{
                const auto result=transport.submit_error(job.message.context,job.task.route,job.task.id,*job.outgoing_error);
                if(result!=SubmitResult::busy)job={};
                break;}
            case Stage::precheck_submit:
            case Stage::start_submit:{
                const bool start=job.stage==Stage::start_submit;
                const auto result=start?transport.request_command_start(job.message.context,job.message.envelope,*job.dispatch_ticket,job.check_token):transport.request_command_check(job.message.context,job.message.envelope,job.check_token);
                if(start&&result!=SubmitResult::busy)trace_start(CommandTracePoint::start_submission,unsigned(result));
                if(result==SubmitResult::busy)break;
                if(result==SubmitResult::queued){job.sent_ns=now();job.stage=start?Stage::start_wait:Stage::precheck_wait;}
                else decline(SessionError::obsolete_connection,start);
                break;}
            case Stage::precheck_wait:
            case Stage::start_wait:{
                const bool start=job.stage==Stage::start_wait;CommandCheck check;
                if(transport.poll_command_check(check)){
                    if(check.token!=job.check_token){fail(EndpointFault::protocol);break;}
                    if(start)job.start_check=check;
                    if(!check.fresh()||(start&&!check.start_granted))decline(check.error,start);
                    else if(start)job.stage=Stage::execute_submit;
                    else{auto q=request(WorkerOperation::begin_dispatch);q.session=job.message.context.session;q.clock_qualified=true;rpc(q,After::dispatch);}
                }else if(now()-job.sent_ns>=options.operation_timeout_ns)fail(EndpointFault::timeout);
                break;}
            case Stage::execute_submit:{const auto submitted=worker.submit_execute(std::move(*job.dispatch_ticket));
                if(submitted.result!=WorkerSubmit::busy)trace_start(CommandTracePoint::execute_submission,unsigned(submitted.result),submitted.token);
                if(submitted.result==WorkerSubmit::queued){job.worker_token=submitted.token;job.sent_ns=now();job.after=After::finish;job.stage=Stage::rpc_wait;}
                else if(submitted.result!=WorkerSubmit::busy)fail(EndpointFault::worker);
                break;}
            case Stage::event:emit();break;
        }
    }
    void run()noexcept{
        std::unique_ptr<JournalWorker> worker;
        try{
            trace(CommandTracePoint::endpoint_started);worker=std::make_unique<JournalWorker>(options.worker);current.running=true;const auto startup=now();bool seen_transport=false;
            while(!stopping.load()){
                if(resume_test.exchange(false))worker->resume_test_barrier();
                context_changes();WorkerReply reply;for(unsigned n=0;n<8&&worker->poll(reply);++n)completion(std::move(reply));
                if(worker->state()==WorkerState::failed){fail(EndpointFault::worker);break;}
                const auto network=transport.snapshot();seen_transport=seen_transport||network.running;
                if(seen_transport&&!network.running){fail(EndpointFault::transport);break;}
                if(worker->state()==WorkerState::ready)advance(*worker);
                else if(now()-startup>=5000000000ULL){fail(EndpointFault::timeout);break;}
                publish(worker.get());std::this_thread::sleep_for(std::chrono::milliseconds(2));
            }
        }catch(...){fail(EndpointFault::internal);}
        trace(CommandTracePoint::endpoint_stopping,CommandTraceReason::shutdown,unsigned(current.fault));
        transport.request_stop();
        if(worker){worker->request_stop();if(!worker->join())current.fault=EndpointFault::shutdown_timeout;}
        transport.join();
        {std::lock_guard lock(mutex);if(!zero(job.task.id)){
            if(job.entry&&terminal(*job.entry)&&job.error==JournalError::none)shutdown_event=CommandEvent{job.entry->request_id,job.entry->route,JournalError::none,job.entry};
            else shutdown_event=CommandEvent{job.task.id,job.task.route,job.error==JournalError::none?JournalError::context_lost:job.error,{},job.received_error,job.received_error?job.message.context:TransportContext{}};
        }}
        trace(CommandTracePoint::endpoint_stopped,CommandTraceReason::shutdown,unsigned(current.fault));
        job={};current.running=false;publish(worker.get());
    }
    SubmitResult enqueue(Task task){
        if(stopping.load())return SubmitResult::stopped;
        std::unique_lock lock(mutex,std::try_to_lock);if(!lock.owns_lock())return SubmitResult::busy;
        if(stopping.load())return SubmitResult::stopped;
        if(!shared.ready)return SubmitResult::obsolete;
        if(input_count==input.size())return SubmitResult::busy;
        input[(input_head+input_count++)%input.size()]=task;return SubmitResult::queued;
    }
};
CommandEndpoint::CommandEndpoint(EndpointOptions options):impl_(std::make_unique<Impl>(std::move(options))){}
CommandEndpoint::~CommandEndpoint()=default;
SubmitResult CommandEndpoint::execute(std::uint32_t route,Identity id,RateCommand command,std::uint64_t ingress){
    const auto* definition=impl_->options.transport.session.manifest.find(route);const auto time=now();
    if(!impl_->sender||zero(id)||!valid_command(command)||!definition||!definition->enabled||definition->kind!=RouteKind::command||definition->budget_ms!=command.budget_ms||!ingress||ingress>time||time-ingress>=std::uint64_t(command.budget_ms)*1000000)return SubmitResult::invalid;
    return impl_->enqueue({true,id,route,command,ingress,impl_->transport.snapshot().context});
}
SubmitResult CommandEndpoint::query(std::uint32_t route,Identity id){const auto* definition=impl_->options.transport.session.manifest.find(route);if(!impl_->sender||zero(id)||!definition||!definition->enabled||definition->kind!=RouteKind::command)return SubmitResult::invalid;return impl_->enqueue({false,id,route,{},0,impl_->transport.snapshot().context});}
bool CommandEndpoint::poll(CommandEvent& event){
    std::lock_guard lock(impl_->mutex);
    if(impl_->output_count){event=impl_->output[impl_->output_head];impl_->output[impl_->output_head]={};impl_->output_head=(impl_->output_head+1)%impl_->output.size();--impl_->output_count;return true;}
    // After join, report unresolved local work from its already bounded storage.
    // These are local context-loss notifications, never device nonexecution proof.
    if(!impl_->shared.running&&impl_->stopping.load()){
        if(impl_->shutdown_event){event=*impl_->shutdown_event;impl_->shutdown_event.reset();
            if(event.entry&&terminal(*event.entry))for(auto& track:impl_->tracks)if(track.used&&track.id==event.request_id){track={};if(impl_->shared.tracked)--impl_->shared.tracked;}
            return true;
        }
        if(impl_->input_count){const auto task=impl_->input[impl_->input_head];impl_->input[impl_->input_head]={};impl_->input_head=(impl_->input_head+1)%impl_->input.size();--impl_->input_count;impl_->shared.queued=impl_->input_count;event={task.id,task.route,JournalError::context_lost,{}};return true;}
        for(auto& track:impl_->tracks)if(track.used){event={track.id,track.route,JournalError::context_lost,{}};track={};if(impl_->shared.tracked)--impl_->shared.tracked;return true;}
    }
    return false;
}
EndpointSnapshot CommandEndpoint::snapshot()const{std::lock_guard lock(impl_->mutex);return impl_->shared;}
TransportOwner& CommandEndpoint::transport()noexcept{return impl_->transport;}
bool CommandEndpoint::resume_test_barrier()noexcept{
    if(!impl_->options.worker.test_pause_at&&!impl_->options.worker.test_handler_pause)return false;
    impl_->resume_test.store(true);return true;
}
void CommandEndpoint::request_stop()noexcept{impl_->stopping=true;impl_->transport.request_stop();}
void CommandEndpoint::join(){request_stop();if(impl_->thread.joinable())impl_->thread.join();}
}
