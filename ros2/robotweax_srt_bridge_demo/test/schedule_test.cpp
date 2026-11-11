#include <gtest/gtest.h>
#include "schedule.hpp"
using robotweax::srt_bridge_demo::periodic_due;
TEST(Schedule,PreservesTwoHundredHertzUnderLateCallbacks){
    std::uint64_t next=0;unsigned published=0;
    for(std::uint64_t now=0;now<1000000000;now+=1100000){if(periodic_due(next,now,5000000))++published;}
    EXPECT_EQ(published,200U);EXPECT_EQ(next,1000000000U);
}
TEST(Schedule,SkipsMissedSlotsWithoutCatchupBurst){
    std::uint64_t next=10;
    EXPECT_TRUE(periodic_due(next,100,5));EXPECT_EQ(next,105U);
    EXPECT_FALSE(periodic_due(next,100,5));EXPECT_FALSE(periodic_due(next,104,5));
    EXPECT_TRUE(periodic_due(next,105,5));EXPECT_EQ(next,110U);
}
TEST(Schedule,ChecksBoundaryAndInvalidPeriod){
    std::uint64_t next=50;
    EXPECT_FALSE(periodic_due(next,49,5));EXPECT_TRUE(periodic_due(next,50,5));EXPECT_EQ(next,55U);
    EXPECT_FALSE(periodic_due(next,100,0));EXPECT_EQ(next,55U);
}
TEST(Schedule,SaturatesBeforeMonotonicOverflow){
    constexpr auto maximum=std::numeric_limits<std::uint64_t>::max();std::uint64_t next=maximum-5;
    EXPECT_TRUE(periodic_due(next,maximum-2,10));EXPECT_EQ(next,maximum);
    EXPECT_FALSE(periodic_due(next,maximum,10));
}
