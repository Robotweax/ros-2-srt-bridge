#include <robotweax/srt_bridge/wire.hpp>
#include <array>
#include <iostream>
int main(){using namespace robotweax::srt_bridge;Envelope e;e.route_id=1;e.sequence=1;
    const std::array<std::uint32_t,1> routes{1};std::array<std::byte,96> bytes{};
    const auto packed=encode(e,{},Channel::sensor,routes,bytes);if(!packed)return 1;
    const auto result=decode(bytes,Channel::sensor,routes);if(!result||result.message.envelope!=e)return 2;
    std::cout<<"PASS installed minimal core: wire roundtrip without ROS/SRT/Protobuf/SQLite\n";return 0;
}
