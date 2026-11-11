#pragma once
#include <sensor_msgs/msg/imu.hpp>
#include <sensor_msgs/msg/joint_state.hpp>
#include <openssl/evp.h>
#include <array>
#include <bit>
#include <cstdint>
#include <ostream>
#include <string>

namespace robotweax::srt_bridge_demo {
// Logical fields, not CDR padding: route, header(sec,nsec,string), then all
// numeric/sequence fields in ROS declaration order, little endian, u32 lengths.
struct Canonical {
    std::array<unsigned char,928> bytes{};std::size_t size=0;bool valid=true;
    void byte(unsigned char value){if(size==bytes.size()){valid=false;return;}bytes[size++]=value;}
    void u32(std::uint32_t value){for(unsigned i=0;i<4;++i)byte(static_cast<unsigned char>(value>>(8*i)));}
    void text(const std::string& value){if(value.size()>64){valid=false;return;}u32(value.size());for(auto c:value)byte(static_cast<unsigned char>(c));}
    void number(double value){const auto bits=std::bit_cast<std::uint64_t>(value);for(unsigned i=0;i<8;++i)byte(static_cast<unsigned char>(bits>>(8*i)));}
    template<class T> void header(const T& h){u32(static_cast<std::uint32_t>(h.stamp.sec));u32(h.stamp.nanosec);if(h.stamp.nanosec>=1000000000)valid=false;text(h.frame_id);}
    template<class T> void vector3(const T& v){number(v.x);number(v.y);number(v.z);}
    template<class T> void numbers(const T& v){for(double n:v)number(n);}
};
inline Canonical logical(const sensor_msgs::msg::Imu& m){Canonical c;c.u32(1);c.header(m.header);c.vector3(m.orientation);c.number(m.orientation.w);c.numbers(m.orientation_covariance);c.vector3(m.angular_velocity);c.numbers(m.angular_velocity_covariance);c.vector3(m.linear_acceleration);c.numbers(m.linear_acceleration_covariance);return c;}
inline Canonical logical(const sensor_msgs::msg::JointState& m){Canonical c;c.u32(2);c.header(m.header);if(m.name.size()>6){c.valid=false;return c;}c.u32(m.name.size());for(const auto& n:m.name)c.text(n);for(const auto* v:{&m.position,&m.velocity,&m.effort}){if(v->size()>6||(v->size()&&v->size()!=m.name.size())){c.valid=false;return c;}c.u32(v->size());c.numbers(*v);}return c;}
inline std::string digest(const Canonical& c){
    if(!c.valid)return {};
    std::array<unsigned char,32> bytes{};unsigned n=bytes.size();
    if(EVP_Digest(c.bytes.data(),c.size,bytes.data(),&n,EVP_sha256(),nullptr)!=1||n!=bytes.size())return {};
    static constexpr char digits[]="0123456789abcdef";std::string result;result.reserve(64);
    for(auto b:bytes){result+=digits[b>>4];result+=digits[b&15];}return result;
}
// One serialized timer-group writer; dump only after publishing fence or join.
// Storage is fixed; hashing and JSON I/O are deferred until source is disabled.
// Trace failure never suppresses publication or changes the source schedule.
template<std::size_t Capacity=10000> class SourceTrace {
    struct Event {Canonical payload;std::uint64_t sequence=0,counter=0,begin_ns=0,end_ns=0,due_ns=0,period_ns=0,skipped=0;std::uint32_t route=0,nanosec=0;std::int32_t sec=0;};
    std::array<Event,Capacity> rows_{};std::size_t count_=0,cursor_=0;std::uint64_t attempted_=0,dropped_=0,encoding_failed_=0,hash_failed_=0,dumped_attempted_=0,window_=0;
public:
    template<class T> void record(std::uint32_t route,std::uint64_t counter,const T& m,std::uint64_t begin,std::uint64_t end,std::uint64_t due,std::uint64_t period,std::uint64_t skipped){
        ++attempted_;if(count_==Capacity){++dropped_;return;}auto& e=rows_[count_++];e.payload=logical(m);if(!e.payload.valid)++encoding_failed_;
        e.sequence=attempted_;e.counter=counter;e.begin_ns=begin;e.end_ns=end;e.due_ns=due;e.period_ns=period;e.skipped=skipped;e.route=route;e.sec=m.header.stamp.sec;e.nanosec=m.header.stamp.nanosec;
    }
    void dump(std::ostream& out){
        if(attempted_==dumped_attempted_)return;
        ++window_;const auto printed=count_-cursor_;
        for(;cursor_<count_;++cursor_){const auto& e=rows_[cursor_];const auto hash=digest(e.payload);if(hash.empty())++hash_failed_;
            out<<"SOURCE_TRACE {\"window\":"<<window_<<",\"sequence\":"<<e.sequence<<",\"route\":"<<e.route<<",\"counter\":"<<e.counter
                <<",\"stamp_sec\":"<<e.sec<<",\"stamp_nanosec\":"<<e.nanosec<<",\"begin_ns\":"<<e.begin_ns<<",\"end_ns\":"<<e.end_ns
                <<",\"due_ns\":"<<e.due_ns<<",\"period_ns\":"<<e.period_ns<<",\"skipped_slots\":"<<e.skipped<<",\"payload_bytes\":"<<e.payload.size
                <<",\"payload_sha256\":\""<<hash<<"\"}"<<'\n';
        }
        const bool complete=!dropped_&&!encoding_failed_&&!hash_failed_&&count_==attempted_&&out.good();
        out<<"SOURCE_TRACE_STATUS {\"schema_version\":1,\"window\":"<<window_<<",\"attempted\":"<<attempted_<<",\"recorded\":"<<count_<<",\"printed\":"<<printed
            <<",\"dropped\":"<<dropped_<<",\"encoding_failed\":"<<encoding_failed_<<",\"hash_failed\":"<<hash_failed_<<",\"limit\":"<<Capacity<<",\"complete\":"<<(complete?"true":"false")<<"}"<<std::endl;
        dumped_attempted_=attempted_;
    }
};
}
