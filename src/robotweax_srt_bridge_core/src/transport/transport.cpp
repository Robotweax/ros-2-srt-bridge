#include <robotweax/srt_bridge/transport.hpp>
#include <robotweax/srt_bridge/queues.hpp>
#include "../worker/execution_pool.hpp"
#include "receiver_retention.hpp"
#include <srt/srt.h>
#include <arpa/inet.h>
#include <algorithm>
#include <atomic>
#include <chrono>
#include <mutex>
#include <stdexcept>
#include <thread>
#include <limits>

namespace robotweax::srt_bridge {
namespace {
constexpr std::uint64_t second=1000000000;
std::mutex provider_mutex;
unsigned provider_users=0;
struct Provider {
    Provider(){std::lock_guard lock(provider_mutex);if(!provider_users&&srt_startup()==SRT_ERROR)throw std::runtime_error("SRT startup failed");++provider_users;}
    ~Provider(){std::lock_guard lock(provider_mutex);if(!--provider_users)srt_cleanup();}
};
void require(bool ok){if(!ok)throw std::runtime_error("transport provider operation failed");}
template<class T> void set(SRTSOCKET s,SRT_SOCKOPT option,T value){require(srt_setsockflag(s,option,&value,sizeof(value))!=SRT_ERROR);}
template<class T> T get(SRTSOCKET s,SRT_SOCKOPT option){T value{};int size=sizeof(value);require(srt_getsockflag(s,option,&value,&size)!=SRT_ERROR&&size==sizeof(value));return value;}
struct Address {
    sockaddr_storage value{};int size=0;bool ipv6=false;
    explicit Address(const Endpoint& endpoint){
        auto& v4=reinterpret_cast<sockaddr_in&>(value);v4.sin_family=AF_INET;v4.sin_port=htons(endpoint.port);
        if(inet_pton(AF_INET,endpoint.address.c_str(),&v4.sin_addr)==1){size=sizeof(v4);return;}
        value={};auto& v6=reinterpret_cast<sockaddr_in6&>(value);v6.sin6_family=AF_INET6;v6.sin6_port=htons(endpoint.port);
        if(inet_pton(AF_INET6,endpoint.address.c_str(),&v6.sin6_addr)!=1)throw std::invalid_argument("transport requires numeric IP addresses");
        size=sizeof(v6);ipv6=true;
    }
    const sockaddr* ptr()const{return reinterpret_cast<const sockaddr*>(&value);}
};
std::uint16_t port(SRTSOCKET fd){sockaddr_storage address{};int size=sizeof(address);require(srt_getsockname(fd,reinterpret_cast<sockaddr*>(&address),&size)!=SRT_ERROR);
    return ntohs(address.ss_family==AF_INET?reinterpret_cast<sockaddr_in&>(address).sin_port:reinterpret_cast<sockaddr_in6&>(address).sin6_port);}
bool zero(const Identity& id){return std::all_of(id.begin(),id.end(),[](std::byte b){return b==std::byte{};});}
std::uint64_t retry_seed(){std::uint64_t value=0;for(auto byte:random_identity())value=(value<<8)^std::to_integer<unsigned>(byte);return value;}
Channel channel(unsigned i){return i==0?Channel::control:Channel::sensor;}
bool same_control(const TransportContext& a,const TransportContext& b){return a.session==b.session&&a.control_generation==b.control_generation;}
bool control_ready(SessionState state){return state==SessionState::control_active||state==SessionState::sensor_binding||state==SessionState::active;}
}
std::uint64_t TransportOwner::monotonic_ns() noexcept {
    return std::chrono::duration_cast<std::chrono::nanoseconds>(std::chrono::steady_clock::now().time_since_epoch()).count();
}
struct TransportOwner::Impl {
    struct Link {
        SRTSOCKET fd=SRT_INVALID_SOCK,listener=SRT_INVALID_SOCK;
        ReconnectPlan retry;
        std::uint64_t generation=0,security_deadline=0;
        bool ready=false;
        explicit Link(std::uint64_t seed):retry(seed){}
    };
    struct Input {
        TransportContext context{};Kind kind=Kind::sample;std::uint32_t route=0;Identity request{};
        std::array<std::byte,control_message_bytes-envelope_bytes> bytes{};std::size_t size=0;std::uint64_t origin=0;
        std::shared_ptr<DurableCommandTicket::Proof> proof{};
    };
    TransportConfig config;
    Address control_address,sensor_address;
    Session session;
    OutboundQueues queues;
    BandwidthBudget budget;
    std::array<Link,2> links{Link{retry_seed()},Link{retry_seed()}};
    std::array<std::uint32_t,8> route_ids{};
    std::size_t route_count=0;
    int epoll=-1;
    std::uint64_t next_probe=0;std::array<std::uint64_t,2> next_provider_sample{};
    std::atomic<bool> stopping{false};
    std::thread thread;
    mutable std::mutex mutex;
    TransportSnapshot shared{},current{};
    struct MailboxCounts {std::uint64_t sensor_submitted=0,sensor_ingress_replaced=0,sensor_ingress_flushed=0,sensor_inputs=0,sensor_receive_replaced=0,sensor_receive_flushed=0,sensor_polled=0,sensor_poll_expired=0;} mailbox_counts;
    void flush_mailboxes(){
        mailbox_counts.sensor_ingress_flushed+=std::count(sample_pending.begin(),sample_pending.end(),true);
        mailbox_counts.sensor_receive_flushed+=std::count(sample_received.begin(),sample_received.end(),true);
        sample_pending.fill(false);sample_received.fill(false);
    }
    std::array<Input,8> samples{};
    std::array<bool,8> sample_pending{},sample_received{};
    std::array<Input,64> controls{};
    std::size_t input_head=0,input_count=0,input_commands=0;
    std::optional<Input> pending_command{};bool pending_clock_reported=false;
    std::array<std::shared_ptr<DurableCommandTicket::Proof>,64> command_proofs{};
    std::array<TransportMessage,64> incoming{};
    std::size_t output_head=0,output_count=0,received_commands=0,sample_cursor=0;
    ReceiverRetention retained;
    std::array<TransportMessage,8> incoming_samples{};
    std::uint64_t publication_epoch=1;bool publication_allowed=false;bool shutting_down=false;
    struct CheckSlot {unsigned state=0;TransportContext context{};Envelope envelope{};CommandCheck result{};std::shared_ptr<execution_detail::Record> proof{};};
    std::array<CheckSlot,64> checks{};
    std::size_t check_cursor=0,check_poll_cursor=0;
    struct ActiveGrant {std::shared_ptr<execution_detail::Record> proof{};TransportContext context{};};
    std::array<ActiveGrant,64> grants{};
    struct Receipt {Identity id{},session{};std::uint32_t route=0;std::uint64_t command=0,query=0;};
    std::array<Receipt,64> receipts{};std::size_t receipt_cursor=0;
    void remember(const Envelope& e){
        auto found=std::find_if(receipts.begin(),receipts.end(),[&](const auto& r){return r.id==e.request_id&&r.route==e.route_id&&r.session==e.session_id;});
        if(found==receipts.end()){found=receipts.begin()+receipt_cursor;receipt_cursor=(receipt_cursor+1)%receipts.size();*found={e.request_id,e.session_id,e.route_id,0,0};}
        (e.kind==Kind::command?found->command:found->query)=e.sequence;
    }
    bool match_error(const Envelope& e,const ControlError& error){
        auto found=std::find_if(receipts.begin(),receipts.end(),[&](const auto& r){return r.id==e.request_id&&r.route==e.route_id&&r.session==e.session_id;});
        if(found==receipts.end())return false;
        auto& sequence=error.request_kind==Kind::command?found->command:found->query;
        if(!sequence||sequence!=error.request_sequence)return false;
        sequence=0;return true;
    }
    void queue_error(const Envelope& request,ControlErrorCode code){
        if(config.session.role!=Role::caller||(request.kind!=Kind::command&&request.kind!=Kind::query)||!request.sequence)return;
        const ControlError error{code,request.kind,request.sequence,0};std::array<std::byte,control_error_payload_bytes> bytes{};
        const auto encoded=encode_control_error(error,bytes);if(!encoded)return;
        const auto made=session.make_control(Kind::error,request.route_id,request.request_id,encoded.bytes_written,0,monotonic_ns());apply(made.action);
        if(made.envelope)queues.control({Channel::control,links[0].generation},*made.envelope,std::span(bytes).first(encoded.bytes_written));
    }
    explicit Impl(TransportConfig c):config(std::move(c)),control_address(config.control),sensor_address(config.sensor),
        session(config.session),queues(config.session.manifest),budget(config.bandwidth,monotonic_ns()) {
        if(control_address.ipv6!=sensor_address.ipv6||config.passphrase.size()<10||config.passphrase.size()>79||
           (config.session.role==Role::caller&&(!config.control.port||!config.sensor.port)))throw std::invalid_argument("invalid transport endpoints or credential length");
        for(const auto& route:config.session.manifest.routes())route_ids[route_count++]=route.id;
        thread=std::thread([this]{run();});
    }
    ~Impl(){stopping=true;if(thread.joinable())thread.join();}
    void trace(CommandTracePoint point,CommandTraceReason reason,const Identity& id={},std::uint32_t route=0,unsigned value=0,unsigned detail=0){
        if(!config.command_trace)return;
        const auto c=context();
        config.command_trace->record(CommandTraceProducer::transport,{0,monotonic_ns(),point,reason,id,c.session,config.session.local_epoch,
            c.control_generation,c.sensor_generation,route,value,{},detail});
    }
    TransportContext context()const{return {session.session_id(),links[0].generation,links[1].generation};}
    std::size_t index(std::uint32_t route)const{
        for(std::size_t i=0;i<route_count;++i)if(route_ids[i]==route)return i;
        return route_count;
    }
    void publish(){
        current.state=session.state();current.context=context();
        current.clock_deadline_ns=session.clock_deadline().value_or(0);current.clock_qualified=session.clock_state()==ClockError::none&&monotonic_ns()<current.clock_deadline_ns;
        current.control_retry=links[0].retry.state();current.sensor_retry=links[1].retry.state();
        std::lock_guard lock(mutex);
        if(shared.context!=current.context||!current.running)flush_mailboxes();
        if(!same_control(shared.context,current.context)||!current.running){
            for(std::size_t n=0;n<input_count;++n){const auto& item=controls[(input_head+n)%controls.size()];
                if(item.kind==Kind::command)trace(CommandTracePoint::mailbox_flushed,current.running?CommandTraceReason::context_mismatch:CommandTraceReason::shutdown,item.request,item.route);}
            if(pending_command)trace(CommandTracePoint::mailbox_flushed,current.running?CommandTraceReason::context_mismatch:CommandTraceReason::shutdown,pending_command->request,pending_command->route);
            while(retained.size()){
                trace_receiver(CommandTracePoint::receiver_retained_dropped,retained.front().message,unsigned(SessionError::obsolete_connection),current.running?CommandTraceReason::context_mismatch:CommandTraceReason::shutdown);
                retained.pop();++current.stale_work;
            }
            received_commands=0;
            current.stale_work+=input_count+output_count+(pending_command?1:0);pending_command.reset();receipts={};receipt_cursor=0;
            for(auto& slot:checks)if(slot.state){if(slot.proof)slot.proof->pool->revoke(*slot.proof);slot.result.error=SessionError::obsolete_connection;slot.result.start_granted=false;slot.state=2;}
            input_head=input_count=input_commands=output_head=output_count=0;
        }
        publication_allowed=current.running&&current.state==SessionState::active&&current.clock_qualified&&publication_epoch!=UINT64_MAX;
        current.control_ingress=input_count+(pending_command?1:0);current.control_received=output_count+retained.size();
        current.sensor_submitted=mailbox_counts.sensor_submitted;
        current.sensor_ingress_replaced=mailbox_counts.sensor_ingress_replaced;
        current.sensor_ingress_flushed=mailbox_counts.sensor_ingress_flushed;
        current.sensor_inputs=mailbox_counts.sensor_inputs;
        current.sensor_receive_replaced=mailbox_counts.sensor_receive_replaced;
        current.sensor_receive_flushed=mailbox_counts.sensor_receive_flushed;
        current.sensor_polled=mailbox_counts.sensor_polled;
        current.sensor_poll_expired=mailbox_counts.sensor_poll_expired;
        current.sensor_ingress_pending=std::count(sample_pending.begin(),sample_pending.end(),true);
        current.sensor_receive_pending=std::count(sample_received.begin(),sample_received.end(),true);
        current.sensor_outbound_pending=queues.sensor_count();
        current.sensor_outbound_replaced=queues.stats().sensor_replaced;
        current.sensor_outbound_expired=queues.stats().sensor_expired-queues.stats().sensor_enqueue_expired;
        current.sensor_outbound_flushed=queues.stats().sensor_flushed;
        current.sensor_replaced+=shared.sensor_replaced;shared=current;current.sensor_replaced=0;
    }
    void close_fd(SRTSOCKET& fd){
        if(fd!=SRT_INVALID_SOCK){srt_epoll_remove_usock(epoll,fd);srt_close(fd);fd=SRT_INVALID_SOCK;}
    }
    SRTSOCKET create(unsigned i){
        const auto fd=srt_create_socket();require(fd!=SRT_INVALID_SOCK);
        try{
            set(fd,SRTO_TRANSTYPE,i==0?SRTT_CONTROL:SRTT_SENSOR);set(fd,SRTO_MSS,control_address.ipv6?1280:1500);
            set(fd,SRTO_CRYPTOMODE,2);set(fd,SRTO_ENFORCEDENCRYPTION,true);set(fd,SRTO_ROBOTWEAX_SESSIONAUTH,true);set(fd,SRTO_PBKEYLEN,32);
            require(srt_setsockflag(fd,SRTO_PASSPHRASE,config.passphrase.data(),config.passphrase.size())!=SRT_ERROR);
            set(fd,SRTO_PAYLOADSIZE,1024);set(fd,SRTO_FC,256);set(fd,SRTO_SNDBUF,262144);set(fd,SRTO_RCVBUF,262144);
            set(fd,SRTO_UDP_SNDBUF,262144);set(fd,SRTO_UDP_RCVBUF,262144);
            set(fd,SRTO_CONNTIMEO,3000);set(fd,SRTO_SNDSYN,false);set(fd,SRTO_RCVSYN,false);set(fd,SRTO_LINGER,linger{0,0});
            return fd;
        }catch(...){srt_close(fd);throw;}
    }
    void add(SRTSOCKET fd,bool connecting){int events=SRT_EPOLL_IN|SRT_EPOLL_ERR|(connecting?SRT_EPOLL_OUT:0);require(srt_epoll_add_usock(epoll,fd,&events)!=SRT_ERROR);}
    void listen(unsigned i){
        auto& link=links[i];link.listener=create(i);const auto& address=i?sensor_address:control_address;
        require(srt_bind(link.listener,address.ptr(),address.size)!=SRT_ERROR&&srt_listen(link.listener,4)!=SRT_ERROR);add(link.listener,false);
        (i?current.sensor_port:current.control_port)=port(link.listener);
    }
    void provider_sample(unsigned i,bool before_close=false){
        auto& diagnostics=i?config.sensor_provider_diagnostics:config.provider_diagnostics;
        if(!diagnostics||diagnostics->exhausted())return;
        const auto now=monotonic_ns();
        if(!before_close&&now<next_provider_sample[i])return;
        next_provider_sample[i]=now+100000000ULL;
        ProviderObservation o;o.channel=i;o.begin_ns=now;o.owner_epoch=config.session.local_epoch;
        o.session=session.session_id();o.generation=links[i].generation;o.socket=links[i].fd;o.before_close=before_close;
        if(links[i].fd!=SRT_INVALID_SOCK){
            o.state_before=unsigned(srt_getsockstate(links[i].fd));o.unavailable=2;
            int size=sizeof(o.idle_timeout_ms);
            o.idle_timeout_available=srt_getsockflag(links[i].fd,SRTO_PEERIDLETIMEO,&o.idle_timeout_ms,&size)!=SRT_ERROR;
            if(links[i].ready){
                SRT_TRACEBSTATS stats{};
                if(srt_bstats(links[i].fd,&stats,0)==SRT_ERROR){o.unavailable=3;o.error=srt_getlasterror(nullptr);}
                else{
                    o.available=true;o.unavailable=0;
                    o.data_sent=stats.pktSentTotal;o.data_received=stats.pktRecvTotal;o.retransmitted=stats.pktRetransTotal;
                    o.ack_sent=stats.pktSentACKTotal;o.ack_received=stats.pktRecvACKTotal;
                    o.nak_sent=stats.pktSentNAKTotal;o.nak_received=stats.pktRecvNAKTotal;o.undecrypt=stats.pktRcvUndecryptTotal;
                    o.bytes_sent=stats.byteSentTotal;o.bytes_received=stats.byteRecvTotal;
                    o.send_buffer_packets=stats.pktSndBuf;o.send_buffer_bytes=stats.byteSndBuf;
                    o.receive_buffer_packets=stats.pktRcvBuf;o.receive_buffer_bytes=stats.byteRcvBuf;
                    o.flight_packets=stats.pktFlightSize;o.rtt_ms=stats.msRTT;
                    o.unique_sent=stats.pktSentUniqueTotal;o.unique_received=stats.pktRecvUniqueTotal;
                    o.sender_loss=stats.pktSndLossTotal;o.receiver_loss=stats.pktRcvLossTotal;
                    o.sender_drop=stats.pktSndDropTotal;o.receiver_drop=stats.pktRcvDropTotal;
                    o.sender_filter_extra=stats.pktSndFilterExtraTotal;o.receiver_filter_extra=stats.pktRcvFilterExtraTotal;
                    o.receiver_filter_supply=stats.pktRcvFilterSupplyTotal;o.receiver_filter_loss=stats.pktRcvFilterLossTotal;
                    o.flow_window_packets=stats.pktFlowWindow;o.congestion_window_packets=stats.pktCongestionWindow;
                }
            }
            o.state_after=unsigned(srt_getsockstate(links[i].fd));
        }
        o.end_ns=monotonic_ns();diagnostics->record(o);
    }
    void drop(unsigned i,bool permanent){
        if(links[i].fd!=SRT_INVALID_SOCK)provider_sample(i,true);
        auto& link=links[i];close_fd(link.fd);link.ready=false;
        if(config.session.role==Role::caller){
            const auto time=monotonic_ns();
            if(permanent)link.retry.permanent_failure();
            else if(link.retry.state()==RetryState::connected)link.retry.connection_lost(link.generation,time);
            else if(link.retry.state()==RetryState::connecting)link.retry.complete(link.generation,time,RetryOutcome::transient_failure);
        }
    }
    void revoke_grants(){
        for(auto& grant:grants)if(grant.proof)grant.proof->pool->revoke(*grant.proof);
        std::lock_guard lock(mutex);for(auto& slot:checks)if(slot.proof)slot.proof->pool->revoke(*slot.proof);
    }
    void refresh_grants(){
        for(auto& grant:grants)if(grant.proof){auto& record=*grant.proof;const auto state=record.pool->state(record);
            if(!same_control(grant.context,context())||!record.live->load()||(state==execution_detail::State::granted&&monotonic_ns()>=record.pool->deadline(record)))record.pool->revoke(record);
            const auto current=record.pool->state(record);
            if(current==execution_detail::State::revoked||current==execution_detail::State::finished||!record.live->load())grant={};
        }
    }
    void apply(SessionAction action){
        if(action.close_control||action.close_sensor)
            trace(CommandTracePoint::session_action,shutting_down?CommandTraceReason::shutdown:CommandTraceReason::session_decision,{},0,unsigned(action.error),
                unsigned(action.close_control)|(unsigned(action.close_sensor)<<1)|(unsigned(action.flush_samples)<<2));
        if(action.close_control||(action.flush_samples&&!action.close_sensor))revoke_grants();
        const bool permanent=session.state()==SessionState::failed;
        const auto discarded=queues.apply(action);current.stale_work+=discarded.count;
        for(std::size_t n=0;n<discarded.count;++n)trace(CommandTracePoint::outbound_flushed,shutting_down?CommandTraceReason::shutdown:CommandTraceReason::context_mismatch,discarded.ids[n]);
        if(action.close_control){command_proofs={};receipts={};receipt_cursor=0;}
        if(action.close_sensor)drop(1,permanent);
        if(action.close_control){drop(0,permanent);next_probe=0;}
        if(permanent){current.fault=TransportFault::protocol;links[0].retry.permanent_failure();links[1].retry.permanent_failure();}
        if(action.flush_samples){std::lock_guard lock(mutex);flush_mailboxes();publication_allowed=false;if(publication_epoch!=UINT64_MAX)++publication_epoch;}
        if(action.send){
            std::array<std::byte,management_payload_bytes> bytes{};auto& out=*action.send;
            const auto encoded=encode_management(out.payload,bytes);require(bool(encoded));
            const auto body=std::span(bytes).first(encoded.bytes_written);
            const auto result=out.connection.channel==Channel::control?queues.control(out.connection,out.envelope,body):queues.binding(out.connection,out.envelope,body);
            if(result!=QueueError::none){++current.rejected;apply(session.control_lost(links[0].generation));}
        }
    }
    void lost(unsigned i,CommandTraceReason reason,unsigned value=0){
        trace(CommandTracePoint::link_lost,reason,{},0,value,i);
        if(!links[i].ready){drop(i,false);return;}
        apply(i?session.sensor_lost(links[i].generation):session.control_lost(links[i].generation));
    }
    void connect(unsigned i,const RetryAction& action){
        auto& link=links[i];if(action.close)close_fd(link.fd);
        if(!action.connect)return;
        link.generation=action.attempt;link.ready=false;link.fd=create(i);link.security_deadline=monotonic_ns()+3*second;add(link.fd,true);
        const auto& address=i?sensor_address:control_address;
        if(srt_connect(link.fd,address.ptr(),address.size)==SRT_ERROR){
            // Nonblocking connect returns zero on the qualified provider. Any
            // immediate error is a failed attempt; no blocking retry here.
            drop(i,false);
        }
    }
    void accept(unsigned i){
        auto& link=links[i];const auto fd=srt_accept(link.listener,nullptr,nullptr);
        if(fd==SRT_INVALID_SOCK){if(srt_getlasterror(nullptr)!=SRT_EASYNCRCV)throw std::runtime_error("accept failed");return;}
        if(link.fd!=SRT_INVALID_SOCK||(i&&!control_ready(session.state()))||session.state()==SessionState::failed){srt_close(fd);++current.rejected;return;}
        if(link.generation==std::numeric_limits<std::uint64_t>::max()){srt_close(fd);throw std::runtime_error("generation exhausted");}
        link.fd=fd;++link.generation;link.ready=false;link.security_deadline=monotonic_ns()+3*second;
        set(fd,SRTO_SNDSYN,false);set(fd,SRTO_RCVSYN,false);set(fd,SRTO_LINGER,linger{0,0});add(fd,false);
    }
    void secured(unsigned i){
        auto& link=links[i];
        if(get<int>(link.fd,SRTO_SNDKMSTATE)!=SRT_KM_S_SECURED||get<int>(link.fd,SRTO_RCVKMSTATE)!=SRT_KM_S_SECURED)return;
        Security security{channel(i),get<int>(link.fd,SRTO_CRYPTOMODE)==2,get<bool>(link.fd,SRTO_ROBOTWEAX_SESSIONAUTH),get<bool>(link.fd,SRTO_ENFORCEDENCRYPTION)};
        require(get<SRT_TRANSTYPE>(link.fd,SRTO_TRANSTYPE)==(i?SRTT_SENSOR:SRTT_CONTROL));
        require(!get<bool>(link.fd,SRTO_SNDSYN)&&!get<bool>(link.fd,SRTO_RCVSYN));
        if(config.session.role==Role::caller){auto a=link.retry.complete(link.generation,monotonic_ns(),RetryOutcome::connected);if(a.error!=RetryError::none){drop(i,false);return;}}
        int events=SRT_EPOLL_IN|SRT_EPOLL_ERR;require(srt_epoll_update_usock(epoll,link.fd,&events)!=SRT_ERROR);
        link.ready=true;require(queues.open({channel(i),link.generation})==QueueError::none);
        apply(i?session.sensor_connected(link.generation,security,monotonic_ns(),config.session.role==Role::caller?random_identity():Identity{}):
            session.control_connected(link.generation,security,monotonic_ns(),config.session.role==Role::listener?random_identity():Identity{}));
    }
    void trace_receiver(CommandTracePoint point,const TransportMessage& message,unsigned value,CommandTraceReason reason=CommandTraceReason::none,const SampleResult* result=nullptr){
        if(!config.command_trace)return;
        CommandTraceEvent e{0,monotonic_ns(),point,reason,message.envelope.request_id,message.context.session,config.session.local_epoch,
            message.context.control_generation,message.context.sensor_generation,message.envelope.route_id,value,{},unsigned(Kind::command)};
        e.request_sequence=message.envelope.sequence;e.origin_ns=message.envelope.source_monotonic_ns;e.evaluated_ns=result?result->evaluated_ns:message.evaluated_ns;
        e.clock_deadline_ns=session.clock_deadline().value_or(0);e.clock_error=unsigned(session.clock_state());e.age_error=result?unsigned(result->age.error):0;
        if(result&&result->age.age_ns){e.age_lower_ns=result->age.age_ns->lower;e.age_upper_ns=result->age.age_ns->upper;}
        if(point==CommandTracePoint::receiver_expiry_admission){e.expiry_deadline_ns=message.deadline_ns;e.budget_ms=message.envelope.valid_for_ms;}
        config.command_trace->record(CommandTraceProducer::transport,e);
    }
    void process_retained(){
        for(unsigned n=0;n<8&&retained.size();++n){
            const auto time=monotonic_ns();const auto message=retained.front().message;
            if(!retained.matches(context())||!control_ready(session.state())){
                trace_receiver(CommandTracePoint::receiver_retained_dropped,message,unsigned(SessionError::obsolete_connection),CommandTraceReason::context_mismatch);retained.pop();++current.stale_work;continue;
            }
            const auto result=session.check_command(message.envelope,time);apply(result.action);
            const auto expired=ReceiverRetention::expiry_deadline(message.envelope,result);
            if(!expired&&retained.expired(time)){
                trace_receiver(CommandTracePoint::receiver_retained_dropped,message,unsigned(SessionError::clock_unqualified),CommandTraceReason::deadline);
                retained.pop();queue_error(message.envelope,ControlErrorCode::clock_unqualified);++current.rejected;continue;
            }
            if(!result.envelope&&!expired){
                if(ReceiverRetention::soft_gap(result)||ReceiverRetention::ambiguous(message.envelope,result))break;
                trace_receiver(CommandTracePoint::receiver_retained_dropped,message,unsigned(result.action.error),CommandTraceReason::session_rejected,&result);retained.pop();++current.rejected;
                if(result.action.error==SessionError::stale_sample)queue_error(message.envelope,ControlErrorCode::start_expired);
                else if(result.action.error==SessionError::clock_unqualified)queue_error(message.envelope,ControlErrorCode::clock_unqualified);
                continue;
            }
            auto ready=message;const auto maximum=std::uint64_t(message.envelope.valid_for_ms)*1000000;
            ready.evaluated_ns=result.evaluated_ns;ready.expiry_only=expired.has_value();
            if(expired)ready.deadline_ns=*expired;
            else{
                require(result.age.age_ns&&result.age.age_ns->upper>=0&&std::uint64_t(result.age.age_ns->upper)<=maximum);
                ready.deadline_ns=result.evaluated_ns+maximum-std::uint64_t(result.age.age_ns->upper);
            }
            {std::lock_guard lock(mutex);require(output_count<incoming.size()&&received_commands<ReceiverRetention::command_capacity);
                retained.pop();incoming[(output_head+output_count++)%incoming.size()]=ready;++received_commands;}
            ++current.received;trace_receiver(expired?CommandTracePoint::receiver_expiry_admission:CommandTracePoint::receiver_resumed,ready,unsigned(expired?SessionError::stale_sample:SessionError::none),CommandTraceReason::none,&result);
        }
    }
    bool control_space(){std::lock_guard lock(mutex);return output_count+retained.size()<incoming.size()&&queues.control_count()<64;}
    void receive(unsigned i){
        auto& link=links[i];
        for(unsigned n=0;n<8&&link.ready&&link.fd!=SRT_INVALID_SOCK;++n){
            if(!i&&!control_space())return; // Backpressure before consuming any CONTROL frame.
            std::array<std::byte,control_message_bytes+1> bytes{};
            const bool observing=i&&bool(config.sample_trace);SRT_MSGCTRL metadata=srt_msgctrl_default;
            const auto receive_begin=observing?monotonic_ns():0;
            const int count=observing?srt_recvmsg2(link.fd,reinterpret_cast<char*>(bytes.data()),bytes.size(),&metadata):
                srt_recvmsg(link.fd,reinterpret_cast<char*>(bytes.data()),bytes.size());
            if(count==SRT_ERROR){const auto error=srt_getlasterror(nullptr);if(error!=SRT_EASYNCRCV)lost(i,CommandTraceReason::receive_error,unsigned(error));return;}
            const auto decoded=decode(std::span(bytes).first(count),channel(i),std::span(route_ids).first(route_count));
            if(!decoded){++current.rejected;lost(i,CommandTraceReason::wire_decode,unsigned(decoded.error));return;}
            const auto& view=decoded.message;const auto kind=view.envelope.kind;const Connection connection{channel(i),link.generation};
            if(kind!=Kind::sample&&kind!=Kind::command&&kind!=Kind::query&&kind!=Kind::status&&kind!=Kind::error){apply(session.receive(connection,view,monotonic_ns()));continue;}
            if(kind==Kind::sample)++current.samples_received;
            const auto admission_ns=monotonic_ns();
            const auto result=i?session.admit_sample(connection,view,admission_ns):session.admit_control(connection,view,admission_ns);
            if(config.command_trace&&(kind==Kind::command||kind==Kind::query)){
                const auto c=context();
                CommandTraceEvent e{0,monotonic_ns(),CommandTracePoint::control_admission,CommandTraceReason::none,
                    view.envelope.request_id,view.envelope.session_id,config.session.local_epoch,c.control_generation,c.sensor_generation,
                    view.envelope.route_id,unsigned(result.action.error),{},unsigned(kind)};
                e.request_sequence=view.envelope.sequence;e.origin_ns=view.envelope.source_monotonic_ns;e.evaluated_ns=admission_ns;
                e.clock_deadline_ns=session.clock_deadline().value_or(0);e.clock_error=unsigned(session.clock_state());e.age_error=unsigned(result.age.error);
                config.command_trace->record(CommandTraceProducer::transport,e);
            }
            if(observing&&kind==Kind::sample){
                SampleTraceEvent e;e.point=unsigned(SampleTracePoint::receiver_decision);e.begin_ns=receive_begin;e.end_ns=monotonic_ns();
                e.origin_ns=view.envelope.source_monotonic_ns;e.owner_epoch=config.session.local_epoch;e.session=view.envelope.session_id;e.source_epoch=view.envelope.source_epoch;
                e.control_generation=links[0].generation;e.sensor_generation=link.generation;e.envelope_sequence=view.envelope.sequence;e.route=view.envelope.route_id;
                e.kind=unsigned(kind);e.result=unsigned(result.action.error);e.bytes=count;e.socket=link.fd;e.message_number=metadata.msgno;
                config.sample_trace->record(SampleTraceLane::transport,e);
            }
            apply(result.action);
            const auto expired=kind==Kind::command?ReceiverRetention::expiry_deadline(view.envelope,result):std::optional<std::uint64_t>{};
            const bool wait_command=kind==Kind::command&&(ReceiverRetention::soft_gap(result)||ReceiverRetention::ambiguous(view.envelope,result));
            if(kind==Kind::command&&(wait_command||((result.envelope||expired)&&retained.size()))){
                TransportMessage pending;pending.context=context();pending.envelope=view.envelope;pending.size=view.payload.size();pending.evaluated_ns=admission_ns;
                std::copy(view.payload.begin(),view.payload.end(),pending.payload.begin());
                bool saved;{std::lock_guard lock(mutex);saved=retained.push(pending,admission_ns,output_count,received_commands);}
                if(saved)trace_receiver(CommandTracePoint::receiver_deferred,pending,unsigned(result.action.error));
                else{trace_receiver(CommandTracePoint::receiver_capacity_rejected,pending,unsigned(ControlErrorCode::busy),CommandTraceReason::queue_rejected);queue_error(view.envelope,ControlErrorCode::busy);++current.rejected;}
                continue;
            }
            if(!result.envelope&&!expired){
                ++current.rejected;
                if(kind==Kind::sample){
                    ++current.samples_rejected;
                    if(result.action.error==SessionError::clock_unqualified||result.action.error==SessionError::clock_invalid)++current.samples_unknown_age;
                    if(result.action.error==SessionError::stale_sample)++current.samples_stale;
                }
                switch(result.action.error){
                    case SessionError::clock_unqualified:queue_error(view.envelope,ControlErrorCode::clock_unqualified);break;
                    case SessionError::stale_sample:queue_error(view.envelope,ControlErrorCode::start_expired);break;
                    case SessionError::malformed:case SessionError::oversize:queue_error(view.envelope,ControlErrorCode::invalid_request);break;
                    default:break;
                }
                continue;
            }
            if(kind==Kind::error){const auto error=decode_control_error(view.payload);require(error.has_value());if(!match_error(view.envelope,*error)){++current.unmatched_errors;++current.rejected;continue;}++current.errors_received;}
            TransportMessage message;message.context=context();message.envelope=expired?view.envelope:*result.envelope;message.expiry_only=expired.has_value();message.size=view.payload.size();
            std::copy(view.payload.begin(),view.payload.end(),message.payload.begin());message.evaluated_ns=result.evaluated_ns;
            if(expired)message.deadline_ns=*expired;
            else if(kind==Kind::sample||kind==Kind::command){
                const auto max_age=std::uint64_t(message.envelope.valid_for_ms)*1000000;
                require(result.age.age_ns.has_value()&&result.age.age_ns->upper>=0&&std::uint64_t(result.age.age_ns->upper)<=max_age);
                message.deadline_ns=result.evaluated_ns+max_age-std::uint64_t(result.age.age_ns->upper);
            }
            if(kind==Kind::command){
                bool room;{std::lock_guard lock(mutex);room=retained.room(output_count,received_commands);}
                if(!room){trace_receiver(CommandTracePoint::receiver_capacity_rejected,message,unsigned(ControlErrorCode::busy),CommandTraceReason::queue_rejected);queue_error(view.envelope,ControlErrorCode::busy);++current.rejected;continue;}
            }
            if(expired)trace_receiver(CommandTracePoint::receiver_expiry_admission,message,unsigned(SessionError::stale_sample),CommandTraceReason::none,&result);
            std::lock_guard lock(mutex);
            if(i){message.publication_epoch=publication_epoch;const auto at=index(message.envelope.route_id);require(at<route_count);if(sample_received[at]){++current.sensor_replaced;++mailbox_counts.sensor_receive_replaced;}incoming_samples[at]=message;sample_received[at]=true;}
            else{require(output_count<incoming.size());incoming[(output_head+output_count++)%incoming.size()]=message;if(kind==Kind::command)++received_commands;}
            ++current.received;
        }
    }
    void process_checks(){
        for(unsigned n=0;n<8;++n){
            CheckSlot work;std::size_t at=checks.size();
            {std::lock_guard lock(mutex);for(std::size_t offset=0;offset<checks.size();++offset){const auto i=(check_cursor+offset)%checks.size();if(checks[i].state==1){at=i;work=checks[i];checks[i].state=3;check_cursor=(i+1)%checks.size();break;}}}
            if(at==checks.size())return;
            auto result=work.result;
            if(!same_control(work.context,context()))result.error=SessionError::obsolete_connection;
            else{
                const auto gate=session.check_command(work.envelope,monotonic_ns());apply(gate.action);result.error=gate.action.error;
                if(gate.envelope){result.evaluated_ns=gate.evaluated_ns;const auto age=std::uint64_t(gate.age.age_ns->upper);result.deadline_ns=result.evaluated_ns+std::uint64_t(work.envelope.valid_for_ms)*1000000-age;}
            }
            if(work.proof){
                auto& record=*work.proof;
                if(result.error==SessionError::none){
                    result.deadline_ns=std::min(result.deadline_ns,record.entry.context.deadline_ns);
                    const auto clock_deadline=session.clock_deadline();
                    if(!clock_deadline)result.error=SessionError::clock_unqualified;
                    else result.deadline_ns=std::min(result.deadline_ns,*clock_deadline);
                    auto free=std::find_if(grants.begin(),grants.end(),[](const auto& grant){return !grant.proof;});
                    if(result.error==SessionError::none){
                        if(monotonic_ns()>=result.deadline_ns)result.error=SessionError::stale_sample;
                        else if(free==grants.end()||!record.pool->grant(record,result.deadline_ns))result.error=SessionError::obsolete_connection;
                        else{*free={work.proof,work.context};result.start_granted=true;}
                    }
                }
                if(!result.start_granted)record.pool->revoke(record);
            }
            std::lock_guard lock(mutex);checks[at].result=result;checks[at].state=2;
        }
    }
    void release_pending_command(){std::lock_guard lock(mutex);pending_command.reset();}
    void inputs(){
        // One CONTROL item and eight latest samples per iteration bound owner work.
        // Keep an item in the ingress mailbox while the outgoing CONTROL FIFO is full.
        std::array<Input,9> work{};std::size_t count=0;
        {std::lock_guard lock(mutex);
            if(queues.control_count()<64){
                if(pending_command)work[count++]=*pending_command;
                else if(input_count){work[count++]=controls[input_head];
                    if(controls[input_head].kind==Kind::command){--input_commands;pending_command=work[count-1];pending_clock_reported=false;}
                    controls[input_head]={};input_head=(input_head+1)%controls.size();--input_count;
                }
            }
            for(std::size_t i=0;i<route_count;++i)if(sample_pending[i]){work[count++]=samples[i];++mailbox_counts.sensor_inputs;samples[i]={};sample_pending[i]=false;}
        }
        for(std::size_t i=0;i<count;++i){auto& item=work[i];
            const bool bad_context=item.kind==Kind::sample?item.context!=context():!same_control(item.context,context());
            const bool revoked=!bad_context&&item.proof&&!item.proof->live->load();
            const bool expired=!bad_context&&!revoked&&item.proof&&time_expired(item.proof->entry);
            if(bad_context||revoked||expired){++current.stale_work;if(item.kind==Kind::sample)++current.sensor_input_rejected;
                if(item.kind==Kind::command)trace(CommandTracePoint::input_dropped,bad_context?CommandTraceReason::context_mismatch:
                    revoked?CommandTraceReason::proof_revoked:CommandTraceReason::deadline,item.request,item.route);
                if(item.kind==Kind::command)release_pending_command();
                continue;}
            const auto time=monotonic_ns();
            auto made=item.kind==Kind::sample?session.make_sample(item.route,item.size,time):session.make_control(item.kind,item.route,item.request,item.size,item.origin,time);
            apply(made.action);if(!made.envelope){
                if(item.kind==Kind::command&&made.action.error==SessionError::clock_unqualified){
                    if(!pending_clock_reported){trace(CommandTracePoint::clock_deferred,CommandTraceReason::session_rejected,item.request,item.route,unsigned(made.action.error));pending_clock_reported=true;}
                    continue; // Retain original proof/origin/deadline in the reserved ingress slot.
                }
                if(item.kind==Kind::command){trace(CommandTracePoint::make_rejected,CommandTraceReason::session_rejected,item.request,item.route,unsigned(made.action.error));release_pending_command();}
                ++current.rejected;if(item.kind==Kind::sample)++current.sensor_input_rejected;continue;
            }
            auto envelope=*made.envelope;
            if(item.kind==Kind::sample)envelope.source_monotonic_ns=item.origin; // Preserve callback ingress, not dequeue time.
            const auto body=std::span(item.bytes).first(item.size);
            const auto result=item.kind==Kind::sample?queues.sensor({Channel::sensor,links[1].generation},envelope,body,time):queues.control({Channel::control,links[0].generation},envelope,body);
            if(result!=QueueError::none){if(item.kind==Kind::command)trace(CommandTracePoint::queue_rejected,CommandTraceReason::queue_rejected,item.request,item.route,unsigned(result));++current.rejected;if(item.kind==Kind::sample)++current.sensor_input_rejected;}
            else if(item.proof){const auto at=std::find(command_proofs.begin(),command_proofs.end(),nullptr);require(at!=command_proofs.end());*at=std::move(item.proof);}
            if(item.kind==Kind::command)release_pending_command();
        }
    }
    bool time_expired(const JournalEntry& e)const{return monotonic_ns()>=e.context.deadline_ns;}
    void send(unsigned i){
        if(!links[i].ready)return;
        for(unsigned n=0;n<8;++n){const auto time=monotonic_ns();const bool binding=i&&queues.binding_front();
            const auto* packet=i?(binding?queues.binding_front():queues.sensor_front(time)):queues.control_front();if(!packet)return;
            auto proof=command_proofs.end();
            if(!i&&packet->envelope.kind==Kind::command){
                proof=std::find_if(command_proofs.begin(),command_proofs.end(),[&](const auto& p){return p&&p->entry.request_id==packet->envelope.request_id;});
                const bool missing=proof==command_proofs.end();
                const bool revoked=!missing&&!(*proof)->live->load();
                const bool expired=!missing&&!revoked&&time_expired((*proof)->entry);
                if(missing||revoked||expired){
                    trace(CommandTracePoint::outbound_dropped,missing?CommandTraceReason::missing_proof:
                        revoked?CommandTraceReason::proof_revoked:CommandTraceReason::deadline,packet->envelope.request_id,packet->envelope.route_id);
                    if(proof!=command_proofs.end())proof->reset();
                    queues.control_sent();++current.rejected;continue;
                }
            }
            auto permit=budget.reserve(channel(i),packet->size,time);if(!permit){if(permit.error!=BudgetError::rate_limited)throw std::runtime_error("invalid budget");return;}
            const auto ttl=i?(binding?200:sensor_ttl_ms(*packet,time)):-1;
            const bool observing=i&&bool(config.sample_trace);
            SRT_MSGCTRL metadata=srt_msgctrl_default;metadata.msgttl=ttl;metadata.inorder=0;
            const auto trace_begin=observing?monotonic_ns():0;
            const int count=observing?srt_sendmsg2(links[i].fd,reinterpret_cast<const char*>(packet->bytes.data()),packet->size,&metadata):
                srt_sendmsg(links[i].fd,reinterpret_cast<const char*>(packet->bytes.data()),packet->size,ttl,0);
            const int error=count==SRT_ERROR?srt_getlasterror(nullptr):0;
            const auto trace_end=observing?monotonic_ns():0;
            require(budget.finish(permit.id,count!=SRT_ERROR));
            if(observing){
                SampleTraceEvent e;e.begin_ns=trace_begin;e.end_ns=trace_end;e.origin_ns=packet->envelope.source_monotonic_ns;
                e.owner_epoch=config.session.local_epoch;e.session=packet->envelope.session_id;e.source_epoch=packet->envelope.source_epoch;
                e.control_generation=links[0].generation;e.sensor_generation=links[1].generation;
                e.envelope_sequence=packet->envelope.sequence;e.route=packet->envelope.route_id;e.kind=unsigned(packet->envelope.kind);
                e.bytes=packet->size;e.socket=links[i].fd;e.message_number=count==SRT_ERROR?0:metadata.msgno;
                e.point=unsigned(count==SRT_ERROR?SampleTracePoint::sdk_error:SampleTracePoint::sdk_accepted);e.result=unsigned(error);
                int size=sizeof(e.initial_sequence);
                e.initial_sequence_available=srt_getsockflag(links[i].fd,SRTO_ISN,&e.initial_sequence,&size)!=SRT_ERROR&&size==sizeof(e.initial_sequence);
                config.sample_trace->record(SampleTraceLane::transport,e);
            }
            if(count==SRT_ERROR){if(packet->envelope.kind==Kind::command&&error!=SRT_EASYNCSND)trace(CommandTracePoint::provider_error,CommandTraceReason::provider_error,packet->envelope.request_id,packet->envelope.route_id,unsigned(error));if(error!=SRT_EASYNCSND)lost(i,CommandTraceReason::provider_error,unsigned(error));return;}
            require(count==static_cast<int>(packet->size));
            if(packet->envelope.kind==Kind::command)trace(CommandTracePoint::provider_sent,CommandTraceReason::none,packet->envelope.request_id,packet->envelope.route_id);
            ++current.sent;if(packet->envelope.kind==Kind::sample)++current.sensor_sent;
            if(packet->envelope.kind==Kind::command||packet->envelope.kind==Kind::query)remember(packet->envelope);
            else if(packet->envelope.kind==Kind::error)++current.errors_sent;
            const auto route=packet->envelope.route_id;
            if(!i){if(proof!=command_proofs.end())proof->reset();queues.control_sent();}else if(binding)queues.binding_sent();else queues.sensor_sent(route);
        }
    }
    void timers(){
        refresh_grants();
        apply(session.tick(monotonic_ns()));
        if((control_ready(session.state())||session.state()==SessionState::synchronizing)&&monotonic_ns()>=next_probe){apply(session.begin_probe(monotonic_ns()));next_probe=monotonic_ns()+second;}
        for(unsigned i=0;i<2;++i){auto& link=links[i];
            if(config.session.role==Role::caller){
                const bool enabled=!i||control_ready(session.state());
                if(enabled&&session.state()!=SessionState::failed){
                    if(link.retry.state()==RetryState::idle||link.retry.state()==RetryState::cancelled)link.retry.activate(monotonic_ns());
                    connect(i,link.retry.poll(monotonic_ns()));
                }else if(i){link.retry.cancel();close_fd(link.fd);link.ready=false;}
            }
            if(link.fd==SRT_INVALID_SOCK)continue;
            const auto state=srt_getsockstate(link.fd);
            if(state==SRTS_BROKEN||state==SRTS_CLOSED||state==SRTS_NONEXIST){lost(i,CommandTraceReason::socket_state,unsigned(state));continue;}
            if(!link.ready){if(monotonic_ns()>=link.security_deadline){lost(i,CommandTraceReason::security_timeout);continue;}if(state==SRTS_CONNECTED)secured(i);}
        }
    }
    void run() noexcept {
        try{
            Provider provider;
            try{
                epoll=srt_epoll_create();require(epoll>=0);require(srt_epoll_set(epoll,SRT_EPOLL_ENABLE_EMPTY)!=SRT_ERROR);
                if(config.session.role==Role::listener){listen(0);listen(1);}
                current.running=true;publish();
                while(!stopping.load(std::memory_order_relaxed)){
                    timers();provider_sample(0);provider_sample(1);publish();process_retained();process_checks();inputs();send(0);send(1);
                    if(links[0].ready){int events=SRT_EPOLL_ERR|(control_space()?SRT_EPOLL_IN:0);require(srt_epoll_update_usock(epoll,links[0].fd,&events)!=SRT_ERROR);}
                    // Keep the active sender's maximum requested wait at 1ms.
                    // If a paced sample becomes eligible sooner, poll SRT first,
                    // then sleep only to that deadline. Never spin or round a
                    // near-due sample past its next replacement arrival.
                    const auto before_wait=monotonic_ns();
                    const bool sending=config.session.role==Role::caller&&session.state()==SessionState::active;
                    std::uint64_t wait_ns=sending?1000000:10000000;
                    if(sending){const auto due=queues.sensor_due_ns(before_wait);if(due&&*due>before_wait)wait_ns=std::min(wait_ns,*due-before_wait);}
                    const int wait_ms=static_cast<int>(wait_ns/1000000);
                    const auto wake_at=before_wait+wait_ns;
                    std::array<SRT_EPOLL_EVENT,4> events{};const int count=srt_epoll_uwait(epoll,events.data(),events.size(),wait_ms);
                    if(count==SRT_ERROR&&srt_getlasterror(nullptr)!=SRT_ETIMEOUT)throw std::runtime_error("epoll failed");
                    if(count<=0){
                        if(!wait_ms){const auto time=monotonic_ns();if(time<wake_at)std::this_thread::sleep_for(std::chrono::nanoseconds(wake_at-time));}
                        continue;
                    }
                    for(int n=0;n<count;++n)for(unsigned i=0;i<2;++i){
                        if(events[n].fd==links[i].listener){if(events[n].events&SRT_EPOLL_ERR)throw std::runtime_error("listener failed");accept(i);}
                        else if(events[n].fd==links[i].fd){if(events[n].events&SRT_EPOLL_ERR)lost(i,CommandTraceReason::epoll_error,unsigned(events[n].events));else if(links[i].ready&&(events[n].events&SRT_EPOLL_IN))receive(i);}
                    }
                }
            }catch(...){current.fault=TransportFault::io;}
            shutting_down=true;trace(CommandTracePoint::transport_stopping,CommandTraceReason::shutdown,{},0,unsigned(current.fault));
            apply(session.stop());queues.stop();links[0].retry.cancel();links[1].retry.cancel();
            for(auto& link:links){close_fd(link.fd);close_fd(link.listener);}
            if(epoll>=0){srt_epoll_release(epoll);epoll=-1;}
        }catch(...){current.fault=TransportFault::provider;}
        stopping=true;current.running=false;publish();
    }
    SubmitResult enqueue_check(TransportContext context,const Envelope& command,std::uint64_t token,std::shared_ptr<execution_detail::Record> proof={}){
        if(stopping.load())return SubmitResult::stopped;
        std::unique_lock lock(mutex,std::try_to_lock);if(!lock.owns_lock())return SubmitResult::busy;
        if(stopping.load())return SubmitResult::stopped;
        if(!same_control(context,shared.context))return SubmitResult::obsolete;
        auto empty=checks.end();for(auto at=checks.begin();at!=checks.end();++at){if(at->state&&at->result.token==token)return SubmitResult::invalid;if(!at->state)empty=at;}
        if(empty==checks.end())return SubmitResult::busy;
        if(proof&&(!proof->live->load()||proof->requested.exchange(true)))return SubmitResult::obsolete;
        *empty={1,context,command,{token,0,0,context,SessionError::invalid_state},std::move(proof)};return SubmitResult::queued;
    }
    SubmitResult submit(Input item){
        if(stopping.load())return SubmitResult::stopped;
        std::unique_lock lock(mutex,std::try_to_lock);if(!lock.owns_lock())return SubmitResult::busy;
        if(stopping.load())return SubmitResult::stopped;
        if((item.kind==Kind::sample?item.context!=shared.context:!same_control(item.context,shared.context))||zero(item.context.session))return SubmitResult::obsolete;
        if(item.kind==Kind::sample){const auto at=index(item.route);if(at==route_count)return SubmitResult::invalid;
            ++mailbox_counts.sensor_submitted;
            if(sample_pending[at]){++shared.sensor_replaced;++mailbox_counts.sensor_ingress_replaced;}
            samples[at]=item;sample_pending[at]=true;
        }else{
            if(input_count+(pending_command?1:0)==controls.size()||(item.proof&&input_commands+(pending_command?1:0)==56))return SubmitResult::busy;
            if(item.proof){if(!item.proof->live->load()||item.proof->claimed.exchange(true))return SubmitResult::obsolete;++input_commands;}
            controls[(input_head+input_count++)%controls.size()]=std::move(item);
        }
        return SubmitResult::queued;
    }
};
TransportOwner::TransportOwner(TransportConfig config):impl_(std::make_unique<Impl>(std::move(config))){}
TransportOwner::~TransportOwner()=default;
void TransportOwner::request_stop()noexcept{impl_->stopping=true;}
void TransportOwner::join(){request_stop();if(impl_->thread.joinable())impl_->thread.join();}
bool TransportOwner::authorize_sample(const TransportMessage& message)const{
    std::lock_guard lock(impl_->mutex);const auto time=monotonic_ns();
    return !impl_->stopping.load()&&impl_->publication_allowed&&message.envelope.kind==Kind::sample&&message.context==impl_->shared.context&&
        message.publication_epoch==impl_->publication_epoch&&time<message.deadline_ns&&time<impl_->shared.clock_deadline_ns;
}
TransportSnapshot TransportOwner::snapshot()const{std::lock_guard lock(impl_->mutex);return impl_->shared;}
SubmitResult TransportOwner::submit_sample(TransportContext context,std::uint32_t route,std::span<const std::byte> body,std::uint64_t ingress){
    const auto* definition=impl_->config.session.manifest.find(route);const auto time=monotonic_ns();
    if(impl_->config.session.role!=Role::caller||!definition||!definition->enabled||definition->kind!=RouteKind::sensor||body.size()>definition->max_payload_bytes||!ingress||ingress>time||time-ingress>=std::uint64_t(definition->budget_ms)*1000000)return SubmitResult::invalid;
    Impl::Input input;input.context=context;input.route=route;input.origin=ingress;input.size=body.size();std::copy(body.begin(),body.end(),input.bytes.begin());return impl_->submit(input);
}
SubmitResult TransportOwner::submit_query(TransportContext context,std::uint32_t route,Identity request){
    const auto* definition=impl_->config.session.manifest.find(route);
    if(impl_->config.session.role!=Role::listener||!definition||!definition->enabled||definition->kind!=RouteKind::command||zero(request))return SubmitResult::invalid;
    Impl::Input input;input.kind=Kind::query;input.context=context;input.route=route;input.request=request;return impl_->submit(input);
}
SubmitResult TransportOwner::submit_status(TransportContext context,std::uint32_t route,Identity request,const CommandStatus& status){
    const auto* definition=impl_->config.session.manifest.find(route);
    if(impl_->config.session.role!=Role::caller||!definition||!definition->enabled||definition->kind!=RouteKind::command||zero(request))return SubmitResult::invalid;
    Impl::Input input;input.kind=Kind::status;input.context=context;input.route=route;input.request=request;
    const auto result=encode_command_status(route,status,input.bytes);if(!result)return SubmitResult::invalid;
    input.size=result.bytes_written;return impl_->submit(input);
}
SubmitResult TransportOwner::submit_error(TransportContext context,std::uint32_t route,Identity request,const ControlError& error){
    const auto* definition=impl_->config.session.manifest.find(route);
    if(impl_->config.session.role!=Role::caller||!definition||!definition->enabled||definition->kind!=RouteKind::command||zero(request))return SubmitResult::invalid;
    Impl::Input input;input.kind=Kind::error;input.context=context;input.route=route;input.request=request;
    const auto result=encode_control_error(error,input.bytes);if(!result||result.bytes_written>definition->max_payload_bytes)return SubmitResult::invalid;
    input.size=result.bytes_written;return impl_->submit(input);
}
SubmitResult TransportOwner::submit_command(TransportContext context,DurableCommandTicket&& ticket){
    if(!ticket.proof_)return SubmitResult::invalid;
    const auto& p=*ticket.proof_;const auto& e=p.entry;const auto* route=impl_->config.session.manifest.find(e.route);
    if(impl_->config.session.role!=Role::listener||!route||!route->enabled||route->kind!=RouteKind::command||route->budget_ms!=e.command.budget_ms||
       p.local_peer!=impl_->config.session.local_peer_id||p.remote_peer!=impl_->config.session.expected_peer_id||e.owner_epoch!=impl_->config.session.local_epoch||e.context.source_epoch!=impl_->config.session.local_epoch||e.state!=CommandState::local_queued)return SubmitResult::invalid;
    if(!p.live->load()||p.claimed.load()||e.context.session!=context.session||impl_->time_expired(e))return SubmitResult::obsolete;
    Impl::Input input;input.kind=Kind::command;input.context=context;input.route=e.route;input.request=e.request_id;input.origin=e.context.source_monotonic_ns;input.proof=ticket.proof_;
    const auto encoded=encode_rate_command(e.command,input.bytes);if(!encoded)return SubmitResult::invalid;
    input.size=encoded.bytes_written;const auto result=impl_->submit(std::move(input));if(result==SubmitResult::queued)ticket.proof_.reset();return result;
}
SubmitResult TransportOwner::request_command_check(TransportContext context,const Envelope& command,std::uint64_t token){
    if(!token||command.kind!=Kind::command||impl_->config.session.role!=Role::caller)return SubmitResult::invalid;
    return impl_->enqueue_check(context,command,token);
}
SubmitResult TransportOwner::request_command_start(TransportContext context,const Envelope& command,DispatchTicket& ticket,std::uint64_t token){
    const auto record=ticket.record_;if(!record||!token||command.kind!=Kind::command||impl_->config.session.role!=Role::caller)return SubmitResult::invalid;
    const auto& e=record->entry;
    if(record->local_peer!=impl_->config.session.local_peer_id||record->remote_peer!=impl_->config.session.expected_peer_id||e.owner_epoch!=impl_->config.session.local_epoch||
       e.state!=CommandState::dispatching||e.request_id!=command.request_id||e.route!=command.route_id||e.context.session!=context.session||
       e.context.session!=command.session_id||e.context.source_epoch!=command.source_epoch||e.context.source_monotonic_ns!=command.source_monotonic_ns||e.command.budget_ms!=command.valid_for_ms)return SubmitResult::invalid;
    if(!record->live->load()||record->requested.load())return SubmitResult::obsolete;
    return impl_->enqueue_check(context,command,token,record);
}
bool TransportOwner::poll_command_check(CommandCheck& check){
    std::lock_guard lock(impl_->mutex);
    for(std::size_t n=0;n<impl_->checks.size();++n){const auto at=(impl_->check_poll_cursor+n)%impl_->checks.size();if(impl_->checks[at].state!=2)continue;
        check=impl_->checks[at].result;impl_->checks[at]={};impl_->check_poll_cursor=(at+1)%impl_->checks.size();return true;}
    return false;
}
bool TransportOwner::poll_control(TransportMessage& message){
    std::lock_guard lock(impl_->mutex);if(!impl_->output_count)return false;
    message=impl_->incoming[impl_->output_head];if(message.envelope.kind==Kind::command)--impl_->received_commands;impl_->incoming[impl_->output_head]={};impl_->output_head=(impl_->output_head+1)%impl_->incoming.size();--impl_->output_count;return true;
}
bool TransportOwner::poll_sample(TransportMessage& message){
    std::lock_guard lock(impl_->mutex);const auto time=monotonic_ns();
    for(std::size_t n=0;n<impl_->route_count;++n){const auto at=(impl_->sample_cursor+n)%impl_->route_count;if(!impl_->sample_received[at])continue;
        impl_->sample_received[at]=false;const auto& item=impl_->incoming_samples[at];if(time>=item.deadline_ns){++impl_->mailbox_counts.sensor_poll_expired;continue;}
        ++impl_->mailbox_counts.sensor_polled;message=item;impl_->sample_cursor=(at+1)%impl_->route_count;return true;}
    return false;
}
}
