// Native provider probe for the pinned M3 lab; never linked into bridge/simulator.
#include <rclcpp/rclcpp.hpp>
#include <rcl/node.h>
#include <rcl/publisher.h>
#include <sensor_msgs/msg/imu.hpp>
#include <sensor_msgs/msg/joint_state.hpp>
#include <robotweax_srt_bridge_msgs/msg/dds_command_frame.hpp>
#include <rmw_fastrtps_cpp/get_publisher.hpp>
#include <rmw_fastrtps_cpp/get_participant.hpp>
#include <fastdds/rtps/flowcontrol/FlowControllerDescriptor.hpp>
#include <iostream>
#include <stdexcept>
namespace native_dds=::eprosima::fastdds::dds;
namespace native_rtps=::eprosima::fastdds::rtps;
namespace {
void require(bool condition,const char* message){if(!condition)throw std::runtime_error(message);}
template<class Publisher> void check(const Publisher& publisher,bool sensor){
    auto* writer=rmw_fastrtps_cpp::get_datawriter(rcl_publisher_get_rmw_handle(publisher->get_publisher_handle().get()));require(writer,"native writer unavailable");
    const auto& q=writer->get_qos();
    require(q.publish_mode().kind==(sensor?native_dds::ASYNCHRONOUS_PUBLISH_MODE:native_dds::SYNCHRONOUS_PUBLISH_MODE),"publication mode mismatch");
    require(std::string(q.publish_mode().flow_controller_name)==(sensor?"m3_sensors_32k":native_rtps::FASTDDS_FLOW_CONTROLLER_DEFAULT),"flow controller mismatch");
    require(q.history().kind==native_dds::KEEP_LAST_HISTORY_QOS&&q.history().depth==(sensor?1:64),"history mismatch");
    require(q.reliability().kind==(sensor?native_dds::BEST_EFFORT_RELIABILITY_QOS:native_dds::RELIABLE_RELIABILITY_QOS),"reliability mismatch");
    require(q.durability().kind==native_dds::VOLATILE_DURABILITY_QOS,"durability mismatch");
    require(q.endpoint().history_memory_policy==::eprosima::fastrtps::rtps::PREALLOCATED_WITH_REALLOC_MEMORY_MODE,"memory policy mismatch");
    require(q.data_sharing().kind()==native_dds::OFF,"data sharing mismatch");
}
}
int main(int argc,char** argv){
    rclcpp::init(argc,argv);
    try{
        auto node=std::make_shared<rclcpp::Node>("m3_dds_profile_probe");
        auto* participant=rmw_fastrtps_cpp::get_domain_participant(rcl_node_get_rmw_handle(node->get_node_base_interface()->get_rcl_node_handle()));require(participant,"native participant unavailable");
        unsigned matches=0;for(const auto& flow:participant->get_qos().flow_controllers())if(std::string(flow->name)=="m3_sensors_32k"){
            require(flow->max_bytes_per_period==1600&&flow->period_ms==50&&flow->scheduler==native_rtps::FlowControllerSchedulerPolicy::FIFO,"flow descriptor mismatch");++matches;
        }
        require(matches==1,"exactly one sensor controller required");
        auto imu=node->create_publisher<sensor_msgs::msg::Imu>("/robot/imu",rclcpp::SensorDataQoS().keep_last(1));
        auto joints=node->create_publisher<sensor_msgs::msg::JointState>("/robot/joint_states",rclcpp::SensorDataQoS().keep_last(1));
        auto control=node->create_publisher<robotweax_srt_bridge_msgs::msg::DdsCommandFrame>("/dds/commands/operator",rclcpp::QoS(64).reliable().durability_volatile());
        check(imu,true);check(joints,true);check(control,false);
        std::cout<<"{\"verified\":true,\"sensor_topics\":[\"/robot/imu\",\"/robot/joint_states\"],\"sensor_mode\":\"ASYNCHRONOUS\",\"controller\":\"m3_sensors_32k\",\"max_bytes_per_period\":1600,\"period_ms\":50,\"control_mode\":\"SYNCHRONOUS\",\"control_controller\":\"default unlimited\",\"history_memory\":\"PREALLOCATED_WITH_REALLOC\",\"data_sharing\":\"OFF\"}\n";
        control.reset();joints.reset();imu.reset();node.reset();rclcpp::shutdown();return 0;
    }catch(const std::exception& e){std::cerr<<e.what()<<'\n';rclcpp::shutdown();return 1;}
}
