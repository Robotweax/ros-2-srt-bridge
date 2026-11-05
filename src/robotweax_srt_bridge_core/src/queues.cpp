#include <robotweax/srt_bridge/queues.hpp>
#include <algorithm>
#include <limits>

namespace robotweax::srt_bridge {
OutboundQueues::OutboundQueues(RouteManifest manifest):manifest_(std::move(manifest)) {
    std::size_t i=0;for(const auto& r:manifest_.routes())routes_[i++]=r.id;
}
bool OutboundQueues::current(Connection c) const noexcept {
    if(c.channel==Channel::control)return control_open_&&c.generation==control_generation_;
    return c.channel==Channel::sensor&&sensor_open_&&c.generation==sensor_generation_;
}
QueueError OutboundQueues::open(Connection c) {
    if(stopped_)return QueueError::stopped;
    if(c.channel!=Channel::control&&c.channel!=Channel::sensor)return QueueError::malformed;
    auto& generation=c.channel==Channel::control?control_generation_:sensor_generation_;
    auto& active=c.channel==Channel::control?control_open_:sensor_open_;
    if(!c.generation||c.generation<=generation)return QueueError::obsolete_connection;
    if(active||(c.channel==Channel::sensor&&!control_open_))return QueueError::busy;
    generation=c.generation;active=true;return QueueError::none;
}
QueueError OutboundQueues::control(Connection c,const Envelope& e,std::span<const std::byte> payload) {
    if(stopped_)return QueueError::stopped;
    if(c.channel!=Channel::control||!current(c))return QueueError::obsolete_connection;
    if(payload.size()>control_message_bytes-envelope_bytes)return QueueError::oversize;
    const bool application=e.kind==Kind::command||e.kind==Kind::status||e.kind==Kind::query||e.kind==Kind::error;
    if(application){
        const auto* route=manifest_.find(e.route_id);
        if(!route||route->kind!=RouteKind::command)return QueueError::unknown_route;
        if(!route->enabled)return QueueError::disabled_route;
        if(payload.size()>route->max_payload_bytes)return QueueError::oversize;
    }else if(payload.size()>management_payload_bytes)return QueueError::oversize;
    const bool command=e.kind==Kind::command;
    const auto size=envelope_bytes+payload.size();
    if(count_==64||size>262144-bytes_||(command&&(commands_==56||size>229376-command_bytes_))){
        ++stats_.control_busy;return QueueError::busy;
    }
    auto& slot=control_[(head_+count_)%control_.size()];
    const auto encoded=encode(e,payload,Channel::control,routes_,slot.bytes);
    if(!encoded)return QueueError::malformed;
    slot.connection=c;slot.envelope=e;slot.size=encoded.bytes_written;slot.deadline_ns=0;
    ++count_;bytes_+=slot.size;if(command){++commands_;command_bytes_+=slot.size;}
    return QueueError::none;
}
QueueError OutboundQueues::binding(Connection c,const Envelope& e,std::span<const std::byte> payload){
    if(stopped_)return QueueError::stopped;
    if(c.channel!=Channel::sensor||!current(c))return QueueError::obsolete_connection;
    if(e.kind!=Kind::bind||payload.size()>management_payload_bytes)return QueueError::malformed;
    if(!decode_management(Kind::bind,payload))return QueueError::malformed;
    QueuedPacket packet;const auto result=encode(e,payload,Channel::sensor,routes_,packet.bytes);
    if(!result)return QueueError::malformed;
    packet.connection=c;packet.envelope=e;packet.size=result.bytes_written;
    binding_=packet;binding_occupied_=true;return QueueError::none;
}
const QueuedPacket* OutboundQueues::control_front() const noexcept {return count_?&control_[head_]:nullptr;}
void OutboundQueues::control_sent() noexcept {
    if(!count_)return;
    auto& slot=control_[head_];bytes_-=slot.size;
    if(slot.envelope.kind==Kind::command){--commands_;command_bytes_-=slot.size;}
    slot={};head_=(head_+1)%control_.size();--count_;
}
QueueError OutboundQueues::sensor(Connection c,const Envelope& e,std::span<const std::byte> payload,std::uint64_t now) {
    if(stopped_)return QueueError::stopped;
    if(c.channel!=Channel::sensor||!current(c))return QueueError::obsolete_connection;
    if(now<last_sensor_time_||e.source_monotonic_ns>now)return QueueError::invalid_time;
    last_sensor_time_=now;
    const auto* route=manifest_.find(e.route_id);
    if(!route||route->kind!=RouteKind::sensor)return QueueError::unknown_route;
    if(!route->enabled)return QueueError::disabled_route;
    if(e.kind!=Kind::sample||!e.sequence||e.valid_for_ms!=route->budget_ms)return QueueError::malformed;
    if(payload.size()>route->max_payload_bytes)return QueueError::oversize;
    const auto budget=static_cast<std::uint64_t>(e.valid_for_ms)*1000000;
    if(e.source_monotonic_ns>std::numeric_limits<std::uint64_t>::max()-budget)return QueueError::invalid_time;
    const auto deadline=e.source_monotonic_ns+budget;
    if(now>=deadline||deadline-now<1000000){++stats_.sensor_expired;return QueueError::expired;}
    const auto index=static_cast<std::size_t>(route-manifest_.routes().data());
    if(occupied_[index]&&e.source_epoch==sensor_[index].envelope.source_epoch&&
       e.session_id==sensor_[index].envelope.session_id&&e.sequence<=sensor_[index].envelope.sequence){
        ++stats_.sensor_out_of_order;return QueueError::out_of_order;
    }
    // Encode into a temporary so a rejected replacement cannot corrupt the old sample.
    QueuedPacket packet;const auto encoded=encode(e,payload,Channel::sensor,routes_,packet.bytes);
    if(!encoded)return QueueError::malformed;
    packet.connection=c;packet.envelope=e;packet.size=encoded.bytes_written;packet.deadline_ns=deadline;
    if(occupied_[index])++stats_.sensor_replaced;
    sensor_[index]=packet;occupied_[index]=true;return QueueError::none;
}
int sensor_ttl_ms(const QueuedPacket& p,std::uint64_t now) noexcept {
    if(now>=p.deadline_ns)return 0;
    return static_cast<int>(std::min<std::uint64_t>((p.deadline_ns-now)/1000000,60000));
}
const QueuedPacket* OutboundQueues::sensor_front(std::uint64_t now) {
    if(stopped_||now<last_sensor_time_)return nullptr;
    last_sensor_time_=now;
    for(std::size_t n=0;n<sensor_.size();++n){
        const auto index=(sensor_cursor_+n)%sensor_.size();
        if(!occupied_[index])continue;
        if(!sensor_ttl_ms(sensor_[index],now)){occupied_[index]=false;sensor_[index]={};++stats_.sensor_expired;continue;}
        if(rate_started_[index]&&now<next_sample_ns_[index])continue;
        sensor_cursor_=index;return &sensor_[index];
    }
    return nullptr;
}
void OutboundQueues::sensor_sent(std::uint32_t route) noexcept {
    for(std::size_t i=0;i<routes_.size();++i)if(routes_[i]==route&&occupied_[i]){
        const auto interval=(1000000000ULL+manifest_.routes()[i].max_rate_hz-1)/manifest_.routes()[i].max_rate_hz;
        next_sample_ns_[i]=last_sensor_time_>std::numeric_limits<std::uint64_t>::max()-interval?
            std::numeric_limits<std::uint64_t>::max():last_sensor_time_+interval;
        rate_started_[i]=true;occupied_[i]=false;sensor_[i]={};sensor_cursor_=(i+1)%sensor_.size();return;
    }
}
void OutboundQueues::flush_sensor() noexcept {
    for(std::size_t i=0;i<occupied_.size();++i)if(occupied_[i]){++stats_.sensor_flushed;occupied_[i]=false;sensor_[i]={};}
}
DiscardedCommands OutboundQueues::apply(const SessionAction& action) noexcept {
    DiscardedCommands discarded;
    if(action.close_control){
        while(const auto* packet=control_front()){
            if(packet->envelope.kind==Kind::command)discarded.ids[discarded.count++]=packet->envelope.request_id;
            ++stats_.control_flushed;control_sent();
        }
        control_open_=sensor_open_=false;binding_sent();flush_sensor();
    }
    if(action.close_sensor){sensor_open_=false;binding_sent();flush_sensor();}
    if(action.flush_samples)flush_sensor();
    return discarded;
}
DiscardedCommands OutboundQueues::stop() noexcept {
    SessionAction action;action.close_control=action.close_sensor=action.flush_samples=true;
    auto discarded=apply(action);stopped_=true;return discarded;
}
}
