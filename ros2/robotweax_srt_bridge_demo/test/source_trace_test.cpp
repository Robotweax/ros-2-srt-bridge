#include <gtest/gtest.h>
#include "source_trace.hpp"
#include <sstream>
using namespace robotweax::srt_bridge_demo;
namespace {
sensor_msgs::msg::Imu imu(){sensor_msgs::msg::Imu m;m.header.stamp.sec=1;m.header.stamp.nanosec=2;m.header.frame_id="demo_imu";m.orientation.w=1.;m.angular_velocity.x=200.;m.angular_velocity.z=1.;m.linear_acceleration.z=9.81;return m;}
sensor_msgs::msg::JointState joints(){sensor_msgs::msg::JointState m;m.header.stamp.sec=1;m.header.stamp.nanosec=2;m.header.frame_id="demo_base";for(unsigned i=0;i<6;++i){m.name.push_back("joint_"+std::to_string(i+1));m.position.push_back(i+.001);m.velocity.push_back(200.);m.effort.push_back(0.);}return m;}
}
TEST(SourceTrace,MatchesIndependentLogicalPayloadGoldens){
    const auto a=logical(imu()),b=logical(joints());
    EXPECT_TRUE(a.valid);EXPECT_EQ(a.size,320U);EXPECT_EQ(digest(a),"9b9fb4ab825de5547904f18cecdd6d3a3c2a8ad02788c3830367d59c1e86555d");
    EXPECT_TRUE(b.valid);EXPECT_EQ(b.size,251U);EXPECT_EQ(digest(b),"86afad2bc7c769a1aee62395b7c49a5b4ab90fdf131087065a09a37ee50f4ef3");
}
TEST(SourceTrace,RejectsOversizeAndMalformedFields){
    auto a=imu();a.header.frame_id=std::string(65,'x');EXPECT_FALSE(logical(a).valid);EXPECT_TRUE(digest(logical(a)).empty());
    a=imu();a.header.stamp.nanosec=1000000000;EXPECT_FALSE(logical(a).valid);
    auto b=joints();b.position.resize(1);EXPECT_FALSE(logical(b).valid);b=joints();b.name.push_back("extra");EXPECT_FALSE(logical(b).valid);
    Canonical c;for(unsigned i=0;i<929;++i)c.byte(0);EXPECT_FALSE(c.valid);EXPECT_EQ(c.size,928U);
}
TEST(SourceTrace,DefersOutputAndRetainsOverflowWithoutRepeatingDump){
    SourceTrace<2> trace;std::ostringstream out;
    trace.record(1,1,imu(),100,101,99,5,0);trace.record(2,1,joints(),102,103,99,20,0);trace.record(1,2,imu(),105,106,104,5,0);
    EXPECT_TRUE(out.str().empty());trace.dump(out);const auto first=out.str();
    EXPECT_NE(first.find("\"payload_sha256\":\"9b9fb4"),std::string::npos);
    EXPECT_NE(first.find("\"attempted\":3,\"recorded\":2,\"printed\":2,\"dropped\":1"),std::string::npos);
    EXPECT_NE(first.find("\"complete\":false"),std::string::npos);trace.dump(out);EXPECT_EQ(out.str(),first);
}
TEST(SourceTrace,SubsequentWindowPrintsOnlyNewRecordsAndFailuresStayVisible){
    SourceTrace<3> trace;std::ostringstream out;trace.record(1,1,imu(),100,101,99,5,0);trace.dump(out);
    EXPECT_NE(out.str().find("\"complete\":true"),std::string::npos);out.str("");
    auto bad=imu();bad.header.frame_id=std::string(65,'x');trace.record(1,2,bad,105,106,104,5,0);trace.dump(out);
    EXPECT_NE(out.str().find("\"window\":2,\"sequence\":2"),std::string::npos);
    EXPECT_EQ(out.str().find("\"sequence\":1"),std::string::npos);
    EXPECT_NE(out.str().find("\"encoding_failed\":1,\"hash_failed\":1"),std::string::npos);
    EXPECT_NE(out.str().find("\"complete\":false"),std::string::npos);
}
