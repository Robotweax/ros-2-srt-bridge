#include <gtest/gtest.h>
#include <robotweax_srt_bridge/sensor_codec.hpp>
namespace rb=robotweax::ros_bridge;
TEST(SensorCodec,BoundsAndHashes){sensor_msgs::msg::Imu imu;imu.header.frame_id=std::string(64,'f');imu.orientation.w=1;rb::SensorBytes encoded;ASSERT_TRUE(rb::encode(imu,encoded));EXPECT_EQ(encoded.size,380U);sensor_msgs::msg::Imu copy;EXPECT_TRUE(rb::decode(std::span(encoded.bytes).first(encoded.size),copy));EXPECT_EQ(imu,copy);imu.header.frame_id+= 'x';EXPECT_FALSE(rb::encode(imu,encoded));EXPECT_NE(rb::type_hash<sensor_msgs::msg::Imu>(),rb::type_hash<sensor_msgs::msg::JointState>());}
TEST(SensorCodec,JointSequences){for(unsigned n=0;n<=6;++n)for(unsigned mask=0;mask<8;++mask){sensor_msgs::msg::JointState message;message.header.frame_id=std::string(64,'f');message.name.resize(n,std::string(64,'j'));if(mask&1)message.position.resize(n,1);if(mask&2)message.velocity.resize(n,2);if(mask&4)message.effort.resize(n,3);rb::SensorBytes bytes;ASSERT_TRUE(rb::encode(message,bytes))<<n<<"/"<<mask;sensor_msgs::msg::JointState copy;ASSERT_TRUE(rb::decode(std::span(bytes.bytes).first(bytes.size),copy));EXPECT_EQ(message,copy);if(n==6&&mask==7){EXPECT_EQ(bytes.size,684U);}}}
TEST(SensorCodec,RejectUnboundedOrInvalid){sensor_msgs::msg::JointState m;m.name.resize(7,"joint");rb::SensorBytes b;EXPECT_FALSE(rb::encode(m,b));m.name.resize(6);m.position.resize(5);EXPECT_FALSE(rb::encode(m,b));m.position.clear();m.name[0]=std::string(65,'j');EXPECT_FALSE(rb::encode(m,b));m.name[0]="\xc0\x80";EXPECT_FALSE(rb::encode(m,b));m.name[0]=std::string("a\0b",3);EXPECT_FALSE(rb::encode(m,b));}
TEST(SensorCodec,PreflightBeforeAllocation){sensor_msgs::msg::JointState m;rb::SensorBytes b;ASSERT_TRUE(rb::encode(m,b));auto bytes=b.bytes;for(unsigned i=12;i<16;++i)bytes[i]=std::byte{255};sensor_msgs::msg::JointState copy;EXPECT_FALSE(rb::decode(std::span(bytes).first(b.size),copy));for(std::size_t n=0;n<b.size;++n)EXPECT_FALSE(rb::decode(std::span(b.bytes).first(n),copy));bytes=b.bytes;bytes[1]=std::byte{3};EXPECT_FALSE(rb::decode(std::span(bytes).first(b.size),copy));}

TEST(SensorCodec,EmptyVectorPaddingIsZero){sensor_msgs::msg::JointState m;rb::SensorBytes b;ASSERT_TRUE(rb::encode(m,b));ASSERT_EQ(b.size,44U);for(std::size_t i=17;i<b.size;++i){EXPECT_EQ(b.bytes[i],std::byte{});}}
TEST(SensorCodec,AllFieldAlignments){
    for(unsigned frame=0;frame<8;++frame)for(unsigned n=0;n<=6;++n)for(unsigned mask=0;mask<8;++mask){
        sensor_msgs::msg::JointState m;m.header.frame_id=std::string(frame,'f');
        for(unsigned i=0;i<n;++i)m.name.push_back(std::string((frame+i)%8,'j'));
        if(mask&1){m.position.resize(n,1);}
        if(mask&2){m.velocity.resize(n,2);}
        if(mask&4){m.effort.resize(n,3);}
        rb::SensorBytes b;ASSERT_TRUE(rb::encode(m,b))<<frame<<"/"<<n<<"/"<<mask;
        sensor_msgs::msg::JointState copy;ASSERT_TRUE(rb::decode(std::span(b.bytes).first(b.size),copy));EXPECT_EQ(m,copy);
    }
}

#include <robotweax_srt_bridge/publication_metrics.hpp>
TEST(PublicationMetrics,BoundariesAndPopulation){
    rb::PublicationMetrics m;
    for(auto value:{0ULL,1ULL,1000000ULL,1000001ULL,249999999ULL,250000000ULL}){ASSERT_TRUE(m.observe(value));}
    EXPECT_FALSE(m.observe(250000001));EXPECT_FALSE(m.observe(UINT64_MAX));
    EXPECT_EQ(m.count,6U);EXPECT_EQ(m.maximum_ns,250000000U);
    EXPECT_EQ(m.age_upper_ms[0],1U);EXPECT_EQ(m.age_upper_ms[1],2U);EXPECT_EQ(m.age_upper_ms[2],1U);EXPECT_EQ(m.age_upper_ms[250],2U);
}
