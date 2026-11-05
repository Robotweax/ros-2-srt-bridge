#include <rclcpp/serialization.hpp>
#include <rclcpp/serialized_message.hpp>
#include <sensor_msgs/msg/imu.hpp>
#include <sensor_msgs/msg/joint_state.hpp>
#include <rosidl_typesupport_cpp/message_type_support.hpp>
#include <algorithm>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>

namespace {
constexpr std::size_t envelope_bytes = 96;
constexpr std::size_t payload_limit = 1024 - envelope_bytes;
// Pilot contract: at most six joints; at most 64 UTF-8 bytes per joint name.
constexpr std::size_t name_limit = 64;
void require(bool value, const char* message) {
    if (!value) throw std::runtime_error(message);
}
template<class T> std::string hash() {
    const auto* support = rosidl_typesupport_cpp::get_message_type_support_handle<T>();
    require(support && support->get_type_hash_func, "type hash API missing");
    const auto* result = support->get_type_hash_func(support);
    require(result && result->version == 1, "missing or unsupported type hash");
    require(std::any_of(std::begin(result->value), std::end(result->value),
        [](auto value) { return value != 0; }), "zero type hash");
    std::ostringstream out;
    out << "RIHS01_" << std::hex << std::setfill('0');
    for (auto value : result->value) out << std::setw(2) << unsigned(value);
    return out.str();
}
template<class T> std::size_t roundtrip(const T& source) {
    rclcpp::Serialization<T> serialization;
    rclcpp::SerializedMessage buffer;
    serialization.serialize_message(&source, &buffer);
    T restored;
    serialization.deserialize_message(&buffer, &restored);
    require(restored == source, "CDR roundtrip mismatch");
    return buffer.size();
}
}
int main() {
    try {
        sensor_msgs::msg::Imu imu;
        imu.header.frame_id = std::string(64, 'f');
        imu.orientation.w = 1.;
        imu.angular_velocity.x = 2.;
        imu.linear_acceleration.z = 9.81;
        sensor_msgs::msg::JointState joints;
        joints.header.frame_id = std::string(64, 'f');
        joints.name.resize(6, std::string(name_limit, 'j'));
        joints.position.resize(6, 1.);
        joints.velocity.resize(6, 2.);
        joints.effort.resize(6, 3.);
        const auto imu_size = roundtrip(imu);
        const auto joint_size = roundtrip(joints);
        require(imu_size <= payload_limit, "bounded Imu does not fit");
        require(joint_size <= payload_limit, "bounded JointState does not fit");
        const auto imu_hash = hash<sensor_msgs::msg::Imu>();
        const auto joint_hash = hash<sensor_msgs::msg::JointState>();
        require(imu_hash != joint_hash, "distinct schemas have equal hashes");
        // Valid ROS messages can exceed the bridge budget: never infer a bound from type alone.
        joints.name[0] = std::string(1024, 'x');
        require(roundtrip(joints) > payload_limit, "oversize fixture unexpectedly fits");
        std::cout << "{\n  \"ros_distro\": \"jazzy\",\n  \"rmw\": \"rmw_fastrtps_cpp\",\n"
            << "  \"frame_id_max_utf8_bytes\": 64,\n  \"joint_name_max_utf8_bytes\": " << name_limit
            << ",\n  \"joint_count_max\": 6,\n  \"imu\": {\"type_hash\": \"" << imu_hash
            << "\", \"bounded_cdr_bytes\": " << imu_size << "},\n  \"joint_state\": {\"type_hash\": \"" << joint_hash
            << "\", \"bounded_cdr_bytes\": " << joint_size << "},\n  \"envelope_bytes\": 96,\n"
            << "  \"sensor_payload_budget_bytes\": " << payload_limit << "\n}\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "FAIL: " << error.what() << '\n'; return 1;
    }
}
