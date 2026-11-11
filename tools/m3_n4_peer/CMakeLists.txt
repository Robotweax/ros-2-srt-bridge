cmake_minimum_required(VERSION 3.20)
project(m3_n4_peer LANGUAGES CXX)
set(M3_FIXTURE_SDK_PREFIX "" CACHE PATH "Explicit installed SDK; never rebuilt by this fixture")
if(M3_FIXTURE_SDK_PREFIX)
  find_package(RobotweaxBridge 0.1 CONFIG REQUIRED COMPONENTS endpoint
    PATHS "${M3_FIXTURE_SDK_PREFIX}/lib/cmake/RobotweaxBridge" NO_DEFAULT_PATH)
else()
  find_package(RobotweaxBridge 0.1 CONFIG REQUIRED COMPONENTS endpoint)
endif()
get_filename_component(_sdk_prefix "${RobotweaxBridge_DIR}/../../.." REALPATH)
if(M3_FIXTURE_SDK_PREFIX)
  get_filename_component(_requested_prefix "${M3_FIXTURE_SDK_PREFIX}" REALPATH)
  if(NOT _sdk_prefix STREQUAL _requested_prefix)
    message(FATAL_ERROR "Resolved SDK differs from explicit fixture prefix")
  endif()
endif()
find_package(Python3 REQUIRED COMPONENTS Interpreter)
add_executable(m3_n4_peer main.cpp)
target_link_libraries(m3_n4_peer PRIVATE RobotweaxBridge::endpoint)
target_compile_definitions(m3_n4_peer PRIVATE N4_WORKER_EXECUTABLE="$<TARGET_FILE:RobotweaxBridge::journal_worker>")
target_compile_features(m3_n4_peer PRIVATE cxx_std_20)
target_compile_options(m3_n4_peer PRIVATE -Wall -Wextra -Wpedantic -Werror)
add_custom_command(TARGET m3_n4_peer POST_BUILD
  COMMAND "${Python3_EXECUTABLE}" "${CMAKE_CURRENT_SOURCE_DIR}/../m3_n4_fixture.py"
    --sdk "${_sdk_prefix}" --peer "$<TARGET_FILE:m3_n4_peer>"
    --worker "$<TARGET_FILE:RobotweaxBridge::journal_worker>"
    --provider "$<TARGET_FILE:RobotweaxSRT::srt>"
    --out "${CMAKE_CURRENT_BINARY_DIR}/fixture-binding.json"
  VERBATIM)
