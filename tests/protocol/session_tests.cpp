#include <robotweax/srt_bridge/session.hpp>
#include <array>
#include <iostream>
#include <limits>
#include <stdexcept>
using namespace robotweax::srt_bridge;
namespace {
unsigned checks = 0;
void check(bool b, const char* message) { ++checks; if (!b) throw std::runtime_error(message); }
Identity id(unsigned n) { Identity result{}; result[0] = static_cast<std::byte>(n); return result; }
RouteManifest manifest() {
    Route r; r.id=1; r.type_name="sensor_msgs/msg/Imu"; r.type_hash="RIHS01_"+std::string(64,'a');
    const auto result=make_manifest(std::span(&r,1)); check(bool(result),"manifest"); return *result.value;
}
SessionConfig config(Role role) {
    return {role,role==Role::caller?"robot":"operator",role==Role::caller?"operator":"robot",
            id(role==Role::caller?1:2),role==Role::caller?1U:2U,manifest(),{0,0,5000000000ULL,50000000}};
}
Security security(Channel c) { return {c,true,true,true}; }
struct Pair {
    Session c{config(Role::caller)}, l{config(Role::listener)};
    std::uint64_t now=1000000000, cg=1, lg=11, cs=1, ls=11;
    std::uint64_t next() { return now+=1000000; }
    SessionAction deliver(Session& receiver, SessionAction message, bool to_listener=true) {
        check(message.send.has_value(),"expected outbound management");
        std::array<std::byte,512> payload{};
        const auto packed=encode_management(message.send->payload,payload); check(bool(packed),"payload encoding");
        std::array<std::byte,4096> wire{}; const std::array<std::uint32_t,1> allowed{1};
        const auto encoded=encode(message.send->envelope,std::span(payload).first(packed.bytes_written),
                                  message.send->connection.channel,allowed,wire); check(bool(encoded),"wire encoding");
        const auto decoded=decode(std::span(wire).first(encoded.bytes_written),message.send->connection.channel,allowed);
        check(bool(decoded),"wire decoding");
        const auto channel=message.send->connection.channel;
        return receiver.receive({channel,channel==Channel::control?(to_listener?lg:cg):(to_listener?ls:cs)},decoded.message,next());
    }
    void handshake(unsigned session=10) {
        check(l.control_connected(lg,security(Channel::control),next(),id(session)).error==SessionError::none,"listener control");
        auto hello=c.control_connected(cg,security(Channel::control),next());
        auto welcome=deliver(l,std::move(hello)); check(deliver(c,std::move(welcome),false).error==SessionError::none,"welcome");
        check(c.state()==SessionState::synchronizing && l.state()==SessionState::synchronizing,"premature control activation");
        auto cp=c.begin_probe(next());
        check(c.begin_probe(next()).error==SessionError::probe_busy,"multiple outstanding probes");
        auto cr=deliver(l,std::move(cp)); auto ready_c=deliver(c,std::move(cr),false);
        check(ready_c.send.has_value(),"caller clock did not produce READY");
        check(deliver(l,std::move(ready_c)).error==SessionError::none,"caller READY");
        auto lp=l.begin_probe(next()); auto lr=deliver(c,std::move(lp),false); auto ready_l=deliver(l,std::move(lr));
        check(deliver(c,std::move(ready_l),false).error==SessionError::none,"listener READY");
        check(c.state()==SessionState::control_active && l.state()==SessionState::control_active,"mutual readiness");
    }
    SessionAction bind(unsigned nonce=20) {
        check(l.sensor_connected(ls,security(Channel::sensor),next()).error==SessionError::none,"listener sensor");
        auto bind=c.sensor_connected(cs,security(Channel::sensor),next(),id(nonce));
        check(c.state()==SessionState::sensor_binding,"samples enabled before BIND ack");
        return deliver(l,std::move(bind));
    }
    void activate() { handshake(); check(deliver(c,bind(),false).error==SessionError::none,"BIND ack"); }
    MessageView sample(Envelope& envelope) { static const std::array<std::byte,4> data{}; return {envelope,data}; }
};
void happy_and_data() {
    Pair p; p.activate(); check(p.c.state()==SessionState::active && p.l.state()==SessionState::active,"active");
    auto sent=p.c.make_sample(1,4,p.next()); check(sent.envelope.has_value(),"sample creation"); auto e=*sent.envelope;
    check(p.l.admit_sample({Channel::sensor,p.ls},p.sample(e),p.next()).envelope.has_value(),"fresh sample rejected");
    check(p.l.admit_sample({Channel::sensor,p.ls},p.sample(e),p.next()).action.error==SessionError::replay,"duplicate sample");
    check(p.c.make_sample(1,929,p.next()).action.error==SessionError::oversize,"sender oversize");
    check(p.c.make_sample(99,4,p.next()).action.error==SessionError::unknown_route,"unknown route");
    sent=p.c.make_sample(1,4,p.next()); e=*sent.envelope; auto old=e;
    e.session_id=id(99);
    check(p.l.admit_sample({Channel::sensor,p.ls},p.sample(e),p.next()).action.error==SessionError::stale_session,"old session sample");
    e=old; e.source_epoch=id(99);
    check(p.l.admit_sample({Channel::sensor,p.ls},p.sample(e),p.next()).action.error==SessionError::epoch_mismatch,"old epoch sample");
    e=old; e.valid_for_ms=251;
    check(p.l.admit_sample({Channel::sensor,p.ls},p.sample(e),p.next()).action.error==SessionError::malformed,"peer enlarged freshness budget");
    e=old;
    check(p.l.admit_sample({Channel::sensor,p.ls},p.sample(e),p.now+300000000).action.error==SessionError::stale_sample,"stale sample");
}
void rebind_and_disconnect() {
    Pair p; p.handshake(); auto old_ack=p.bind();
    const auto c_loss=p.c.sensor_lost(p.cs), l_loss=p.l.sensor_lost(p.ls);
    check(c_loss.flush_samples && !c_loss.close_control && l_loss.flush_samples,"sensor loss invalidated CONTROL");
    check(p.c.state()==SessionState::control_active,"sensor-only reconnect phase");
    ++p.cs; ++p.ls; auto new_ack=p.bind(21);
    check(p.deliver(p.c,std::move(old_ack),false).error==SessionError::binding_mismatch,"old ack confirmed replacement sensor");
    check(p.c.state()==SessionState::sensor_binding,"old ack activated data");
    check(p.deliver(p.c,std::move(new_ack),false).error==SessionError::none,"new ack");
    auto sent=p.c.make_sample(1,4,p.next()); check(sent.envelope->sequence==1,"first source sequence");
    auto e=*sent.envelope; check(p.l.admit_sample({Channel::sensor,p.ls},p.sample(e),p.next()).envelope.has_value(),"first receive");
    p.c.sensor_lost(p.cs); p.l.sensor_lost(p.ls); ++p.cs; ++p.ls;
    check(p.deliver(p.c,p.bind(22),false).error==SessionError::none,"second rebind");
    check(p.c.make_sample(1,4,p.next()).envelope->sequence==2,"sensor reconnect reset sequence");
    check(p.l.admit_sample({Channel::sensor,p.ls-1},p.sample(e),0).action.error==SessionError::obsolete_connection,"old event caused clock regression");
    check(p.l.state()==SessionState::active,"stale connection event poisoned replacement");
    const auto lost=p.l.control_lost(p.lg);
    check(lost.close_sensor && lost.flush_samples && p.l.state()==SessionState::disconnected,"CONTROL loss kept SENSOR alive");
    p.c.control_lost(p.cg); ++p.cg; ++p.lg; ++p.cs; ++p.ls; p.handshake(11);
    check(p.deliver(p.c,p.bind(23),false).error==SessionError::none,"full reconnect bind");
    check(p.c.make_sample(1,4,p.next()).envelope->sequence==3,"full reconnect silently reset source sequence");
    check(p.l.control_lost(p.lg-1).error==SessionError::obsolete_connection && p.l.state()==SessionState::active,"old close killed new session");
}
void bad_peers_and_timeouts() {
    Pair p;
    auto bad=security(Channel::control); bad.gcm=false;
    const auto action=p.c.control_connected(1,bad,p.next());
    check(action.close_control && p.c.state()==SessionState::failed,"crypto downgrade");
    check(p.c.control_connected(2,security(Channel::control),p.next()).error==SessionError::invalid_state,"permanent failure auto-retried");
    check(p.c.reactivate(),"explicit reactivation");
    p.c.stop(); check(!p.c.reactivate() && p.c.state()==SessionState::stopped,"stop was not terminal");
    Pair bad_peer;
    bad_peer.l.control_connected(11,security(Channel::control),bad_peer.next(),id(10));
    auto hello=bad_peer.c.control_connected(1,security(Channel::control),bad_peer.next());
    std::get<Hello>(hello.send->payload).peer_id="intruder";
    check(bad_peer.deliver(bad_peer.l,std::move(hello)).error==SessionError::bad_peer && bad_peer.l.state()==SessionState::failed,"unconfigured peer");
    Pair limits_peer;
    limits_peer.l.control_connected(11,security(Channel::control),limits_peer.next(),id(10));
    hello=limits_peer.c.control_connected(1,security(Channel::control),limits_peer.next());
    std::get<Hello>(hello.send->payload).limits.routes=7;
    check(limits_peer.deliver(limits_peer.l,std::move(hello)).error==SessionError::limits_mismatch,"limits downgraded");
    Pair mismatch;
    mismatch.l.control_connected(11,security(Channel::control),mismatch.next(),id(10));
    hello=mismatch.c.control_connected(1,security(Channel::control),mismatch.next());
    std::get<Hello>(hello.send->payload).routes_sha256[0]^=std::byte{1};
    check(mismatch.deliver(mismatch.l,std::move(hello)).error==SessionError::manifest_mismatch,"manifest mismatch");
    Pair timeout; timeout.handshake(); auto pending=timeout.c.begin_probe(timeout.next());
    auto reply=timeout.deliver(timeout.l,std::move(pending)); timeout.now+=2000000000;
    check(timeout.deliver(timeout.c,std::move(reply),false).error==SessionError::probe_not_pending,"late probe qualified clock");
    timeout.c.tick(timeout.next());
    check(timeout.c.begin_probe(timeout.next()).send.has_value(),"probe timeout stuck admission");
    Pair binding; binding.handshake(); auto ignored=binding.bind(); (void)ignored;
    binding.now+=200000000; check(binding.c.tick(binding.next()).send.has_value(),"BIND retry missing");
    binding.now+=3000000000;
    check(binding.c.tick(binding.next()).error==SessionError::binding_timeout && binding.c.state()==SessionState::control_active,"unbounded BIND retry");
    Pair late; late.handshake(); auto late_ack=late.bind(); late.now+=3000000000;
    check(late.deliver(late.c,std::move(late_ack),false).error==SessionError::binding_timeout,"late ack bypassed timer deadline");
    Pair late_hello; late_hello.l.control_connected(11,security(Channel::control),late_hello.next(),id(10));
    auto pending_hello=late_hello.c.control_connected(1,security(Channel::control),late_hello.next()); late_hello.now+=3000000000;
    check(late_hello.deliver(late_hello.l,std::move(pending_hello)).error==SessionError::handshake_timeout,"late HELLO bypassed deadline");
    Pair initial; initial.c.control_connected(1,security(Channel::control),initial.next());
    check(initial.c.tick(initial.now+3000000000).error==SessionError::handshake_timeout,"unbounded handshake");
}
void cross_channel_reorder() {
    Pair p;
    p.l.control_connected(p.lg,security(Channel::control),p.next(),id(10));
    auto hello=p.c.control_connected(p.cg,security(Channel::control),p.next());
    p.deliver(p.c,p.deliver(p.l,std::move(hello)),false);
    auto reply=p.deliver(p.c,p.l.begin_probe(p.next()),false);
    auto ready_l=p.deliver(p.l,std::move(reply));p.deliver(p.c,std::move(ready_l),false);
    reply=p.deliver(p.l,p.c.begin_probe(p.next()));
    auto delayed_ready=p.deliver(p.c,std::move(reply),false);
    check(p.c.state()==SessionState::control_active&&p.l.state()==SessionState::synchronizing,"reorder setup");
    auto early_bind=p.bind();check(early_bind.error==SessionError::invalid_state,"BIND bypassed mutual READY");
    check(p.deliver(p.l,std::move(delayed_ready)).error==SessionError::none,"delayed CONTROL READY rejected");
    p.now+=200000000;
    auto ack=p.deliver(p.l,p.c.tick(p.next()));
    check(p.deliver(p.c,std::move(ack),false).error==SessionError::none&&p.c.state()==SessionState::active,"BIND retry did not recover channel reordering");
}
void peer_restart() {
    Pair p; p.activate();
    auto previous=p.c.make_sample(1,4,p.next()); auto old=*previous.envelope;
    check(p.l.admit_sample({Channel::sensor,p.ls},p.sample(old),p.next()).envelope.has_value(),"pre-restart sample");
    p.c.control_lost(p.cg);p.l.control_lost(p.lg);++p.cg;++p.lg;++p.cs;++p.ls;
    auto cfg=config(Role::caller);cfg.local_epoch=id(9);Session restarted(std::move(cfg));
    p.l.control_connected(p.lg,security(Channel::control),p.next(),id(11));
    auto welcome=p.deliver(p.l,restarted.control_connected(p.cg,security(Channel::control),p.next()));
    p.deliver(restarted,std::move(welcome),false);
    auto reply=p.deliver(p.l,restarted.begin_probe(p.next()));
    auto ready=p.deliver(restarted,std::move(reply),false);p.deliver(p.l,std::move(ready));
    reply=p.deliver(restarted,p.l.begin_probe(p.next()),false);
    ready=p.deliver(p.l,std::move(reply));p.deliver(restarted,std::move(ready),false);
    p.l.sensor_connected(p.ls,security(Channel::sensor),p.next());
    auto ack=p.deliver(p.l,restarted.sensor_connected(p.cs,security(Channel::sensor),p.next(),id(21)));
    check(p.deliver(restarted,std::move(ack),false).error==SessionError::none,"new boot binding");
    old.session_id=p.l.session_id();
    check(p.l.admit_sample({Channel::sensor,p.ls},p.sample(old),p.next()).action.error==SessionError::epoch_mismatch,"old epoch under new session");
    auto fresh=restarted.make_sample(1,4,p.next());auto e=*fresh.envelope;
    check(e.sequence==1&&p.l.admit_sample({Channel::sensor,p.ls},p.sample(e),p.next()).envelope.has_value(),"new epoch failed to reset receive watermark");
}
void clock_invalidation_and_wrap() {
    Pair p; p.activate();
    p.now+=5000000001ULL;
    check(p.c.make_sample(1,4,p.next()).action.error==SessionError::clock_unqualified,"expired clock admitted outbound sample");
    auto pending=p.c.begin_probe(p.next()); auto reply=p.deliver(p.l,std::move(pending));
    auto& t=std::get<TimeReply>(reply.send->payload); t.responder_receive_ns+=10000000000ULL; t.responder_send_ns+=10000000000ULL;
    const auto invalid=p.deliver(p.c,std::move(reply),false);
    check(invalid.error==SessionError::clock_invalid && invalid.close_sensor && invalid.close_control && invalid.flush_samples,"clock jump did not invalidate session");
    Pair unsolicited; unsolicited.handshake();
    auto foreign=unsolicited.c.begin_probe(unsolicited.next()); auto foreign_reply=unsolicited.deliver(unsolicited.l,std::move(foreign));
    ++std::get<TimeReply>(foreign_reply.send->payload).initiator_send_ns;
    check(unsolicited.deliver(unsolicited.c,std::move(foreign_reply),false).error==SessionError::probe_not_pending,"unmatched reply updated clock");
    Pair limits; limits.activate();
    auto sent=limits.c.make_sample(1,4,limits.next()); auto e=*sent.envelope; e.sequence=std::numeric_limits<std::uint64_t>::max();
    check(limits.l.admit_sample({Channel::sensor,limits.ls},limits.sample(e),limits.next()).envelope.has_value(),"max sequence rejected");
    e.sequence=0;
    check(limits.l.admit_sample({Channel::sensor,limits.ls},limits.sample(e),limits.next()).action.error==SessionError::replay,"sequence wrapped silently");
    check(limits.c.tick(0).error==SessionError::invalid_time && limits.c.state()==SessionState::disconnected,"local clock regression");
}
}
int main() { try { happy_and_data(); rebind_and_disconnect(); bad_peers_and_timeouts(); cross_channel_reorder(); peer_restart(); clock_invalidation_and_wrap();
    std::cout<<"PASS session contract: "<<checks<<" checks\n"; }
    catch(const std::exception& e) { std::cerr<<"FAIL: "<<e.what()<<'\n'; return 1; } }
