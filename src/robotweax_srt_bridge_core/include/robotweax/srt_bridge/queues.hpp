#pragma once
#include <robotweax/srt_bridge/session.hpp>
#include <optional>

namespace robotweax::srt_bridge {
enum class QueueError { none, busy, oversize, malformed, obsolete_connection, unknown_route, disabled_route, expired, out_of_order, stopped, invalid_time };
struct QueuedPacket {
    Connection connection{};
    Envelope envelope{};
    std::array<std::byte,control_message_bytes> bytes{};
    std::size_t size=0;
    std::uint64_t deadline_ns=0;
    std::span<const std::byte> wire() const noexcept { return {bytes.data(),size}; }
};
struct QueueStats {
    std::uint64_t sensor_enqueue_expired=0;
    std::uint64_t sensor_replaced=0, sensor_expired=0, sensor_flushed=0, sensor_out_of_order=0;
    std::uint64_t control_busy=0, control_flushed=0;
};
struct DiscardedCommands {
    std::array<Identity,64> ids{};
    std::size_t count=0;
};
// Fixed storage, single owner. It records volatile queue admission only; COMMAND
// persistence/ACCEPTED/dispatch semantics belong to the journal, never this class.
class OutboundQueues {
public:
    explicit OutboundQueues(RouteManifest manifest);
    OutboundQueues(const OutboundQueues&)=delete;
    OutboundQueues& operator=(const OutboundQueues&)=delete;
    QueueError open(Connection connection);
    QueueError control(Connection connection,const Envelope& envelope,std::span<const std::byte> payload);
    QueueError sensor(Connection connection,const Envelope& envelope,std::span<const std::byte> payload,std::uint64_t now);
    QueueError binding(Connection connection,const Envelope& envelope,std::span<const std::byte> payload);
    const QueuedPacket* binding_front() const noexcept { return binding_occupied_ ? &binding_ : nullptr; }
    void binding_sent() noexcept { binding_occupied_=false; binding_={}; }
    const QueuedPacket* control_front() const noexcept;
    void control_sent() noexcept;
    const QueuedPacket* sensor_front(std::uint64_t now);
    void sensor_sent(std::uint32_t route) noexcept;
    DiscardedCommands apply(const SessionAction& action) noexcept;
    DiscardedCommands stop() noexcept;
    // Earliest eligibility of any occupied sample; null when empty.
    std::optional<std::uint64_t> sensor_due_ns(std::uint64_t now) const noexcept;
    std::size_t sensor_count() const noexcept;
    std::size_t control_count() const noexcept { return count_; }
    std::size_t control_bytes() const noexcept { return bytes_; }
    const QueueStats& stats() const noexcept { return stats_; }
private:
    RouteManifest manifest_;
    std::array<std::uint32_t,8> routes_{};
    std::array<QueuedPacket,64> control_{};
    std::array<QueuedPacket,8> sensor_{};
    std::array<bool,8> occupied_{},rate_started_{};
    std::array<std::uint64_t,8> next_sample_ns_{};
    QueuedPacket binding_{};
    bool binding_occupied_=false;
    std::uint64_t control_generation_=0,sensor_generation_=0,last_sensor_time_=0;
    bool control_open_=false,sensor_open_=false,stopped_=false;
    std::size_t head_=0,count_=0,bytes_=0,commands_=0,command_bytes_=0,sensor_cursor_=0;
    QueueStats stats_{};
    bool current(Connection connection) const noexcept;
    void flush_sensor() noexcept;
};
// Returns zero if less than one complete millisecond of SENSOR validity remains.
int sensor_ttl_ms(const QueuedPacket& packet,std::uint64_t now) noexcept;
}
