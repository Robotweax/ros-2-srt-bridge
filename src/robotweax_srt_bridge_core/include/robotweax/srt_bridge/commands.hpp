#pragma once
#include <robotweax/srt_bridge/wire.hpp>
#include <optional>
#include <string>

namespace robotweax::srt_bridge {
enum class CommandState : std::uint8_t { local_queued=1,accepted,dispatching,succeeded,failed,rejected,expired,unknown };
enum class CommandReason : std::uint8_t { none,context_lost,reconcile_required,start_deadline,generation_conflict,handler_failed,effect_uncertain };
struct RateCommand {
    std::uint32_t rate_hz=0,budget_ms=5000;
    std::uint64_t expected_generation=0,new_generation=1;
    bool operator==(const RateCommand&) const=default;
};
struct RateResult {
    std::uint32_t rate_hz=0;
    std::uint64_t generation=0;
    bool valid=false;
    bool operator==(const RateResult&) const=default;
};
struct CommandStatus {
    CommandState state=CommandState::unknown;
    CommandReason reason=CommandReason::none;
    RateCommand command{};
    Digest payload_hash{};
    RateResult result{};
    std::uint64_t revision=0;
    bool operator==(const CommandStatus&) const=default;
};
bool valid_command(const RateCommand&) noexcept;
bool valid_remote_status(std::uint32_t route,const CommandStatus&);
std::string rate_command_schema_hash();
Digest command_hash(std::uint32_t route,const RateCommand& command);
enum class CommandCodecError { none,malformed,invalid,oversize,output_too_small };
struct CommandEncoding {
    CommandCodecError error=CommandCodecError::none;
    std::size_t bytes_written=0;
    explicit operator bool() const noexcept{return error==CommandCodecError::none;}
};
std::optional<RateCommand> decode_rate_command(std::span<const std::byte> payload);
std::optional<CommandStatus> decode_command_status(std::uint32_t route,std::span<const std::byte> payload);
CommandEncoding encode_rate_command(const RateCommand&,std::span<std::byte> output);
CommandEncoding encode_command_status(std::uint32_t route,const CommandStatus&,std::span<std::byte> output);
// QUERY has no body; its request ID and route are in the fixed envelope.
bool valid_query(std::span<const std::byte> payload) noexcept;
}
