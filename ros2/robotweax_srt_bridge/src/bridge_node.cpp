#include <robotweax_srt_bridge/sensor_codec.hpp>
#include <robotweax_srt_bridge/publication_metrics.hpp>
#include <robotweax/srt_bridge/endpoint.hpp>
#include <robotweax_srt_bridge_msgs/msg/bridge_state.hpp>
#include <robotweax_srt_bridge_msgs/msg/command_status.hpp>
#include <robotweax_srt_bridge_msgs/srv/execute_command.hpp>
#include <robotweax_srt_bridge_msgs/srv/get_command_status.hpp>
#include <robotweax_srt_bridge_msgs/srv/get_bridge_metrics.hpp>
#include <rclcpp/rclcpp.hpp>
#include <fstream>
#include <iostream>
#include <sstream>
#include <sys/stat.h>
#include <filesystem>
namespace core=robotweax::srt_bridge;
namespace rb=robotweax::ros_bridge;
namespace msgs=robotweax_srt_bridge_msgs;
namespace {
using Imu=sensor_msgs::msg::Imu;using Joints=sensor_msgs::msg::JointState;
using Execute=msgs::srv::ExecuteCommand;using Get=msgs::srv::GetCommandStatus;using Status=msgs::msg::CommandStatus;
static_assert(Status::SUCCEEDED==unsigned(core::CommandState::succeeded));
static_assert(Execute::Response::QUEUED==unsigned(core::SubmitResult::queued));
static_assert(Execute::Response::NOT_READY==unsigned(core::SubmitResult::obsolete));
template<class Handle> bool sensor_qos(const Handle& handle){const auto q=handle->get_actual_qos().get_rmw_qos_profile();return q.reliability==RMW_QOS_POLICY_RELIABILITY_BEST_EFFORT&&q.durability==RMW_QOS_POLICY_DURABILITY_VOLATILE&&q.history==RMW_QOS_POLICY_HISTORY_KEEP_LAST&&q.depth==1;}
core::Identity identity(const std::array<std::uint8_t,16>& id){core::Identity out{};for(std::size_t i=0;i<16;++i)out[i]=std::byte(id[i]);return out;}
std::string credential(const std::string& path){struct stat st{};if(stat(path.c_str(),&st)||!S_ISREG(st.st_mode)||(st.st_mode&0077))throw std::runtime_error("credential file must be private regular file");std::ifstream file(path);std::string key;std::getline(file,key);if(!file||key.size()<10||key.size()>79)throw std::runtime_error("invalid credential file");return key;}
bool final(const Status& status){return status.found&&status.state!=Status::LOCAL_QUEUED&&status.state!=Status::ACCEPTED&&status.state!=Status::DISPATCHING&&!(status.state==Status::UNKNOWN&&status.reason==unsigned(core::CommandReason::reconcile_required));}
class BridgeNode final:public rclcpp::Node {
    std::unique_ptr<core::CommandEndpoint> endpoint_;
    bool caller_=false,sensor_qos_verified_=false;
    std::shared_ptr<core::CommandTrace> command_trace_;
    std::shared_ptr<core::ProviderDiagnostics> provider_diagnostics_,sensor_provider_diagnostics_;
    std::shared_ptr<core::SampleTrace> sample_trace_;
    rclcpp::Subscription<Imu>::SharedPtr imu_in_;rclcpp::Subscription<Joints>::SharedPtr joints_in_;
    rclcpp::Publisher<Imu>::SharedPtr imu_out_;rclcpp::Publisher<Joints>::SharedPtr joints_out_;
    rclcpp::Publisher<msgs::msg::BridgeState>::SharedPtr diagnostics_;
    rclcpp::Service<Execute>::SharedPtr execute_;rclcpp::Service<Get>::SharedPtr get_;
    rclcpp::Service<msgs::srv::GetBridgeMetrics>::SharedPtr metrics_;
    rclcpp::TimerBase::SharedPtr pump_,state_timer_;
    struct Cached {bool used=false;Status status{};};std::array<Cached,64> cache_{};std::size_t cursor_=0;
    rb::PublicationMetrics imu_metrics_,joint_metrics_;
    std::uint32_t max_clock_interval_ms_=50;
    core::Identity local_epoch_{},imu_session_{},joint_session_{};
    std::uint64_t imu_ingress_=0,joint_ingress_=0,submit_busy_=0,submit_obsolete_=0;
    std::uint64_t ingress_=0,published_=0,invalid_=0,oversize_=0,stale_=0,context_=0,imu_seq_=0,joint_seq_=0;
    Cached& cache(const std::array<std::uint8_t,16>& id,std::uint32_t route){for(auto& c:cache_)if(c.used&&c.status.request_id==id&&c.status.route_id==route)return c;auto& c=cache_[cursor_];cursor_=(cursor_+1)%cache_.size();c={};c.used=true;c.status.request_id=id;c.status.route_id=route;return c;}
    template<class T> void ingress(std::uint32_t route,const T& message){const auto origin=core::TransportOwner::monotonic_ns();++ingress_;if constexpr(std::is_same_v<T,Imu>)++imu_ingress_;else ++joint_ingress_;
        bool large=message.header.frame_id.size()>64;
        if constexpr(std::is_same_v<T,Joints>){large=large||message.name.size()>6||message.position.size()>6||message.velocity.size()>6||message.effort.size()>6;for(const auto& n:message.name)large=large||n.size()>64;}
        if(large){++oversize_;return;}if(!rb::valid(message)){++invalid_;return;}rb::SensorBytes encoded;if(!rb::encode(message,encoded)){++invalid_;return;}
        const auto context=endpoint_->transport().snapshot().context;
        const auto before=sample_trace_?core::TransportOwner::monotonic_ns():0;
        const auto result=endpoint_->transport().submit_sample(context,route,std::span(encoded.bytes).first(encoded.size),origin);
        if(sample_trace_){core::SampleTraceEvent e;e.point=unsigned(core::SampleTracePoint::admission);e.begin_ns=before;e.end_ns=core::TransportOwner::monotonic_ns();e.origin_ns=origin;
            e.owner_epoch=local_epoch_;e.source_epoch=local_epoch_;e.session=context.session;e.control_generation=context.control_generation;e.sensor_generation=context.sensor_generation;
            e.route=route;e.callback_sequence=ingress_;e.bytes=encoded.size;e.result=unsigned(result);e.kind=unsigned(core::Kind::sample);
            e.stamp_sec=message.header.stamp.sec;e.stamp_nanosec=message.header.stamp.nanosec;sample_trace_->record(core::SampleTraceLane::ros,e);}
        if(result!=core::SubmitResult::queued){++context_;if(result==core::SubmitResult::busy)++submit_busy_;if(result==core::SubmitResult::obsolete)++submit_obsolete_;}
    }
    static std::string hex(core::Identity id){static constexpr char digits[]="0123456789abcdef";std::string out;for(auto b:id){const auto n=std::to_integer<unsigned>(b);out+=digits[n>>4];out+=digits[n&15];}return out;}
    void command_trace(){
        if(!command_trace_)return;
        core::CommandTraceEvent e;
        for(unsigned n=0;n<core::CommandTrace::capacity&&command_trace_->poll(e);++n){
            std::ostringstream line;line<<"COMMAND_TRACE {\"sequence\":"<<e.sequence<<",\"monotonic_ns\":"<<e.monotonic_ns
                <<",\"point\":"<<unsigned(e.point)<<",\"reason\":"<<unsigned(e.reason)<<",\"request\":\""<<hex(e.request)
                <<"\",\"session\":\""<<hex(e.session)<<"\",\"owner_epoch\":\""<<hex(e.owner_epoch)
                <<"\",\"control_generation\":"<<e.control_generation<<",\"sensor_generation\":"<<e.sensor_generation
                <<",\"route\":"<<e.route<<",\"detail\":"<<e.detail<<",\"value\":"<<e.value<<",\"entry_owner_epoch\":\""<<hex(e.entry_owner_epoch)
                <<"\",\"request_sequence\":"<<e.request_sequence<<",\"origin_ns\":"<<e.origin_ns<<",\"evaluated_ns\":"<<e.evaluated_ns
                <<",\"clock_deadline_ns\":"<<e.clock_deadline_ns<<",\"clock_error\":"<<e.clock_error<<",\"age_error\":"<<e.age_error<<",\"age_lower_ns\":"<<e.age_lower_ns<<",\"age_upper_ns\":"<<e.age_upper_ns
                <<",\"expiry_deadline_ns\":"<<e.expiry_deadline_ns<<",\"budget_ms\":"<<e.budget_ms<<"}";
            std::cout<<line.str()<<std::endl;
        }
    }
    void provider_diagnostics_stream(const std::shared_ptr<core::ProviderDiagnostics>& diagnostics,bool sensor){
        if(!diagnostics)return;
        core::ProviderObservation o;
        for(unsigned n=0;n<core::ProviderDiagnostics::capacity&&diagnostics->poll(o);++n){
            std::ostringstream line;line.precision(17);line<<(sensor?"SENSOR_PROVIDER_STATS {":"PROVIDER_STATS {");
            line<<"\"sequence\":"<<o.sequence;
            line<<",\"begin_ns\":"<<o.begin_ns;
            line<<",\"end_ns\":"<<o.end_ns;
            line<<",\"generation\":"<<o.generation;
            line<<",\"socket\":"<<o.socket;
            line<<",\"state_before\":"<<o.state_before;
            line<<",\"state_after\":"<<o.state_after;
            line<<",\"unavailable\":"<<o.unavailable;
            line<<",\"error\":"<<o.error;
            line<<",\"idle_timeout_ms\":"<<o.idle_timeout_ms;
            line<<",\"available\":"<<o.available;
            line<<",\"idle_timeout_available\":"<<o.idle_timeout_available;
            line<<",\"before_close\":"<<o.before_close;
            line<<",\"data_sent\":"<<o.data_sent;
            line<<",\"data_received\":"<<o.data_received;
            line<<",\"retransmitted\":"<<o.retransmitted;
            line<<",\"ack_sent\":"<<o.ack_sent;
            line<<",\"ack_received\":"<<o.ack_received;
            line<<",\"nak_sent\":"<<o.nak_sent;
            line<<",\"nak_received\":"<<o.nak_received;
            line<<",\"undecrypt\":"<<o.undecrypt;
            line<<",\"bytes_sent\":"<<o.bytes_sent;
            line<<",\"bytes_received\":"<<o.bytes_received;
            line<<",\"send_buffer_packets\":"<<o.send_buffer_packets;
            line<<",\"send_buffer_bytes\":"<<o.send_buffer_bytes;
            line<<",\"receive_buffer_packets\":"<<o.receive_buffer_packets;
            line<<",\"receive_buffer_bytes\":"<<o.receive_buffer_bytes;
            line<<",\"flight_packets\":"<<o.flight_packets;
            line<<",\"rtt_ms\":"<<o.rtt_ms;
            if(sensor){
                line<<",\"schema_version\":1,\"channel\":"<<o.channel;
                line<<",\"unique_sent\":"<<o.unique_sent;
                line<<",\"unique_received\":"<<o.unique_received;
                line<<",\"sender_loss\":"<<o.sender_loss;
                line<<",\"receiver_loss\":"<<o.receiver_loss;
                line<<",\"sender_drop\":"<<o.sender_drop;
                line<<",\"receiver_drop\":"<<o.receiver_drop;
                line<<",\"sender_filter_extra\":"<<o.sender_filter_extra;
                line<<",\"receiver_filter_extra\":"<<o.receiver_filter_extra;
                line<<",\"receiver_filter_supply\":"<<o.receiver_filter_supply;
                line<<",\"receiver_filter_loss\":"<<o.receiver_filter_loss;
                line<<",\"flow_window_packets\":"<<o.flow_window_packets;
                line<<",\"congestion_window_packets\":"<<o.congestion_window_packets;
            }
            line<<",\"owner_epoch\":\""<<hex(o.owner_epoch)<<"\",\"session\":\""<<hex(o.session)<<"\"}";
            std::cout<<line.str()<<std::endl;
        }
    }
    void provider_diagnostics(){
        provider_diagnostics_stream(provider_diagnostics_,false);
        provider_diagnostics_stream(sensor_provider_diagnostics_,true);
    }

