#include <rclcpp/rclcpp.hpp>
#include "schedule.hpp"
#include <sensor_msgs/msg/imu.hpp>
#include <sensor_msgs/msg/joint_state.hpp>
#include <robotweax_srt_bridge_msgs/msg/simulator_state.hpp>
#include <robotweax_srt_bridge_msgs/srv/apply_measurement_rate.hpp>
#include <robotweax_srt_bridge_msgs/srv/set_publishing.hpp>
#include <robotweax/srt_bridge/commands.hpp>
#include <chrono>
#include <iostream>
#include <mutex>
#include <thread>
namespace core=robotweax::srt_bridge;
namespace msgs=robotweax_srt_bridge_msgs;
namespace {
using Apply=msgs::srv::ApplyMeasurementRate;
std::uint64_t monotonic_ns(){return std::chrono::duration_cast<std::chrono::nanoseconds>(std::chrono::steady_clock::now().time_since_epoch()).count();}
class Simulator final:public rclcpp::Node {
    std::mutex mutex_;
    bool enabled_=true;
    rclcpp::Service<msgs::srv::SetPublishing>::SharedPtr publishing_;
    std::uint32_t rate_=200;std::uint64_t generation_=0,effects_=0,imus_=0,joints_=0,next_imu_=0,next_joint_=0;
    struct Record {bool used=false;std::array<std::uint8_t,16> id{};std::array<std::uint8_t,32> hash{};std::uint8_t outcome=0;std::uint32_t rate=0;std::uint64_t generation=0;};
    std::array<Record,10000> records_{};std::size_t count_=0;
    rclcpp::CallbackGroup::SharedPtr device_group_,timer_group_;
    rclcpp::Service<Apply>::SharedPtr apply_;
    rclcpp::Publisher<sensor_msgs::msg::Imu>::SharedPtr imu_;
    rclcpp::Publisher<sensor_msgs::msg::JointState>::SharedPtr joint_;
    rclcpp::Publisher<msgs::msg::SimulatorState>::SharedPtr state_;
    rclcpp::TimerBase::SharedPtr publish_,state_timer_;
    void apply(const Apply::Request& q,Apply::Response& response){
        response.request_id=q.request_id;response.payload_hash=q.payload_hash;bool delay=false;
        {std::lock_guard lock(mutex_);Record* existing=nullptr;for(std::size_t i=0;i<count_;++i)if(records_[i].id==q.request_id){existing=&records_[i];break;}
            if(existing){response.payload_hash=existing->hash;response.outcome=existing->hash==q.payload_hash?existing->outcome:Apply::Response::ID_CONFLICT;response.result_rate_hz=existing->rate;response.result_generation=existing->generation;}
            else{
                const core::RateCommand command{q.rate_hz,q.budget_ms,q.expected_generation,q.new_generation};bool valid=core::valid_command(command);core::Digest hash{};
                if(valid)hash=core::command_hash(100,command);
                for(std::size_t i=0;i<32&&valid;++i)valid=std::to_integer<unsigned>(hash[i])==q.payload_hash[i];
                bool nonzero=false;for(auto byte:q.request_id)nonzero=nonzero||byte;
                if(!valid||!nonzero)response.outcome=Apply::Response::INVALID;
                else if(count_==records_.size())response.outcome=Apply::Response::CAPACITY;
                else{
                    if(monotonic_ns()>=q.start_deadline_ns)response.outcome=Apply::Response::EXPIRED;
                    else if(q.expected_generation!=generation_)response.outcome=Apply::Response::GENERATION_CONFLICT;
                    else{const bool changed=rate_!=q.rate_hz;rate_=q.rate_hz;generation_=q.new_generation;++effects_;if(changed){next_imu_=monotonic_ns();}response.outcome=Apply::Response::SUCCEEDED;response.result_rate_hz=rate_;response.result_generation=generation_;delay=true;}
                    records_[count_++]={true,q.request_id,q.payload_hash,response.outcome,response.result_rate_hz,response.result_generation};
                }
            }
            response.current_rate_hz=rate_;response.current_generation=generation_;response.effects=effects_;
        }
        // Demo-only response delay is outside all device locks and the sensor
        // callback group. It models a lost/unobserved reply after an actual effect.
        const auto milliseconds=get_parameter("response_delay_ms").as_int();if(delay&&milliseconds>0&&milliseconds<=5000)std::this_thread::sleep_for(std::chrono::milliseconds(milliseconds));
    }
    void publish(){
        const auto time=monotonic_ns();std::uint32_t rate;std::uint64_t generation,imu_count=0,joint_count=0;
        {std::lock_guard lock(mutex_);if(!enabled_)return;rate=rate_;generation=generation_;if(robotweax::srt_bridge_demo::periodic_due(next_imu_,time,1000000000ULL/rate_)){imu_count=++imus_;}if(robotweax::srt_bridge_demo::periodic_due(next_joint_,time,20000000)){joint_count=++joints_;}}
        if(imu_count){sensor_msgs::msg::Imu m;m.header.stamp=this->now();m.header.frame_id="demo_imu";m.orientation.w=1.;m.angular_velocity.x=rate;m.angular_velocity.y=generation;m.angular_velocity.z=imu_count;m.linear_acceleration.z=9.81;imu_->publish(m);}
        if(joint_count){sensor_msgs::msg::JointState m;m.header.stamp=this->now();m.header.frame_id="demo_base";for(unsigned i=0;i<6;++i){m.name.push_back("joint_"+std::to_string(i+1));m.position.push_back(double(i)+double(joint_count)/1000);m.velocity.push_back(rate);m.effort.push_back(generation);}joint_->publish(m);}
    }
    void state(){msgs::msg::SimulatorState s;{std::lock_guard lock(mutex_);s.rate_hz=rate_;s.generation=generation_;s.effects=effects_;s.imu_published=imus_;s.joints_published=joints_;}state_->publish(s);}
public:
    Simulator():Node("rate_simulator"){
        enabled_=declare_parameter<bool>("publishing_enabled",true);declare_parameter<int>("response_delay_ms",0);device_group_=create_callback_group(rclcpp::CallbackGroupType::Reentrant);timer_group_=create_callback_group(rclcpp::CallbackGroupType::MutuallyExclusive);
        const auto qos=rclcpp::SensorDataQoS().keep_last(1);imu_=create_publisher<sensor_msgs::msg::Imu>("/robot/imu",qos);joint_=create_publisher<sensor_msgs::msg::JointState>("/robot/joint_states",qos);state_=create_publisher<msgs::msg::SimulatorState>("/robot/simulator_state",rclcpp::QoS(1).reliable());
        apply_=create_service<Apply>("/robot/apply_measurement_rate",[this](Apply::Request::SharedPtr q,Apply::Response::SharedPtr response){apply(*q,*response);},rclcpp::ServicesQoS(),device_group_);
        // Serialized with the publish callback, including its actual ROS sends.
        // A disabled response therefore fences all previously started publishes.
        publishing_=create_service<msgs::srv::SetPublishing>("/robot/set_publishing",[this](msgs::srv::SetPublishing::Request::SharedPtr q,msgs::srv::SetPublishing::Response::SharedPtr r){
            std::lock_guard lock(mutex_);enabled_=q->enabled;r->enabled=enabled_;r->monotonic_ns=monotonic_ns();
            if(enabled_){next_imu_=r->monotonic_ns;next_joint_=r->monotonic_ns;}
            r->snapshot.rate_hz=rate_;r->snapshot.generation=generation_;r->snapshot.effects=effects_;r->snapshot.imu_published=imus_;r->snapshot.joints_published=joints_;
        },rclcpp::ServicesQoS(),timer_group_);
        publish_=create_wall_timer(std::chrono::milliseconds(1),[this]{publish();},timer_group_);state_timer_=create_wall_timer(std::chrono::milliseconds(100),[this]{state();},timer_group_);
    }
};
}
int main(int argc,char** argv){rclcpp::init(argc,argv);try{auto node=std::make_shared<Simulator>();rclcpp::executors::MultiThreadedExecutor executor(rclcpp::ExecutorOptions(),3);executor.add_node(node);executor.spin();executor.remove_node(node);node.reset();rclcpp::shutdown();return 0;}catch(const std::exception& e){std::cerr<<e.what()<<'\n';rclcpp::shutdown();return 1;}}
