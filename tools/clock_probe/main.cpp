// Read-only Linux clock diagnostics. Never sets clocks or requests CAP_SYS_TIME.
#include <cerrno>
#include <chrono>
#include <cstdint>
#include <cstdlib>
#include <iostream>
#include <stdexcept>
#include <sys/syscall.h>
#include <sys/timex.h>
#include <thread>
#include <time.h>
#include <unistd.h>

int64_t read_clock(clockid_t id, bool direct) {
  timespec value{};
  const auto result = direct ? syscall(SYS_clock_gettime, id, &value) : clock_gettime(id, &value);
  if (result != 0) throw std::runtime_error("clock_gettime failed");
  return int64_t(value.tv_sec)*1000000000 + value.tv_nsec;
}
void bracket(const char* name, bool direct, clockid_t target) {
  const auto begin=read_clock(CLOCK_MONOTONIC,direct);
  const auto value=read_clock(target,direct);
  const auto end=read_clock(CLOCK_MONOTONIC,direct);
  std::cout << '\"' << name << "\":{\"begin_ns\":" << begin << ",\"value_ns\":" << value << ",\"end_ns\":" << end << '}';
}
int main(int argc, char** argv) {
  try {
    if (argc!=2) throw std::runtime_error("usage: clock_probe SECONDS (1..600)");
    char* rest=nullptr;const long seconds=std::strtol(argv[1],&rest,10);
    if (*rest || seconds<1 || seconds>600) throw std::runtime_error("invalid duration");
    const auto end=std::chrono::steady_clock::now()+std::chrono::seconds(seconds);
    do {
      std::cout << '{';bracket("libc_realtime",false,CLOCK_REALTIME);std::cout << ',';
      bracket("syscall_realtime",true,CLOCK_REALTIME);std::cout << ',';
      bracket("syscall_raw",true,CLOCK_MONOTONIC_RAW);std::cout << ',';
      bracket("syscall_boottime",true,CLOCK_BOOTTIME);
      timex state{}; // modes=0 reads status only, no clock adjustment.
      const int status=adjtimex(&state);
      if (status<0) throw std::runtime_error("read-only adjtimex failed");
      std::cout << ",\"adjtimex\":{\"modes\":0,\"state\":" << status
                << ",\"status\":" << state.status << ",\"offset\":" << state.offset
                << ",\"freq_scaled_ppm\":" << state.freq << ",\"tai\":" << state.tai << "}}\n" << std::flush;
      std::this_thread::sleep_for(std::chrono::milliseconds(100));
    } while(std::chrono::steady_clock::now()<end);
    return 0;
  } catch(const std::exception& error) { std::cerr << error.what() << '\n';return 1; }
}
