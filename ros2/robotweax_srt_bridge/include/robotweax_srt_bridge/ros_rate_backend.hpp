#pragma once
#include <robotweax/srt_bridge/handler.hpp>
#include <rclcpp/rclcpp.hpp>
#include <robotweax_srt_bridge_msgs/srv/apply_measurement_rate.hpp>
#include <chrono>
namespace core=robotweax::srt_bridge;
namespace robotweax::ros_bridge {
using Apply=robotweax_srt_bridge_msgs::srv::ApplyMeasurementRate;
inline std::uint64_t now(){return std::chrono::duration_cast<std::chrono::nanoseconds>(std::chrono::steady_clock::now().time_since_epoch()).count();}
class RosRateBackend final:public core::RateHandlerBackend {
    rclcpp::Context::SharedPtr context_;
    rclcpp::Node::SharedPtr node_;
    rclcpp::Client<Apply>::SharedPtr client_;
    std::unique_ptr<rclcpp::executors::SingleThreadedExecutor> executor_;
    core::HandlerSnapshot snapshot_{};
public:
    ~RosRateBackend()override{if(context_&&context_->is_valid())context_->shutdown("worker exit");}
    void initialize()override{
        context_=std::make_shared<rclcpp::Context>();context_->init(0,nullptr);rclcpp::NodeOptions options;options.context(context_);options.use_global_arguments(false);node_=std::make_shared<rclcpp::Node>("srt_rate_worker",options);
        client_=node_->create_client<Apply>("/robot/apply_measurement_rate");rclcpp::ExecutorOptions eo;eo.context=context_;executor_=std::make_unique<rclcpp::executors::SingleThreadedExecutor>(eo);executor_->add_node(node_);
    }
    core::HandlerSnapshot snapshot()const noexcept override{return snapshot_;}
    core::HandlerOutcome execute(const core::JournalEntry& entry,std::uint64_t deadline)override{
        if(now()>=deadline)return {core::CommandState::expired,core::CommandReason::start_deadline,{}};
        const auto wait=std::chrono::nanoseconds(std::min<std::uint64_t>(500000000ULL,deadline-now()));
        if(!client_->wait_for_service(wait))return {core::CommandState::failed,core::CommandReason::handler_failed,{}};
        if(now()>=deadline)return {core::CommandState::expired,core::CommandReason::start_deadline,{}};
        auto request=std::make_shared<Apply::Request>();for(std::size_t i=0;i<16;++i)request->request_id[i]=std::to_integer<unsigned>(entry.request_id[i]);for(std::size_t i=0;i<32;++i)request->payload_hash[i]=std::to_integer<unsigned>(entry.payload_hash[i]);
        request->rate_hz=entry.command.rate_hz;request->budget_ms=entry.command.budget_ms;request->expected_generation=entry.command.expected_generation;request->new_generation=entry.command.new_generation;request->start_deadline_ns=deadline;
        auto future=client_->async_send_request(request);
        if(executor_->spin_until_future_complete(future,std::chrono::milliseconds(1500))!=rclcpp::FutureReturnCode::SUCCESS){client_->remove_pending_request(future.request_id);return {};}
        const auto response=future.get();if(response->request_id!=request->request_id||response->payload_hash!=request->payload_hash)return {};
        if(response->current_rate_hz>=1&&response->current_rate_hz<=1000)snapshot_={{response->current_rate_hz,response->current_generation,true},response->effects};
        switch(response->outcome){
            case Apply::Response::SUCCEEDED:if(response->result_rate_hz==entry.command.rate_hz&&response->result_generation==entry.command.new_generation)return {core::CommandState::succeeded,core::CommandReason::none,{response->result_rate_hz,response->result_generation,true}};return {};
            case Apply::Response::GENERATION_CONFLICT:return {core::CommandState::failed,core::CommandReason::generation_conflict,{}};
            case Apply::Response::EXPIRED:return {core::CommandState::expired,core::CommandReason::start_deadline,{}};
            case Apply::Response::CAPACITY:case Apply::Response::INVALID:return {core::CommandState::failed,core::CommandReason::handler_failed,{}};
            default:return {};
        }
    }
};

}
