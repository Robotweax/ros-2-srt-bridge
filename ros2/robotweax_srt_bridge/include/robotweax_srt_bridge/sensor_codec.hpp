#pragma once
#include <robotweax/srt_bridge/transport.hpp>
#include <rclcpp/serialization.hpp>
#include <rclcpp/serialized_message.hpp>
#include <sensor_msgs/msg/imu.hpp>
#include <sensor_msgs/msg/joint_state.hpp>
#include <rosidl_typesupport_cpp/message_type_support.hpp>
#include <algorithm>
#include <type_traits>
#include <cstring>
#include <iomanip>
#include <sstream>
#include <string_view>

namespace robotweax::ros_bridge {
namespace core=robotweax::srt_bridge;
inline bool text(std::string_view value){
    if(value.size()>64)return false;
    for(std::size_t i=0;i<value.size();){const auto c=static_cast<unsigned char>(value[i++]);if(!c)return false;if(c<128)continue;
        unsigned rest;std::uint32_t cp,minimum;
        if(c>=0xc2&&c<=0xdf){rest=1;cp=c&31;minimum=0x80;}else if(c>=0xe0&&c<=0xef){rest=2;cp=c&15;minimum=0x800;}else if(c>=0xf0&&c<=0xf4){rest=3;cp=c&7;minimum=0x10000;}else return false;
        if(rest>value.size()-i)return false;
        while(rest--){const auto byte=static_cast<unsigned char>(value[i++]);if((byte&0xc0)!=0x80)return false;cp=(cp<<6)|(byte&63);}
        if(cp<minimum||cp>0x10ffff||(cp>=0xd800&&cp<=0xdfff))return false;
    }
    return true;
}
inline bool valid(const sensor_msgs::msg::Imu& m){return text(m.header.frame_id)&&m.header.stamp.nanosec<1000000000;}
inline bool valid(const sensor_msgs::msg::JointState& m){const auto n=m.name.size();if(!text(m.header.frame_id)||m.header.stamp.nanosec>=1000000000||n>6)return false;
    for(const auto& name:m.name)if(!text(name))return false;
    for(const auto size:{m.position.size(),m.velocity.size(),m.effort.size()})if(size&&size!=n)return false;
    return true;
}
// Preflight the qualified Fast-CDR CDR1 little-endian layout before ROS can
// allocate any peer-sized string/vector. Alignment is relative to encapsulation.
class CdrReader {
    std::span<const std::byte> bytes_;std::size_t at_=4,reported_=4;bool ok_=true;
public:
    explicit CdrReader(std::span<const std::byte> bytes):bytes_(bytes){ok_=bytes.size()>=4&&bytes.size()<=928&&bytes[0]==std::byte{}&&bytes[1]==std::byte{1}&&bytes[2]==std::byte{}&&bytes[3]==std::byte{};}
    void align(std::size_t width){if(!ok_)return;const auto count=(width-(at_-4)%width)%width;if(count>bytes_.size()-at_){ok_=false;return;}at_+=count;reported_+=(width-(reported_-4)%width)%width;}
    void skip(std::size_t count){if(!ok_||count>bytes_.size()-at_){ok_=false;return;}at_+=count;reported_+=count;}
    std::uint32_t u32(){align(4);if(!ok_||bytes_.size()-at_<4){ok_=false;return 0;}std::uint32_t value=0;for(unsigned i=0;i<4;++i)value|=std::uint32_t(std::to_integer<unsigned>(bytes_[at_++]))<<(8*i);reported_+=4;return value;}
    void string(){const auto length=u32();if(!ok_||!length||length>65||length>bytes_.size()-at_){ok_=false;return;}if(bytes_[at_+length-1]!=std::byte{}||!text({reinterpret_cast<const char*>(bytes_.data()+at_),length-1})){ok_=false;return;}at_+=length;reported_+=length;}
    void header(){u32();if(u32()>=1000000000)ok_=false;string();}
    // Jazzy Fast-RTPS size calculation aligns empty vectors, while its actual
    // writer emits no empty-array alignment. The declared buffer length can
    // therefore include trailing unused bytes. Track both bounded cursors.
    void doubles(std::size_t count){if(count)align(8);else reported_+=(8-(reported_-4)%8)%8;skip(count*8);}
    void vector(std::size_t names){const auto count=u32();if(count&&count!=names){ok_=false;return;}doubles(count);}
    void names_and_vectors(){const auto count=u32();if(count>6){ok_=false;return;}for(std::size_t i=0;i<count;++i)string();vector(count);vector(count);vector(count);}
    bool done()const{return ok_&&reported_==bytes_.size()&&at_<=reported_;}
};
inline bool preflight_imu(std::span<const std::byte> bytes){CdrReader r(bytes);r.header();r.doubles(4+9+3+9+3+9);return r.done();}
inline bool preflight_joints(std::span<const std::byte> bytes){CdrReader r(bytes);r.header();r.names_and_vectors();return r.done();}
template<class T> bool preflight(std::span<const std::byte> bytes){if constexpr(std::is_same_v<T,sensor_msgs::msg::Imu>)return preflight_imu(bytes);else return preflight_joints(bytes);}
template<class T> std::string type_hash(){const auto* ts=rosidl_typesupport_cpp::get_message_type_support_handle<T>();if(!ts||!ts->get_type_hash_func)throw std::runtime_error("ROS type hash unavailable");const auto* hash=ts->get_type_hash_func(ts);if(!hash||hash->version!=1)throw std::runtime_error("unsupported ROS type hash");
    bool nonzero=false;std::ostringstream out;out<<"RIHS01_"<<std::hex<<std::setfill('0');for(auto b:hash->value){nonzero=nonzero||b;out<<std::setw(2)<<unsigned(b);}if(!nonzero)throw std::runtime_error("zero ROS type hash");return out.str();
}
struct SensorBytes {std::array<std::byte,928> bytes{};std::size_t size=0;};
template<class T> bool encode(const T& message,SensorBytes& out){if(!valid(message))return false;rclcpp::Serialization<T> codec;rclcpp::SerializedMessage serialized(928);std::memset(serialized.get_rcl_serialized_message().buffer,0,serialized.capacity());try{codec.serialize_message(&message,&serialized);}catch(const std::exception&){return false;}
    if(serialized.size()>out.bytes.size())return false;
    const auto bytes=std::span(reinterpret_cast<const std::byte*>(serialized.get_rcl_serialized_message().buffer),serialized.size());if(!preflight<T>(bytes))return false;
    std::copy(bytes.begin(),bytes.end(),out.bytes.begin());out.size=bytes.size();return true;
}
template<class T> bool decode(std::span<const std::byte> bytes,T& message){if(!preflight<T>(bytes))return false;rclcpp::SerializedMessage serialized(bytes.size());auto& raw=serialized.get_rcl_serialized_message();std::memcpy(raw.buffer,bytes.data(),bytes.size());raw.buffer_length=bytes.size();rclcpp::Serialization<T> codec;
    try{codec.deserialize_message(&serialized,&message);}catch(const std::exception&){return false;}return valid(message);
}
}