    void sample_trace(){
        if(!sample_trace_)return;
        core::SampleTraceEvent e;
        for(unsigned n=0;n<core::SampleTrace::capacity&&sample_trace_->poll(e);++n){
            std::ostringstream out;out<<"SAMPLE_TRACE {\"sequence\":"<<e.sequence<<",\"point\":"<<e.point
                <<",\"begin_ns\":"<<e.begin_ns<<",\"end_ns\":"<<e.end_ns<<",\"origin_ns\":"<<e.origin_ns
                <<",\"owner_epoch\":\""<<hex(e.owner_epoch)<<"\",\"session\":\""<<hex(e.session)<<"\""
                <<",\"control_generation\":"<<e.control_generation<<",\"sensor_generation\":"<<e.sensor_generation
                <<",\"source_epoch\":\""<<hex(e.source_epoch)<<"\",\"envelope_sequence\":"<<e.envelope_sequence<<",\"callback_sequence\":"<<e.callback_sequence
                <<",\"route\":"<<e.route<<",\"bytes\":"<<e.bytes<<",\"kind\":"<<e.kind<<",\"result\":"<<e.result
                <<",\"stamp_sec\":"<<e.stamp_sec<<",\"stamp_nanosec\":"<<e.stamp_nanosec
                <<",\"socket\":"<<e.socket<<",\"message_number\":"<<e.message_number
                <<",\"initial_sequence\":"<<e.initial_sequence<<",\"initial_sequence_available\":"<<e.initial_sequence_available<<"}";
            std::cout<<out.str()<<std::endl;
        }
    }
    void events(){core::CommandEvent event;for(unsigned n=0;n<16&&endpoint_->poll(event);++n){std::array<std::uint8_t,16> id{};for(std::size_t i=0;i<16;++i)id[i]=std::to_integer<unsigned>(event.request_id[i]);auto& c=cache(id,event.route).status;
        c.query_queued=false;c.local_error=unsigned(event.error);c.peer_error=event.peer_error?unsigned(event.peer_error->code):0;
        if(event.entry){const auto& e=*event.entry;c.found=true;c.state=unsigned(e.state);c.reason=unsigned(e.reason);c.revision=e.revision;c.rate_hz=e.command.rate_hz;c.expected_generation=e.command.expected_generation;c.new_generation=e.command.new_generation;c.result_valid=e.result.valid;c.result_rate_hz=e.result.rate_hz;c.result_generation=e.result.generation;}
    }}
    void pump(){command_trace();provider_diagnostics();sample_trace();events();if(caller_)return;core::TransportMessage packet;for(unsigned n=0;n<8&&endpoint_->transport().poll_sample(packet);++n){
        if(packet.envelope.route_id==1){Imu message;if(!rb::decode(packet.body(),message)){++invalid_;continue;}if(core::TransportOwner::monotonic_ns()>=packet.deadline_ns){++stale_;continue;}if(!endpoint_->transport().authorize_sample(packet)){++context_;continue;}const auto age=250000000ULL-(packet.deadline_ns-core::TransportOwner::monotonic_ns());
            if(!imu_metrics_.observe(age)){++stale_;continue;}imu_out_->publish(message);imu_seq_=packet.envelope.sequence;imu_session_=packet.context.session;}
        else if(packet.envelope.route_id==2){Joints message;if(!rb::decode(packet.body(),message)){++invalid_;continue;}if(core::TransportOwner::monotonic_ns()>=packet.deadline_ns){++stale_;continue;}if(!endpoint_->transport().authorize_sample(packet)){++context_;continue;}const auto age=250000000ULL-(packet.deadline_ns-core::TransportOwner::monotonic_ns());
            if(!joint_metrics_.observe(age)){++stale_;continue;}joints_out_->publish(message);joint_seq_=packet.envelope.sequence;joint_session_=packet.context.session;}
        else{++invalid_;continue;}++published_;
    }}
    msgs::msg::BridgeState metrics(){const auto snapshot=endpoint_->snapshot();msgs::msg::BridgeState s;s.ready=snapshot.ready;s.sensor_qos_verified=sensor_qos_verified_;s.clock_qualified=snapshot.transport.clock_qualified;s.session_state=unsigned(snapshot.transport.state);s.fault=unsigned(snapshot.fault);s.worker_fault=unsigned(snapshot.worker_fault);for(std::size_t i=0;i<16;++i)s.session_id[i]=std::to_integer<unsigned>(snapshot.transport.context.session[i]);s.control_generation=snapshot.transport.context.control_generation;s.sensor_generation=snapshot.transport.context.sensor_generation;s.samples_ingress=ingress_;s.samples_published=published_;s.invalid_samples=invalid_;s.oversize_samples=oversize_;s.stale_samples=stale_;s.context_drops=context_;s.imu_sequence=imu_session_==snapshot.transport.context.session?imu_seq_:0;s.joint_sequence=joint_session_==snapshot.transport.context.session?joint_seq_:0;s.commands_sent=snapshot.commands_sent;s.queries_sent=snapshot.queries_sent;s.peer_errors=snapshot.peer_errors;
        for(std::size_t i=0;i<16;++i)s.owner_epoch[i]=std::to_integer<unsigned>(local_epoch_[i]);
        s.imu_ingress=imu_ingress_;s.joint_ingress=joint_ingress_;s.samples_submit_busy=submit_busy_;s.samples_submit_obsolete=submit_obsolete_;
        s.max_clock_interval_ms=max_clock_interval_ms_;s.transport_samples_received=snapshot.transport.samples_received;s.transport_samples_rejected=snapshot.transport.samples_rejected;s.transport_samples_unknown_age=snapshot.transport.samples_unknown_age;s.transport_samples_stale=snapshot.transport.samples_stale;s.transport_sensor_replaced=snapshot.transport.sensor_replaced;s.transport_rejected=snapshot.transport.rejected;
        s.imu_age_upper_histogram_ms=imu_metrics_.age_upper_ms;s.joint_age_upper_histogram_ms=joint_metrics_.age_upper_ms;s.imu_age_upper_max_ns=imu_metrics_.maximum_ns;s.joint_age_upper_max_ns=joint_metrics_.maximum_ns;
        s.sensor_submitted=snapshot.transport.sensor_submitted;
        s.sensor_ingress_replaced=snapshot.transport.sensor_ingress_replaced;
        s.sensor_ingress_flushed=snapshot.transport.sensor_ingress_flushed;
        s.sensor_inputs=snapshot.transport.sensor_inputs;
        s.sensor_input_rejected=snapshot.transport.sensor_input_rejected;
        s.sensor_outbound_replaced=snapshot.transport.sensor_outbound_replaced;
        s.sensor_outbound_expired=snapshot.transport.sensor_outbound_expired;
        s.sensor_outbound_flushed=snapshot.transport.sensor_outbound_flushed;
        s.sensor_sent=snapshot.transport.sensor_sent;
        s.sensor_receive_replaced=snapshot.transport.sensor_receive_replaced;
        s.sensor_receive_flushed=snapshot.transport.sensor_receive_flushed;
        s.sensor_polled=snapshot.transport.sensor_polled;
        s.sensor_poll_expired=snapshot.transport.sensor_poll_expired;
        s.sensor_ingress_pending=snapshot.transport.sensor_ingress_pending;
        s.sensor_outbound_pending=snapshot.transport.sensor_outbound_pending;
        s.sensor_receive_pending=snapshot.transport.sensor_receive_pending;
        return s;}
    void state(){diagnostics_->publish(metrics());}
public:
    BridgeNode():Node("srt_bridge"){
        const auto role=declare_parameter<std::string>("role","caller");if(role!="caller"&&role!="listener")throw std::runtime_error("role must be caller/listener");caller_=role=="caller";
        const auto imu_hash=rb::type_hash<Imu>(),joint_hash=rb::type_hash<Joints>();const auto expected_imu=declare_parameter<std::string>("expected_imu_hash",imu_hash),expected_joint=declare_parameter<std::string>("expected_joint_hash",joint_hash);if(expected_imu!=imu_hash||expected_joint!=joint_hash)throw std::runtime_error("ROS type hash mismatch");
        const auto imu_input=declare_parameter<std::string>("imu_input","/robot/imu"),imu_output=declare_parameter<std::string>("imu_output","/remote/robot/imu"),joint_input=declare_parameter<std::string>("joint_input","/robot/joint_states"),joint_output=declare_parameter<std::string>("joint_output","/remote/robot/joint_states");
        if(imu_input==imu_output||joint_input==joint_output||imu_input==joint_input||imu_output==joint_output)throw std::runtime_error("sensor topics must be distinct");
        const auto address=declare_parameter<std::string>("address","127.0.0.1");const auto control_port=declare_parameter<int>("control_port",10080),sensor_port=declare_parameter<int>("sensor_port",10081),domain=declare_parameter<int>("clock_domain",caller_?41:42);if(control_port<1||control_port>65535||sensor_port<1||sensor_port>65535||domain<0)throw std::runtime_error("invalid bridge address/clock configuration");
        const auto key=credential(declare_parameter<std::string>("credential_file",""));const auto peer=declare_parameter<std::string>("peer_id",caller_?"robot":"operator"),remote=declare_parameter<std::string>("expected_peer_id",caller_?"operator":"robot");const auto worker_path=declare_parameter<std::string>("worker_executable",caller_?(std::filesystem::read_symlink("/proc/self/exe").parent_path()/ROS_WORKER_EXECUTABLE).string():std::string(SDK_WORKER_EXECUTABLE));const auto journal=declare_parameter<std::string>("journal_path","");if(journal.empty())throw std::runtime_error("journal_path is required");
        core::Route imu;imu.id=1;imu.type_name="sensor_msgs/msg/Imu";imu.type_hash=imu_hash;core::Route joints=imu;joints.id=2;joints.type_name="sensor_msgs/msg/JointState";joints.type_hash=joint_hash;joints.max_rate_hz=50;
        core::Route command{100,core::RouteKind::command,core::Direction::listener_to_caller,core::QosMapping::request_status,true,4000,5000,0,1,"robotweax.srt_bridge.v1.SetMeasurementRateCommand",core::rate_command_schema_hash()};const std::array routes{imu,joints,command};auto manifest=core::make_manifest(routes);if(!manifest)throw std::runtime_error("invalid ROS route manifest");
        const auto clock_width=declare_parameter<int>("max_clock_interval_ms",50);if(clock_width<1||clock_width>1000)throw std::runtime_error("invalid maximum clock interval");max_clock_interval_ms_=std::uint32_t(clock_width);
        core::SessionConfig session{caller_?core::Role::caller:core::Role::listener,peer,remote,core::random_identity(),std::uint32_t(domain),*manifest.value,{1000,1000000,5000000000ULL,std::uint64_t(max_clock_interval_ms_)*1000000}};
        core::TransportConfig transport{session,{address,std::uint16_t(control_port)},{address,std::uint16_t(sensor_port)},key};core::WorkerOptions worker;worker.executable=worker_path;worker.journal.path=journal;worker.journal.local_peer_id=peer;worker.journal.remote_peer_id=remote;worker.journal.process_epoch=session.local_epoch;worker.journal.side=caller_?core::JournalSide::receiver:core::JournalSide::sender;worker.external_rate_handler=caller_;
        local_epoch_=session.local_epoch;
        if(declare_parameter<bool>("command_diagnostics",false)){command_trace_=std::make_shared<core::CommandTrace>();transport.command_trace=command_trace_;}
        if(declare_parameter<bool>("provider_diagnostics",false)){provider_diagnostics_=std::make_shared<core::ProviderDiagnostics>();transport.provider_diagnostics=provider_diagnostics_;}
        if(declare_parameter<bool>("sensor_provider_diagnostics",false)){sensor_provider_diagnostics_=std::make_shared<core::ProviderDiagnostics>();transport.sensor_provider_diagnostics=sensor_provider_diagnostics_;}
        if(declare_parameter<bool>("sample_diagnostics",false)){sample_trace_=std::make_shared<core::SampleTrace>();transport.sample_trace=sample_trace_;}
        endpoint_=std::make_unique<core::CommandEndpoint>(core::EndpointOptions{transport,worker});
        const auto qos=rclcpp::SensorDataQoS().keep_last(1);
        if(caller_){imu_in_=create_subscription<Imu>(imu_input,qos,[this](Imu::ConstSharedPtr m){ingress(1,*m);});joints_in_=create_subscription<Joints>(joint_input,qos,[this](Joints::ConstSharedPtr m){ingress(2,*m);});}
        else{
            imu_out_=create_publisher<Imu>(imu_output,qos);joints_out_=create_publisher<Joints>(joint_output,qos);
            execute_=create_service<Execute>("/bridge/execute_command",[this](Execute::Request::SharedPtr request,Execute::Response::SharedPtr response){response->request_id=request->request_id;const auto result=endpoint_->execute(request->route_id,identity(request->request_id),{request->rate_hz,5000,request->expected_generation,request->new_generation},core::TransportOwner::monotonic_ns());response->submission=unsigned(result);});
            get_=create_service<Get>("/bridge/get_command_status",[this](Get::Request::SharedPtr request,Get::Response::SharedPtr response){auto& c=cache(request->request_id,request->route_id).status;
                if((!c.found||(request->refresh&&!final(c)))&&!c.query_queued){const auto r=endpoint_->query(request->route_id,identity(request->request_id));c.query_queued=r==core::SubmitResult::queued;if(!c.query_queued)c.local_error=unsigned(r==core::SubmitResult::busy?core::JournalError::busy:core::JournalError::context_lost);}response->status=c;
            });
        }
        sensor_qos_verified_=caller_?(sensor_qos(imu_in_)&&sensor_qos(joints_in_)):(sensor_qos(imu_out_)&&sensor_qos(joints_out_));
        if(!sensor_qos_verified_)throw std::runtime_error("actual sensor QoS mismatch");
        metrics_=create_service<msgs::srv::GetBridgeMetrics>("/bridge/get_metrics",[this](msgs::srv::GetBridgeMetrics::Request::SharedPtr, msgs::srv::GetBridgeMetrics::Response::SharedPtr response){response->snapshot=metrics();response->monotonic_ns=core::TransportOwner::monotonic_ns();});
        diagnostics_=create_publisher<msgs::msg::BridgeState>("/bridge/state",rclcpp::QoS(1).reliable().durability_volatile());pump_=create_wall_timer(std::chrono::milliseconds(1),[this]{pump();});state_timer_=create_wall_timer(std::chrono::milliseconds(100),[this]{state();});
    }
    ~BridgeNode()override{pump_.reset();state_timer_.reset();if(endpoint_){endpoint_->request_stop();endpoint_->join();command_trace();provider_diagnostics();sample_trace();
            if(sample_trace_)std::cout<<"SAMPLE_TRACE_STATUS {\"schema_version\":2,\"attempted\":"<<sample_trace_->attempted()<<",\"dropped\":"<<sample_trace_->dropped()<<",\"exhausted\":"<<sample_trace_->exhausted()<<",\"limit\":"<<sample_trace_->limit()<<"}"<<std::endl;
            if(provider_diagnostics_)std::cout<<"PROVIDER_STATS_STATUS {\"attempted\":"<<provider_diagnostics_->attempted()<<",\"dropped\":"<<provider_diagnostics_->dropped()<<",\"exhausted\":"<<provider_diagnostics_->exhausted()<<",\"limit\":"<<provider_diagnostics_->limit()<<"}"<<std::endl;
            if(sensor_provider_diagnostics_)std::cout<<"SENSOR_PROVIDER_STATS_STATUS {\"schema_version\":1,\"channel\":1,\"attempted\":"<<sensor_provider_diagnostics_->attempted()<<",\"dropped\":"<<sensor_provider_diagnostics_->dropped()<<",\"exhausted\":"<<sensor_provider_diagnostics_->exhausted()<<",\"limit\":"<<sensor_provider_diagnostics_->limit()<<"}"<<std::endl;
            if(command_trace_)std::cout<<"COMMAND_TRACE_STATUS {\"attempted\":"<<command_trace_->attempted()<<",\"dropped\":"<<command_trace_->dropped()<<"}"<<std::endl;}}
};
}
int main(int argc,char** argv){rclcpp::init(argc,argv);try{auto node=std::make_shared<BridgeNode>();rclcpp::spin(node);node.reset();rclcpp::shutdown();return 0;}catch(const std::exception& e){std::cerr<<"bridge startup failed: "<<e.what()<<'\n';rclcpp::shutdown();return 1;}}
