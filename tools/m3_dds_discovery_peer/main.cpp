// Standalone native DDS diagnostic; never linked into bridge/simulator.
#include <fastdds/dds/domain/DomainParticipantFactory.hpp>
#include <fastdds/dds/domain/DomainParticipant.hpp>
#include <fastdds/dds/domain/DomainParticipantListener.hpp>
#include <fastdds/dds/publisher/Publisher.hpp>
#include <fastdds/dds/publisher/DataWriter.hpp>
#include <fastdds/dds/publisher/DataWriterListener.hpp>
#include <fastdds/dds/subscriber/Subscriber.hpp>
#include <fastdds/dds/subscriber/DataReader.hpp>
#include <fastdds/dds/subscriber/DataReaderListener.hpp>
#include <fastdds/dds/subscriber/SampleInfo.hpp>
#include <fastdds/dds/topic/Topic.hpp>
#include <fastdds/dds/topic/TypeSupport.hpp>
#include <fastdds/rtps/transport/UDPv4TransportDescriptor.h>
#include <fastrtps/utils/IPLocator.h>
#include <fastrtps/rtps/common/SerializedPayload.h>
#include <atomic>
#include <chrono>
#include <csignal>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <mutex>
#include <sstream>
#include <stdexcept>
#include <thread>
#include <unistd.h>
namespace native_dds=eprosima::fastdds::dds;
namespace rtps=eprosima::fastrtps::rtps;
using Clock=std::chrono::steady_clock;
static volatile std::sig_atomic_t signaled=0;
static void signal_stop(int){signaled=1;}
static uint64_t now(){return std::chrono::duration_cast<std::chrono::nanoseconds>(Clock::now().time_since_epoch()).count();}
static void require(bool ok,const char* message){if(!ok)throw std::runtime_error(message);}
static std::string text(const rtps::GUID_t& value){std::ostringstream s;s<<std::hex<<std::setfill('0');for(auto v:value.guidPrefix.value)s<<std::setw(2)<<unsigned(v);for(auto v:value.entityId.value)s<<std::setw(2)<<unsigned(v);return s.str();}
static std::atomic<uint64_t> decode_calls=0,decode_bad_length=0,decode_bad_header=0,last_payload_length=0;
struct Hello {uint32_t magic=0x48454c31,role=0;uint64_t sequence=0,sent_ns=0;};
class HelloType final:public native_dds::TopicDataType {
    static void put(unsigned char* p,uint64_t value,unsigned n){for(unsigned i=0;i<n;++i)p[i]=static_cast<unsigned char>(value>>(8*(n-i-1)));}
    static uint64_t get(const unsigned char* p,unsigned n){uint64_t v=0;for(unsigned i=0;i<n;++i)v=(v<<8)|p[i];return v;}
public:
    HelloType(){setName("M3DiscoveryHelloV1");m_typeSize=28;m_isGetKeyDefined=false;auto_fill_type_object(false);auto_fill_type_information(false);}
    bool serialize(void* data,rtps::SerializedPayload_t* payload) override {
        if(payload->max_size<28)return false;
        const auto& h=*static_cast<Hello*>(data);auto* p=payload->data;
        for(unsigned i=0;i<4;++i)p[i]=0;
        put(p+4,h.magic,4);put(p+8,h.role,4);put(p+12,h.sequence,8);put(p+20,h.sent_ns,8);payload->length=28;payload->encapsulation=0;return true;
    }
    bool deserialize(rtps::SerializedPayload_t* payload,void* data) override {
        ++decode_calls;last_payload_length=payload->length;
        if(payload->length!=28){++decode_bad_length;return false;}
        const auto* p=payload->data;
        if(p[0]||p[1]||p[2]||p[3]){++decode_bad_header;return false;}
        auto& h=*static_cast<Hello*>(data);h.magic=static_cast<uint32_t>(get(p+4,4));h.role=static_cast<uint32_t>(get(p+8,4));h.sequence=get(p+12,8);h.sent_ns=get(p+20,8);return true;
    }
    std::function<uint32_t()> getSerializedSizeProvider(void*) override {return [](){return 28;};}
    void* createData() override {return new Hello;}
    void deleteData(void* p) override {delete static_cast<Hello*>(p);}
    bool getKey(void*,rtps::InstanceHandle_t*,bool) override {return false;}
};
struct Trace {
    std::mutex mutex;uint64_t attempted=0,recorded=0;std::atomic<bool> exhausted=false;
    void emit(const std::string& fields){std::lock_guard lock(mutex);++attempted;if(recorded>=2048){exhausted=true;return;}++recorded;std::cout<<"DDS_PROBE {\"record\":"<<recorded<<",\"monotonic_ns\":"<<now()<<","<<fields<<"}\n"<<std::flush;}
    void finish(bool closed,uint64_t elapsed){std::lock_guard lock(mutex);std::cout<<"DDS_PROBE_STATUS {\"attempted\":"<<attempted<<",\"recorded\":"<<recorded<<",\"limit\":2048,\"exhausted\":"<<(exhausted?"true":"false")<<",\"dds_closed\":"<<(closed?"true":"false")<<",\"shutdown_ns\":"<<elapsed<<"}\n"<<std::flush;}
};
struct ParticipantListener final:native_dds::DomainParticipantListener {
    Trace& trace;std::atomic<bool> peer=false;
    explicit ParticipantListener(Trace& t):trace(t){}
    void on_participant_discovery(native_dds::DomainParticipant*,rtps::ParticipantDiscoveryInfo&& info) override {
        if(info.status==rtps::ParticipantDiscoveryInfo::DISCOVERED_PARTICIPANT)peer=true;
        else if(info.status==rtps::ParticipantDiscoveryInfo::REMOVED_PARTICIPANT||info.status==rtps::ParticipantDiscoveryInfo::DROPPED_PARTICIPANT)peer=false;
        trace.emit("\"event\":\"participant\",\"status\":"+std::to_string(info.status));
    }
};
struct WriterListener final:native_dds::DataWriterListener {
    Trace& trace;std::atomic<int> matches=0;
    explicit WriterListener(Trace& t):trace(t){}
    void on_publication_matched(native_dds::DataWriter*,const native_dds::PublicationMatchedStatus& s) override {matches=s.current_count;trace.emit("\"event\":\"writer_match\",\"current\":"+std::to_string(s.current_count));}
};
struct ReaderListener final:native_dds::DataReaderListener {
    Trace& trace;const uint32_t expected;std::atomic<int> matches=0;std::atomic<uint64_t> received=0,invalid=0,callbacks=0,take_errors=0;uint64_t last=0;
    ReaderListener(Trace& t,uint32_t e):trace(t),expected(e){}
    void on_subscription_matched(native_dds::DataReader*,const native_dds::SubscriptionMatchedStatus& s) override {matches=s.current_count;trace.emit("\"event\":\"reader_match\",\"current\":"+std::to_string(s.current_count));}
    void on_sample_rejected(native_dds::DataReader*,const native_dds::SampleRejectedStatus& s) override {trace.emit("\"event\":\"sample_rejected\",\"reason\":"+std::to_string(s.last_reason));}
    void on_sample_lost(native_dds::DataReader*,const native_dds::SampleLostStatus& s) override {trace.emit("\"event\":\"sample_lost\",\"count\":"+std::to_string(s.total_count));}
    void on_data_available(native_dds::DataReader* reader) override {
        ++callbacks;Hello h;native_dds::SampleInfo info;
        for(;;){
            const auto code=reader->take_next_sample(&h,&info);
            if(code==eprosima::fastrtps::types::ReturnCode_t::RETCODE_NO_DATA)break;
            if(code!=eprosima::fastrtps::types::ReturnCode_t::RETCODE_OK){++take_errors;break;}
            if(!info.valid_data)continue;
            const auto stamp=now();const bool valid=h.magic==0x48454c31&&h.role==expected&&h.sequence>last&&h.sent_ns>0&&h.sent_ns<=stamp;
            if(valid){++received;last=h.sequence;}else ++invalid;
            trace.emit("\"event\":\"hello_received\",\"valid\":"+std::string(valid?"true":"false")+",\"sequence\":"+std::to_string(h.sequence)+",\"sent_ns\":"+std::to_string(h.sent_ns));
        }
    }
};
struct ParticipantGuard {
    native_dds::DomainParticipant* p=nullptr;
    bool close(){if(!p)return true;auto* old=p;p=nullptr;const auto a=old->delete_contained_entities();const auto b=native_dds::DomainParticipantFactory::get_instance()->delete_participant(old);return a==eprosima::fastrtps::types::ReturnCode_t::RETCODE_OK&&b==eprosima::fastrtps::types::ReturnCode_t::RETCODE_OK;}
    ~ParticipantGuard(){close();}
};
int main(int argc,char** argv){
    if(argc!=5){std::cerr<<"role local-ip peer-ip output-directory required\n";return 2;}
    std::signal(SIGINT,signal_stop);std::signal(SIGTERM,signal_stop);
    Trace trace;ParticipantListener participant_listener(trace);WriterListener writer_listener(trace);
    const std::string role=argv[1];const uint32_t number=role=="operator"?1:2;ReaderListener reader_listener(trace,number==1?2:1);ParticipantGuard guard;
    try {
        require(role=="robot"||role=="operator","invalid role");
        native_dds::DomainParticipantQos qos; qos.name("m3_fragment_"+role);qos.transport().use_builtin_transports=false;
        auto transport=std::make_shared<eprosima::fastdds::rtps::UDPv4TransportDescriptor>();transport->maxMessageSize=65000;transport->interfaceWhiteList.push_back(argv[2]);qos.transport().user_transports.push_back(transport);
        rtps::Locator_t meta,user,peer;meta.kind=LOCATOR_KIND_UDPv4;eprosima::fastrtps::rtps::IPLocator::setIPv4(meta,argv[2]);meta.port=26010;user=meta;user.port=26011;peer=meta;eprosima::fastrtps::rtps::IPLocator::setIPv4(peer,argv[3]);
        qos.wire_protocol().builtin.metatrafficUnicastLocatorList.push_back(meta);qos.wire_protocol().builtin.initialPeersList.push_back(peer);qos.wire_protocol().default_unicast_locator_list.push_back(user);
        guard.p=native_dds::DomainParticipantFactory::get_instance()->create_participant(60,qos,&participant_listener);require(guard.p,"participant creation failed");
        native_dds::TypeSupport type(new HelloType);require(type.register_type(guard.p)==eprosima::fastrtps::types::ReturnCode_t::RETCODE_OK,"type registration failed");
        auto* publisher=guard.p->create_publisher(native_dds::PUBLISHER_QOS_DEFAULT);auto* subscriber=guard.p->create_subscriber(native_dds::SUBSCRIBER_QOS_DEFAULT);require(publisher&&subscriber,"owner creation failed");
        auto* out=guard.p->create_topic(number==1?"M3FragmentHelloOperator":"M3FragmentHelloRobot",type.get_type_name(),native_dds::TOPIC_QOS_DEFAULT);
        auto* in=guard.p->create_topic(number==1?"M3FragmentHelloRobot":"M3FragmentHelloOperator",type.get_type_name(),native_dds::TOPIC_QOS_DEFAULT);require(out&&in,"topic creation failed");
        native_dds::DataWriterQos wq;native_dds::DataReaderQos rq;wq.reliability().kind=native_dds::BEST_EFFORT_RELIABILITY_QOS;rq.reliability().kind=native_dds::BEST_EFFORT_RELIABILITY_QOS;wq.history().depth=1;rq.history().depth=1;wq.data_sharing().off();rq.data_sharing().off();
        wq.durability().kind=native_dds::VOLATILE_DURABILITY_QOS;rq.durability().kind=native_dds::VOLATILE_DURABILITY_QOS;wq.history().kind=native_dds::KEEP_LAST_HISTORY_QOS;rq.history().kind=native_dds::KEEP_LAST_HISTORY_QOS;
        const std::vector<rtps::octet> metadata(number==2?4096:0,0x41);wq.user_data()=metadata;rq.user_data()=metadata;
        auto* writer=publisher->create_datawriter(out,wq,&writer_listener);auto* reader=subscriber->create_datareader(in,rq,&reader_listener);require(writer&&reader,"endpoint creation failed");
        const auto policy=[](const auto& q){return q.reliability().kind==native_dds::BEST_EFFORT_RELIABILITY_QOS&&q.durability().kind==native_dds::VOLATILE_DURABILITY_QOS&&q.history().kind==native_dds::KEEP_LAST_HISTORY_QOS&&q.history().depth==1&&q.data_sharing().kind()==native_dds::OFF;};
        require(policy(writer->get_qos())&&policy(reader->get_qos()),"native HELLO QoS readback failed");
        require(writer->get_qos().user_data().size()==metadata.size()&&reader->get_qos().user_data().size()==metadata.size(),"endpoint metadata readback mismatch");
        const auto begun=now();uint64_t sent=0,next_send=begun,next_state=begun;
        const auto path=std::filesystem::path(argv[4])/(role+"-probe-state.json");
        while(!signaled&&now()-begun<110000000000ULL&&!trace.exhausted){
            const auto stamp=now();
            if(stamp>=next_send){Hello h;h.role=number;h.sequence=++sent;h.sent_ns=stamp;require(writer->write(&h),"HELLO write failed");next_send=stamp+100000000;}
            if(stamp>=next_state){
                const std::string state="\"event\":\"state\",\"pid\":"+std::to_string(getpid())+",\"started_ns\":"+std::to_string(begun)+",\"participant\":\""+text(guard.p->guid())+"\",\"writer\":\""+text(writer->guid())+"\",\"reader\":\""+text(reader->guid())+"\",\"writer_metadata_bytes\":"+std::to_string(metadata.size())+",\"reader_metadata_bytes\":"+std::to_string(metadata.size())+",\"peer_discovered\":"+(participant_listener.peer?"true":"false")+",\"writer_matches\":"+std::to_string(writer_listener.matches)+",\"reader_matches\":"+std::to_string(reader_listener.matches)+",\"sent\":"+std::to_string(sent)+",\"received\":"+std::to_string(reader_listener.received)+",\"invalid\":"+std::to_string(reader_listener.invalid)+",\"reader_callbacks\":"+std::to_string(reader_listener.callbacks)+",\"take_errors\":"+std::to_string(reader_listener.take_errors)+",\"decode_calls\":"+std::to_string(decode_calls)+",\"decode_bad_length\":"+std::to_string(decode_bad_length)+",\"decode_bad_header\":"+std::to_string(decode_bad_header)+",\"last_payload_length\":"+std::to_string(last_payload_length)+",\"unread\":"+std::to_string(reader->get_unread_count());
                trace.emit(state);std::ofstream f(path.string()+".tmp");f<<"{\"monotonic_ns\":"<<stamp<<","<<state<<"}\n";f.close();std::filesystem::rename(path.string()+".tmp",path);next_state=stamp+200000000;
            }
            std::this_thread::sleep_for(std::chrono::milliseconds(10));
        }
        require(signaled&&!trace.exhausted,"probe watchdog/budget exhausted");
        const auto before=now();const bool closed=guard.close();const auto elapsed=now()-before;trace.finish(closed,elapsed);require(closed&&elapsed<5000000000ULL,"DDS teardown failed");return 0;
    }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
}
