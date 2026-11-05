#include <robotweax_srt_bridge/dds_command_session.hpp>
#include <robotweax_srt_bridge/dds_inbox.hpp>
#include <robotweax_srt_bridge/ros_rate_backend.hpp>
#include <robotweax_srt_bridge_msgs/msg/dds_command_frame.hpp>
#include <robotweax_srt_bridge_msgs/msg/dds_command_state.hpp>
#include <robotweax_srt_bridge_msgs/srv/execute_command.hpp>
#include <robotweax_srt_bridge_msgs/srv/get_command_status.hpp>
#include <atomic>
#include <fstream>
#include <iostream>
#include <mutex>
#include <thread>
namespace core=robotweax::srt_bridge;
namespace rb=robotweax::ros_bridge;
namespace msgs=robotweax_srt_bridge_msgs;
namespace {
using Frame=msgs::msg::DdsCommandFrame;using Status=msgs::msg::CommandStatus;
using Execute=msgs::srv::ExecuteCommand;using Get=msgs::srv::GetCommandStatus;
std::uint64_t mono_ns(){return std::chrono::duration_cast<std::chrono::nanoseconds>(std::chrono::steady_clock::now().time_since_epoch()).count();}
template<std::size_t N> std::array<std::byte,N> bytes(const std::array<std::uint8_t,N>& a){std::array<std::byte,N> out{};std::transform(a.begin(),a.end(),out.begin(),[](auto b){return std::byte(b);});return out;}
template<std::size_t N> std::array<std::uint8_t,N> octets(const std::array<std::byte,N>& a){std::array<std::uint8_t,N> out{};std::transform(a.begin(),a.end(),out.begin(),[](auto b){return std::to_integer<unsigned>(b);});return out;}
core::Digest namespace_proof(){std::string input;for(const auto* path:{"/proc/sys/kernel/random/boot_id","/proc/self/timens_offsets"}){std::ifstream file(path);if(!file)throw std::runtime_error("common-VM clock namespace proof unavailable");input.append(std::istreambuf_iterator<char>(file),{});input.push_back('\0');}return rb::digest(std::as_bytes(std::span(input.data(),input.size())));}
core::RateCommand command(const Frame& f){return {f.rate_hz,f.budget_ms,f.expected_generation,f.new_generation};}
bool terminal(const core::JournalEntry& e){return e.state!=core::CommandState::local_queued&&e.state!=core::CommandState::accepted&&e.state!=core::CommandState::dispatching&&!(e.state==core::CommandState::unknown&&e.reason==core::CommandReason::reconcile_required);}
Status status(const core::JournalEntry& e){Status s;s.request_id=octets(e.request_id);s.route_id=e.route;s.found=true;s.state=unsigned(e.state);s.reason=unsigned(e.reason);s.revision=e.revision;s.rate_hz=e.command.rate_hz;s.expected_generation=e.command.expected_generation;s.new_generation=e.command.new_generation;s.result_valid=e.result.valid;s.result_rate_hz=e.result.rate_hz;s.result_generation=e.result.generation;return s;}
class DdsCommandNode final:public rclcpp::Node {
    const bool sender_;
    const core::Identity process_=core::random_identity();
    std::mutex authority_;rb::DdsCommandSession session_;
    std::atomic<bool> stop_{false},failed_{false},journal_ready_{false};
    std::atomic<std::uint64_t> commands_{0},queries_{0},dispatches_{0},starts_{0},drops_{0},rejected_{0},errors_{0},effects_{0};
    rclcpp::Publisher<Frame>::SharedPtr out_;rclcpp::Subscription<Frame>::SharedPtr in_;
    rclcpp::Publisher<msgs::msg::DdsCommandState>::SharedPtr states_;
    rclcpp::Service<Execute>::SharedPtr execute_;rclcpp::Service<Get>::SharedPtr get_;
    rclcpp::TimerBase::SharedPtr state_timer_;
    struct Task {unsigned kind=0;core::Identity id{},session{};core::RateCommand command{};std::uint64_t origin=0;bool refresh=false;Frame frame{};};
    rb::DdsInbox<Task> inbox_;
    struct Cached {bool used=false;Status value{};};std::mutex cache_mutex_;std::array<Cached,64> cache_{};std::size_t cursor_=0;
    struct Receipt {std::uint64_t sequence=0;core::Identity id{},session{};};std::array<Receipt,64> receipts_{};std::size_t receipt_cursor_=0;
    std::uint64_t sequence_=0;
    std::thread worker_;
    bool fresh(core::Identity id){std::lock_guard lock(authority_);return !stop_&&!failed_&&session_.fresh(id,mono_ns());}
    core::Identity context(){std::lock_guard lock(authority_);return session_.session();}
    void tick(){const auto replacement=core::random_identity();std::lock_guard lock(authority_);session_.tick(mono_ns(),replacement);if(session_.failed())failed_=true;}
    bool push(Task task){return inbox_.try_push(std::move(task));}
    bool pop(Task& task){return inbox_.pop(task);}
    Cached& slot(core::Identity id){for(auto& item:cache_)if(item.used&&bytes(item.value.request_id)==id)return item;auto& item=cache_[cursor_++%cache_.size()];item={};item.used=true;item.value.request_id=octets(id);item.value.route_id=100;return item;}
    void cache(core::Identity id,const core::JournalResult& r){if(r.error==core::JournalError::storage||r.error==core::JournalError::corrupt){++errors_;failed_=true;}std::lock_guard lock(cache_mutex_);auto& s=slot(id).value;if(r.entry)s=status(*r.entry);s.local_error=unsigned(r.error);s.query_queued=false;}
    void receive(const Frame& f){
        const auto replacement=core::random_identity();
        std::unique_lock lock(authority_);
        const auto time=mono_ns();session_.tick(time,replacement);
        const auto process=bytes(f.process_epoch),link=bytes(f.link_epoch),target=bytes(f.target_link),sid=bytes(f.session_id);const auto proof=bytes(f.clock_namespace);
        if(f.kind==Frame::HELLO){if(!session_.hello(process,link,target,sid,proof,f.sequence,f.sent_monotonic_ns,time))++rejected_;if(session_.failed())failed_=true;return;}
        if((sender_?f.kind!=Frame::STATUS&&f.kind!=Frame::ERROR:f.kind!=Frame::COMMAND&&f.kind!=Frame::QUERY)||f.route_id!=100||bytes(f.request_id)==core::Identity{}||!session_.frame(process,link,target,sid,proof,f.sequence,f.sent_monotonic_ns,time)){++rejected_;return;}
        lock.unlock();Task t;t.kind=3;t.frame=f;if(!inbox_.receive(std::move(t)))++drops_;
    }
    Frame frame(unsigned kind){Frame f;f.kind=kind;std::lock_guard lock(authority_);f.process_epoch=octets(process_);f.link_epoch=octets(session_.link());f.target_link=octets(session_.peer_link());f.session_id=octets(session_.session());f.clock_namespace=octets(session_.clock());return f;}
    bool send(Frame f,bool track=false){
        if(stop_||failed_||(f.kind!=Frame::HELLO&&!fresh(bytes(f.session_id))))return false;
        if(sequence_==UINT64_MAX){failed_=true;return false;}f.sequence=++sequence_;f.sent_monotonic_ns=mono_ns();
        // Only this journal worker publishes; no disk or DDS sends in callbacks.
        out_->publish(f);
        if(track)receipts_[receipt_cursor_++%receipts_.size()]={f.sequence,bytes(f.request_id),bytes(f.session_id)};
        return true;
    }
    void query(core::Identity id){auto f=frame(Frame::QUERY);f.route_id=100;f.request_id=octets(id);if(send(f,true))++queries_;}
    void reply(const Frame& request,const core::JournalResult& r){
        if(!fresh(bytes(request.session_id)))return;
        auto f=frame(r?Frame::STATUS:Frame::ERROR);f.route_id=request.route_id;f.request_id=request.request_id;f.reply_to_sequence=request.sequence;
        if(r){f.status=status(*r.entry);f.payload_hash=octets(r.entry->payload_hash);}else f.status.local_error=unsigned(r.error);
        send(f);
    }
    bool matched(const Frame& f){return std::any_of(receipts_.begin(),receipts_.end(),[&](const auto& r){return r.sequence==f.reply_to_sequence&&r.id==bytes(f.request_id)&&r.session==bytes(f.session_id);});}
    void peer(core::CommandJournal& journal,rb::RosRateBackend* backend,const Frame& f){
        if(!fresh(bytes(f.session_id)))return;
        const auto id=bytes(f.request_id);
        if(sender_){
            if(!matched(f)){++rejected_;return;}
            if(f.kind==Frame::ERROR){if(!f.status.local_error||f.status.local_error>unsigned(core::JournalError::corrupt)){++rejected_;return;}auto r=journal.get(id);if(r.entry)r.error=static_cast<core::JournalError>(f.status.local_error);cache(id,r);return;}
            const auto& s=f.status;core::CommandStatus remote{static_cast<core::CommandState>(s.state),static_cast<core::CommandReason>(s.reason),{s.rate_hz,5000,s.expected_generation,s.new_generation},bytes(f.payload_hash),{s.result_rate_hz,s.result_generation,s.result_valid},s.revision};
            if(!s.found||s.request_id!=f.request_id||s.route_id!=100||!core::valid_remote_status(100,remote)){++rejected_;return;}
            const auto result=journal.observe_remote(id,100,remote,mono_ns());auto r=journal.get(id);if(result!=core::JournalError::none)r.error=result;cache(id,r);return;
        }
        if(f.kind==Frame::QUERY){auto r=journal.get(id);if(r.entry&&r.entry->route!=100)r.error=core::JournalError::conflict;reply(f,r);return;}
        const auto cmd=command(f);const auto time=mono_ns();
        if(!core::valid_command(cmd)||cmd.budget_ms!=5000||!f.origin_monotonic_ns||f.origin_monotonic_ns>time||f.origin_monotonic_ns>UINT64_MAX-5000000000ULL||f.deadline_ns!=f.origin_monotonic_ns+5000000000ULL||bytes(f.payload_hash)!=core::command_hash(100,cmd)){++rejected_;return;}
        auto r=journal.admit(id,100,cmd,{bytes(f.session_id),bytes(f.process_epoch),f.origin_monotonic_ns,f.deadline_ns},time);reply(f,r);
        if(!r||!r.inserted||r.entry->state!=core::CommandState::accepted)return;
        if(!fresh(bytes(f.session_id))){r=journal.decline(id,core::CommandState::rejected,core::CommandReason::context_lost,mono_ns());reply(f,r);return;}
        r=journal.begin_dispatch(id,bytes(f.session_id),true,mono_ns());
        if(!r||r.entry->state!=core::CommandState::dispatching){reply(f,r);return;}++dispatches_;
        bool claimed=false;{
            // This is the atomic start boundary. Session expiry/rebinding and
            // stop use the same mutex. A post-claim revocation cannot undo an
            // already-started handler; uncertain outcomes remain UNKNOWN.
            std::lock_guard lock(authority_);const auto t=mono_ns();
            claimed=!stop_&&!failed_&&session_.fresh(r.entry->context.session,t)&&r.entry->owner_epoch==process_&&r.entry->context.source_epoch==session_.peer_process()&&t<r.entry->context.deadline_ns;
            if(claimed)++starts_;
        }
        core::HandlerOutcome outcome;
        if(claimed)outcome=backend->execute(*r.entry,r.entry->context.deadline_ns);
        else{const bool expired=mono_ns()>=r.entry->context.deadline_ns;outcome={expired?core::CommandState::expired:core::CommandState::rejected,expired?core::CommandReason::start_deadline:core::CommandReason::context_lost,{}};}
        r=journal.finish(id,outcome.state,outcome.reason,outcome.result,mono_ns());effects_=backend->snapshot().effects;
        // The accepted frame and this final result correlate to the same
        // original request. QUERY can recover a committed result if send fails.
        reply(f,r);
        if(!journal.healthy()){++errors_;failed_=true;}
    }
    void work(core::JournalOptions options)noexcept{
        try{
            core::CommandJournal journal(options);std::unique_ptr<rb::RosRateBackend> backend;
            if(!sender_){backend=std::make_unique<rb::RosRateBackend>();backend->initialize();}
            journal_ready_=true;core::Identity previous{};std::uint64_t hello_at=0;
            while(!stop_&&!failed_){
                if(!journal.healthy()){++errors_;failed_=true;break;}
                tick();const auto sid=context();if(previous!=core::Identity{}&&previous!=sid){if(journal.invalidate_session(previous,mono_ns())!=core::JournalError::none){++errors_;failed_=true;break;}}previous=sid;
                if(mono_ns()>=hello_at){send(frame(Frame::HELLO));hello_at=mono_ns()+100000000ULL;}
                Task task;if(!pop(task)){std::this_thread::sleep_for(std::chrono::milliseconds(2));continue;}
                if(task.kind==3){peer(journal,backend.get(),task.frame);continue;}
                if(task.kind==2){auto r=journal.get(task.id);cache(task.id,r);if(r.entry&&task.refresh&&!terminal(*r.entry))query(task.id);continue;}
                if(!fresh(task.session)){cache(task.id,{core::JournalError::context_lost});continue;}
                auto r=journal.admit(task.id,100,task.command,{task.session,process_,task.origin,task.origin+5000000000ULL},mono_ns());cache(task.id,r);
                if(!r)continue;
                if(r.inserted&&r.entry->state==core::CommandState::local_queued&&journal.sender_may_transmit(task.id,task.session,mono_ns())){
                    auto f=frame(Frame::COMMAND);f.session_id=octets(task.session);f.route_id=100;f.request_id=octets(task.id);f.origin_monotonic_ns=task.origin;f.deadline_ns=task.origin+5000000000ULL;f.rate_hz=task.command.rate_hz;f.budget_ms=5000;f.expected_generation=task.command.expected_generation;f.new_generation=task.command.new_generation;f.payload_hash=octets(r.entry->payload_hash);
                    if(send(f,true))++commands_;
                }else if(!terminal(*r.entry))query(task.id); // Never resend a duplicate/recovered intent.
            }
        }catch(const std::exception& e){RCLCPP_ERROR(get_logger(),"DDS command worker: %s",e.what());failed_=true;}
        journal_ready_=false;
    }
    void state(){msgs::msg::DdsCommandState s;{std::lock_guard lock(authority_);s.process_epoch=octets(process_);s.link_epoch=octets(session_.link());s.session_id=octets(session_.session());s.ready=!stop_&&!failed_&&journal_ready_&&session_.fresh(session_.session(),mono_ns());}s.journal_ready=journal_ready_;s.failed=failed_;s.commands_sent=commands_;s.queries_sent=queries_;s.dispatches=dispatches_;s.start_claims=starts_;s.inbox_drops=drops_;s.rejected_frames=rejected_;s.journal_errors=errors_;s.effects=effects_;states_->publish(s);}
public:
    DdsCommandNode():Node("dds_command_coordinator"),sender_(declare_parameter<std::string>("role","sender")=="sender"),session_(sender_,process_,core::random_identity(),namespace_proof()){
        const auto role=get_parameter("role").as_string();if(role!="sender"&&role!="receiver")throw std::invalid_argument("DDS role must be sender/receiver");
        const auto path=declare_parameter<std::string>("journal_path","");if(path.empty())throw std::invalid_argument("DDS journal path required");
        const auto qos=rclcpp::QoS(64).reliable().durability_volatile();out_=create_publisher<Frame>(sender_?"/dds/commands/operator":"/dds/commands/robot",qos);in_=create_subscription<Frame>(sender_?"/dds/commands/robot":"/dds/commands/operator",qos,[this](Frame::ConstSharedPtr f){receive(*f);});
        states_=create_publisher<msgs::msg::DdsCommandState>(sender_?"/dds/commands/sender/state":"/dds/commands/receiver/state",rclcpp::QoS(1).reliable().durability_volatile());
        if(sender_){execute_=create_service<Execute>("/bridge/execute_command",[this](Execute::Request::SharedPtr q,Execute::Response::SharedPtr r){r->request_id=q->request_id;const core::RateCommand cmd{q->rate_hz,5000,q->expected_generation,q->new_generation};const auto sid=context();if(q->route_id!=100||bytes(q->request_id)==core::Identity{}||!core::valid_command(cmd)){r->submission=Execute::Response::INVALID;return;}if(!journal_ready_||!fresh(sid)){r->submission=Execute::Response::NOT_READY;return;}Task t;t.kind=1;t.id=bytes(q->request_id);t.session=sid;t.command=cmd;t.origin=mono_ns();r->submission=push(t)?Execute::Response::QUEUED:Execute::Response::BUSY;});
            get_=create_service<Get>("/bridge/get_command_status",[this](Get::Request::SharedPtr q,Get::Response::SharedPtr r){const auto id=bytes(q->request_id);std::lock_guard lock(cache_mutex_);auto& s=slot(id).value;if(q->route_id!=100||id==core::Identity{}){s.local_error=unsigned(core::JournalError::invalid);}else if(!journal_ready_||failed_){s.local_error=unsigned(core::JournalError::context_lost);s.query_queued=false;}else if(!s.query_queued){Task t;t.kind=2;t.id=id;t.refresh=q->refresh;if(push(t))s.query_queued=true;else s.local_error=unsigned(core::JournalError::busy);}r->status=s;});}
        core::JournalOptions options;options.path=path;options.local_peer_id=sender_?"operator":"robot";options.remote_peer_id=sender_?"robot":"operator";options.side=sender_?core::JournalSide::sender:core::JournalSide::receiver;options.process_epoch=process_;
        worker_=std::thread([this,options]{work(options);});state_timer_=create_wall_timer(std::chrono::milliseconds(100),[this]{state();});
    }
    ~DdsCommandNode()override{{std::lock_guard lock(authority_);stop_=true;}if(worker_.joinable())worker_.join();}
};
}
int main(int argc,char** argv){rclcpp::init(argc,argv);try{auto node=std::make_shared<DdsCommandNode>();rclcpp::spin(node);node.reset();rclcpp::shutdown();return 0;}catch(const std::exception& e){std::cerr<<e.what()<<'\n';rclcpp::shutdown();return 1;}}
