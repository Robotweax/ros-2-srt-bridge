#include <robotweax/srt_bridge/errors.hpp>
#include <robotweax/srt_bridge/session.hpp>
#include <robotweax/srt_bridge/commands.hpp>
#include <openssl/rand.h>
#include <algorithm>
#include <limits>
#include <stdexcept>

namespace robotweax::srt_bridge {
namespace {
constexpr std::uint64_t max_time = std::numeric_limits<std::int64_t>::max();
constexpr std::uint64_t handshake_ns = 3000000000, bind_ns = 3000000000, bind_retry_ns = 200000000, probe_timeout_ns = 2000000000;
bool zero(const Identity& id) { return std::all_of(id.begin(), id.end(), [](auto b) { return b == std::byte{}; }); }
bool soft_clock(ClockError error) { return error == ClockError::unqualified || error == ClockError::expired; }
}
Identity random_identity() {
    Identity result{};
    if (RAND_bytes(reinterpret_cast<unsigned char*>(result.data()), result.size()) != 1 || zero(result))
        throw std::runtime_error("cryptographic identity generation failed");
    return result;
}
Session::Session(SessionConfig config) : config_(std::move(config)), clock_(config_.clock) {
    std::array<std::byte,512> scratch{};
    if ((config_.role != Role::caller && config_.role != Role::listener) || zero(config_.local_epoch) ||
        config_.local_peer_id == config_.expected_peer_id || config_.manifest.routes().size() > config_.limits.routes ||
        !encode_management(Hello{config_.local_peer_id, config_.manifest.digest(), config_.limits}, scratch) ||
        !encode_management(Hello{config_.expected_peer_id, config_.manifest.digest(), config_.limits}, scratch))
        throw std::invalid_argument("invalid bridge session configuration");
}
SessionState Session::state() const noexcept {
    if (stopped_) return SessionState::stopped;
    if (failed_) return SessionState::failed;
    if (!control_up_) return SessionState::disconnected;
    if (!remote_known_) return config_.role == Role::caller ? SessionState::awaiting_welcome : SessionState::awaiting_hello;
    if (!control_ready()) return SessionState::synchronizing;
    if (bound_) return SessionState::active;
    return sensor_up_ ? SessionState::sensor_binding : SessionState::control_active;
}
bool Session::secure(Security s, Channel expected) const noexcept {
    return s.profile == expected && s.gcm && s.sessionauth_v2 && s.enforced_encryption;
}
bool Session::advance(std::uint64_t now) {
    if (now > max_time - handshake_ns || now < last_time_) return false;
    last_time_ = now; return true;
}
SessionAction Session::terminate(SessionError error, bool permanent) {
    const bool had_control = control_up_, had_sensor = sensor_up_;
    control_up_ = remote_known_ = local_ready_ = peer_ready_ = sensor_up_ = bound_ = false;
    pending_probe_.reset(); session_id_ = {}; binding_id_ = {}; remote_epoch_ = {};
    clock_.reset(config_.local_epoch, {}, config_.local_clock_domain, 0);
    failed_ = failed_ || permanent;
    return {error, {}, had_control, had_sensor, true};
}
SessionAction Session::emit(Management payload, Connection destination, std::uint64_t now) {
    if (management_tx_ == std::numeric_limits<std::uint64_t>::max()) return terminate(SessionError::sequence_exhausted, true);
    Envelope e;
    e.kind = kind_of(payload); e.session_id = e.kind == Kind::hello ? Identity{} : session_id_;
    e.source_epoch = config_.local_epoch; e.sequence = ++management_tx_;
    e.source_monotonic_ns = now; e.clock_domain = config_.local_clock_domain;
    return {SessionError::none, OutboundManagement{destination, e, std::move(payload)}};
}
SessionAction Session::control_connected(std::uint64_t generation, Security security, std::uint64_t now, Identity assigned) {
    if (failed_ || stopped_ || control_up_) return {SessionError::invalid_state};
    if (!generation || generation <= control_generation_) return {SessionError::obsolete_connection};
    if (!advance(now)) return terminate(SessionError::invalid_time, false);
    // Mark ownership first so a rejected newly connected socket is explicitly closed.
    control_generation_ = generation; control_up_ = true;
    if (!secure(security, Channel::control)) return terminate(SessionError::bad_security, true);
    if ((config_.role == Role::listener && (zero(assigned) || assigned == last_session_)) ||
        (config_.role == Role::caller && !zero(assigned))) return terminate(SessionError::invalid_identity, true);
    control_rx_ = sensor_rx_ = 0; pending_probe_.reset(); local_ready_ = peer_ready_ = remote_known_ = false;
    session_id_ = assigned; handshake_deadline_ = now + handshake_ns;
    if (config_.role == Role::listener) { last_session_ = assigned; return {}; }
    return emit(Hello{config_.local_peer_id, config_.manifest.digest(), config_.limits}, {Channel::control, generation}, now);
}
void Session::bind_remote(const Envelope& e) {
    if (e.source_epoch != last_remote_epoch_) route_rx_.fill(0);
    remote_epoch_ = last_remote_epoch_ = e.source_epoch;
    remote_domain_ = e.clock_domain; remote_known_ = true;
    clock_.reset(config_.local_epoch, remote_epoch_, config_.local_clock_domain, remote_domain_);
}
SessionError Session::parameters(const Hello& h) const noexcept {
    if (h.peer_id != config_.expected_peer_id) return SessionError::bad_peer;
    if (h.routes_sha256 != config_.manifest.digest()) return SessionError::manifest_mismatch;
    if (h.limits != config_.limits) return SessionError::limits_mismatch;
    return SessionError::none;
}
SessionError Session::identity(const Envelope& e) const noexcept {
    if (e.session_id != session_id_) return SessionError::stale_session;
    if (e.source_epoch != remote_epoch_) return SessionError::epoch_mismatch;
    if (e.clock_domain != remote_domain_) return SessionError::domain_mismatch;
    return SessionError::none;
}
SessionAction Session::sensor_connected(std::uint64_t generation, Security security, std::uint64_t now, Identity binding) {
    if (!control_up_ || !remote_known_ || sensor_up_ || failed_ || stopped_) return {SessionError::invalid_state};
    if (!generation || generation <= sensor_generation_) return {SessionError::obsolete_connection};
    if (!advance(now)) return terminate(SessionError::invalid_time, false);
    sensor_generation_ = generation; sensor_up_ = true; bound_ = false; sensor_rx_ = 0;
    if (!secure(security, Channel::sensor)) return terminate(SessionError::bad_security, true);
    if (config_.role == Role::caller) {
        if (!control_ready() || zero(binding) || binding == last_local_binding_) {
            sensor_up_ = false; return {SessionError::binding_mismatch, {}, false, true, true};
        }
        binding_id_ = last_local_binding_ = binding;
    } else if (!zero(binding)) {
        sensor_up_ = false; return {SessionError::binding_mismatch, {}, false, true, true};
    } else binding_id_ = {};
    bind_deadline_ = now + bind_ns; next_bind_ = now + bind_retry_ns;
    if (config_.role == Role::listener) return {};
    return emit(Bind{config_.local_epoch, remote_epoch_, binding_id_}, {Channel::sensor,generation}, now);
}
SessionAction Session::receive(Connection source, const MessageView& m, std::uint64_t now) {
    const auto& e = m.envelope;
    if (source.channel != Channel::control && source.channel != Channel::sensor) return {SessionError::malformed};
    if (!control_up_ || (source.channel == Channel::control ? source.generation != control_generation_ :
        !sensor_up_ || source.generation != sensor_generation_)) return {SessionError::obsolete_connection};
    if (!advance(now)) return terminate(SessionError::invalid_time, false);
    if (!control_ready() && now >= handshake_deadline_) return terminate(SessionError::handshake_timeout,false);
    if (e.route_id || !zero(e.request_id) || e.valid_for_ms || !e.sequence || e.source_monotonic_ns > max_time)
        return {SessionError::malformed};
    if ((source.channel == Channel::sensor) != (e.kind == Kind::bind)) return {SessionError::malformed};
    auto& high = source.channel == Channel::control ? control_rx_ : sensor_rx_;
    if (e.sequence <= high) return {SessionError::replay};
    if (e.kind != Kind::hello && e.kind != Kind::welcome) {
        if (!remote_known_) return {SessionError::invalid_state};
        if (const auto error = identity(e); error != SessionError::none) return {error};
    }
    const auto parsed = decode_management(e.kind, m.payload);
    if (!parsed) return {SessionError::malformed};
    if (e.kind == Kind::hello) {
        if (config_.role != Role::listener || remote_known_ || !zero(e.session_id)) return {SessionError::invalid_state};
        if (zero(e.source_epoch) || e.source_epoch == config_.local_epoch) return terminate(SessionError::invalid_identity, true);
        if (const auto error = parameters(std::get<Hello>(parsed.value)); error != SessionError::none) return terminate(error, true);
        high = e.sequence; bind_remote(e);
        return emit(Welcome{Hello{config_.local_peer_id,config_.manifest.digest(),config_.limits}, remote_epoch_,config_.local_epoch},
                    {Channel::control,control_generation_}, now);
    }
    if (e.kind == Kind::welcome) {
        if (config_.role != Role::caller || remote_known_) return {SessionError::invalid_state};
        const auto& w = std::get<Welcome>(parsed.value);
        if (zero(e.session_id) || e.session_id == last_session_ || w.caller_epoch != config_.local_epoch || w.listener_epoch != e.source_epoch)
            return terminate(SessionError::invalid_identity, true);
        if (const auto error = parameters(w.parameters); error != SessionError::none) return terminate(error, true);
        high = e.sequence; session_id_ = last_session_ = e.session_id; bind_remote(e); return {};
    }
    if (e.kind == Kind::time_probe) {
        high = e.sequence;
        return emit(TimeReply{std::get<TimeProbe>(parsed.value).initiator_send_ns,now,now}, {Channel::control,control_generation_}, now);
    }
    if (e.kind == Kind::time_reply) {
        const auto& reply = std::get<TimeReply>(parsed.value);
        high = e.sequence;
        if (!pending_probe_ || *pending_probe_ != reply.initiator_send_ns || now - *pending_probe_ >= probe_timeout_ns)
            return {SessionError::probe_not_pending};
        pending_probe_.reset();
        const auto result = clock_.observe({config_.local_epoch,remote_epoch_,config_.local_clock_domain,remote_domain_,
            reply.initiator_send_ns,reply.responder_receive_ns,reply.responder_send_ns,now});
        if (result != ClockError::none) return soft_clock(result) ? SessionAction{SessionError::clock_unqualified} : terminate(SessionError::clock_invalid, false);
        if (!local_ready_) {
            local_ready_ = true;
            return emit(Ready{ReadyPhase::control_ready,config_.manifest.digest(),{}}, {Channel::control,control_generation_}, now);
        }
        return {};
    }
    if (e.kind == Kind::ready) {
        const auto& r = std::get<Ready>(parsed.value);
        if (r.routes_sha256 != config_.manifest.digest()) return terminate(SessionError::manifest_mismatch, true);
        high = e.sequence;
        if (r.phase == ReadyPhase::control_ready) { peer_ready_ = true; return {}; }
        if (sensor_up_ && !bound_ && now >= bind_deadline_) {
            sensor_up_ = false; binding_id_ = {};
            return {SessionError::binding_timeout,{},false,true,true};
        }
        if (config_.role != Role::caller || !sensor_up_ || !control_ready() || r.sensor_binding_id != binding_id_)
            return {SessionError::binding_mismatch};
        bound_ = true; return {};
    }
    if (e.kind == Kind::bind) {
        if (config_.role != Role::listener || !control_ready()) return {SessionError::invalid_state};
        if (!bound_ && now >= bind_deadline_) {
            sensor_up_ = false; binding_id_ = {};
            return {SessionError::binding_timeout,{},false,true,true};
        }
        const auto& b = std::get<Bind>(parsed.value);
        if (b.caller_epoch != remote_epoch_ || b.listener_epoch != config_.local_epoch ||
            (zero(binding_id_) && b.sensor_binding_id == last_peer_binding_) ||
            (!zero(binding_id_) && b.sensor_binding_id != binding_id_)) return {SessionError::binding_mismatch};
        binding_id_ = last_peer_binding_ = b.sensor_binding_id; bound_ = true; high = e.sequence;
        return emit(Ready{ReadyPhase::sensor_bound,config_.manifest.digest(),binding_id_}, {Channel::control,control_generation_}, now);
    }
    return {SessionError::malformed};
}
SessionAction Session::begin_probe(std::uint64_t now) {
    if (!control_up_ || !remote_known_) return {SessionError::invalid_state};
    if (!advance(now)) return terminate(SessionError::invalid_time, false);
    if (pending_probe_ && now - *pending_probe_ >= probe_timeout_ns) pending_probe_.reset();
    if (pending_probe_) return {SessionError::probe_busy};
    if (ever_probed_ && now <= last_probe_start_) return {SessionError::invalid_time};
    ever_probed_ = true; last_probe_start_ = now; pending_probe_ = now;
    return emit(TimeProbe{now}, {Channel::control,control_generation_}, now);
}
SessionAction Session::tick(std::uint64_t now) {
    if (failed_ || stopped_ || !control_up_) return {};
    if (!advance(now)) return terminate(SessionError::invalid_time, false);
    if (!control_ready() && now >= handshake_deadline_) return terminate(SessionError::handshake_timeout, false);
    if (pending_probe_ && now - *pending_probe_ >= probe_timeout_ns) pending_probe_.reset();
    if (sensor_up_ && !bound_) {
        if (now >= bind_deadline_) {
            sensor_up_ = false; binding_id_ = {};
            return {SessionError::binding_timeout,{},false,true,true};
        }
        if (config_.role == Role::caller && now >= next_bind_) {
            next_bind_ = now + bind_retry_ns;
            return emit(Bind{config_.local_epoch,remote_epoch_,binding_id_}, {Channel::sensor,sensor_generation_}, now);
        }
    }
    if (remote_known_) {
        const auto error = clock_.check(now);
        if (error != ClockError::none)
            return soft_clock(error) ? SessionAction{SessionError::clock_unqualified,{},false,false,true} : terminate(SessionError::clock_invalid,false);
    }
    return {};
}
SessionAction Session::control_lost(std::uint64_t generation) {
    if (!control_up_ || generation != control_generation_) return {SessionError::obsolete_connection};
    return terminate(SessionError::none,false);
}
SessionAction Session::sensor_lost(std::uint64_t generation) {
    if (!sensor_up_ || generation != sensor_generation_) return {SessionError::obsolete_connection};
    sensor_up_ = bound_ = false; binding_id_ = {};
    return {SessionError::none,{},false,true,true};
}
SessionAction Session::stop() { auto result = terminate(SessionError::none,false); stopped_ = true; return result; }
bool Session::reactivate() {
    if (stopped_ || control_up_) return false;
    failed_ = false; return true;
}
std::size_t Session::route_index(std::uint32_t route) const noexcept {
    const auto routes = config_.manifest.routes();
    for (std::size_t i = 0; i < routes.size(); ++i) if (routes[i].id == route) return i;
    return routes.size();
}
SampleResult Session::make_control(Kind kind,std::uint32_t id,Identity request,std::size_t bytes,std::uint64_t origin,std::uint64_t now){
    if(!advance(now))return {terminate(SessionError::invalid_time,false),{}, {}};
    if(!control_ready()||zero(request))return {{SessionError::invalid_state},{},{}};
    if((kind!=Kind::command&&kind!=Kind::query&&kind!=Kind::status&&kind!=Kind::error)||
       ((kind==Kind::status||kind==Kind::error)!=(config_.role==Role::caller)))return {{SessionError::wrong_direction},{},{}};
    const auto index=route_index(id);if(index==config_.manifest.routes().size())return {{SessionError::unknown_route},{},{}};
    const auto& route=config_.manifest.routes()[index];
    if(!route.enabled)return {{SessionError::disabled_route},{},{}};
    if(route.kind!=RouteKind::command)return {{SessionError::wrong_direction},{},{}};
    if(bytes>route.max_payload_bytes)return {{SessionError::oversize},{},{}};
    if(kind==Kind::command){
        const auto error=clock_.check(now);
        if(error!=ClockError::none)return {soft_clock(error)?SessionAction{SessionError::clock_unqualified}:terminate(SessionError::clock_invalid,false),{}, {}};
        if(origin>now||now-origin>static_cast<std::uint64_t>(route.budget_ms)*1000000)return {{SessionError::stale_sample},{},{}};
    }
    if(route_tx_[index]==std::numeric_limits<std::uint64_t>::max())return {terminate(SessionError::sequence_exhausted,true),{}, {}};
    Envelope e;e.kind=kind;e.route_id=id;e.request_id=request;e.sequence=++route_tx_[index];e.session_id=session_id_;e.source_epoch=config_.local_epoch;e.clock_domain=config_.local_clock_domain;
    e.source_monotonic_ns=kind==Kind::command?origin:now;e.valid_for_ms=kind==Kind::command?route.budget_ms:0;return {{},e,{}};
}
SampleResult Session::check_command(const Envelope& e,std::uint64_t now){
    if(!advance(now))return {terminate(SessionError::invalid_time,false),{}, {}};
    if(!control_ready())return {{SessionError::invalid_state},{},{}};
    if(config_.role!=Role::caller||e.kind!=Kind::command||zero(e.request_id))return {{SessionError::wrong_direction},{},{}};
    if(const auto error=identity(e);error!=SessionError::none)return {{error},{},{}};
    const auto* route=config_.manifest.find(e.route_id);
    if(!route||route->kind!=RouteKind::command)return {{SessionError::unknown_route},{},{}};
    if(!route->enabled)return {{SessionError::disabled_route},{},{}};
    if(e.valid_for_ms!=route->budget_ms)return {{SessionError::malformed},{},{}};
    const auto age=clock_.age_of_remote(e.source_monotonic_ns,now);
    if(age.error!=ClockError::none)return {soft_clock(age.error)||age.error==ClockError::future_sample?SessionAction{SessionError::clock_unqualified}:terminate(SessionError::clock_invalid,false),{},age};
    if(!age.within_budget(static_cast<std::uint64_t>(route->budget_ms)*1000000))return {{SessionError::stale_sample},{},age};
    return {{},e,age,now};
}
SampleResult Session::admit_control(Connection source,const MessageView& m,std::uint64_t now){
    if(source!=Connection{Channel::control,control_generation_}||!control_up_)return {{SessionError::obsolete_connection},{},{}};
    if(!advance(now))return {terminate(SessionError::invalid_time,false),{}, {}};
    if(!control_ready())return {{SessionError::invalid_state},{},{}};
    const auto& e=m.envelope;
    if((e.kind!=Kind::command&&e.kind!=Kind::query&&e.kind!=Kind::status&&e.kind!=Kind::error)||
       ((e.kind==Kind::status||e.kind==Kind::error)!=(config_.role==Role::listener))||zero(e.request_id))return {{SessionError::wrong_direction},{},{}};
    if(const auto error=identity(e);error!=SessionError::none)return {{error},{},{}};
    const auto index=route_index(e.route_id);if(index==config_.manifest.routes().size())return {{SessionError::unknown_route},{},{}};
    const auto& r=config_.manifest.routes()[index];if(!r.enabled)return {{SessionError::disabled_route},{},{}};
    if(r.kind!=RouteKind::command)return {{SessionError::wrong_direction},{},{}};
    if(m.payload.size()>r.max_payload_bytes)return {{SessionError::oversize},{},{}};
    if(!e.sequence||e.sequence<=route_rx_[index])return {{SessionError::replay},{},{}};
    if(e.kind==Kind::command){auto command=decode_rate_command(m.payload);if(!command||command->budget_ms!=e.valid_for_ms)return {{SessionError::malformed},{},{}};}
    else if(e.valid_for_ms||(e.kind==Kind::query?!valid_query(m.payload):e.kind==Kind::error?!decode_control_error(m.payload):!decode_command_status(e.route_id,m.payload)))return {{SessionError::malformed},{},{}};
    route_rx_[index]=e.sequence;
    return e.kind==Kind::command?check_command(e,now):SampleResult{{},e,{}};
}
SampleResult Session::make_sample(std::uint32_t id, std::size_t bytes, std::uint64_t now) {
    if (!advance(now)) return {terminate(SessionError::invalid_time,false),{}, {}};
    if (config_.role != Role::caller) return {{SessionError::wrong_direction},{},{}};
    if (!control_ready() || !bound_) return {{SessionError::invalid_state},{},{}};
    const auto index = route_index(id);
    if (index == config_.manifest.routes().size()) return {{SessionError::unknown_route},{},{}};
    const auto& r = config_.manifest.routes()[index];
    if (!r.enabled) return {{SessionError::disabled_route},{},{}};
    if (r.kind != RouteKind::sensor) return {{SessionError::wrong_direction},{},{}};
    if (bytes > r.max_payload_bytes) return {{SessionError::oversize},{},{}};
    const auto quality = clock_.check(now);
    if (quality != ClockError::none) return {soft_clock(quality) ? SessionAction{SessionError::clock_unqualified,{},false,false,true} : terminate(SessionError::clock_invalid,false),{}, {}};
    if (route_tx_[index] == std::numeric_limits<std::uint64_t>::max()) return {terminate(SessionError::sequence_exhausted,true),{}, {}};
    Envelope e; e.kind = Kind::sample; e.route_id = id; e.session_id = session_id_;
    e.source_epoch = config_.local_epoch; e.clock_domain = config_.local_clock_domain;
    e.sequence = ++route_tx_[index]; e.source_monotonic_ns = now; e.valid_for_ms = r.budget_ms;
    return {{},e,{}};
}
SampleResult Session::admit_sample(Connection source, const MessageView& m, std::uint64_t now) {
    if (source != Connection{Channel::sensor,sensor_generation_} || !sensor_up_) return {{SessionError::obsolete_connection},{},{}};
    if (!advance(now)) return {terminate(SessionError::invalid_time,false),{}, {}};
    if (config_.role != Role::listener) return {{SessionError::wrong_direction},{},{}};
    if (!control_ready() || !bound_) return {{SessionError::invalid_state},{},{}};
    const auto& e = m.envelope;
    if (const auto error = identity(e); error != SessionError::none) return {{error},{},{}};
    const auto index = route_index(e.route_id);
    if (index == config_.manifest.routes().size()) return {{SessionError::unknown_route},{},{}};
    const auto& r = config_.manifest.routes()[index];
    if (!r.enabled) return {{SessionError::disabled_route},{},{}};
    if (e.kind != Kind::sample || r.kind != RouteKind::sensor || !zero(e.request_id) || e.valid_for_ms != r.budget_ms)
        return {{SessionError::malformed},{},{}};
    if (m.payload.size() > r.max_payload_bytes) return {{SessionError::oversize},{},{}};
    if (!e.sequence || e.sequence <= route_rx_[index]) return {{SessionError::replay},{},{}};
    const auto age = clock_.age_of_remote(e.source_monotonic_ns,now);
    if (age.error != ClockError::none) {
        if (soft_clock(age.error) || age.error == ClockError::future_sample) return {{SessionError::clock_unqualified,{},false,false,true},{},age};
        return {terminate(SessionError::clock_invalid,false),{},age};
    }
    if (!age.within_budget(static_cast<std::uint64_t>(r.budget_ms) * 1000000)) return {{SessionError::stale_sample},{},age};
    route_rx_[index] = e.sequence;
    return {{},e,age,now};
}
}
