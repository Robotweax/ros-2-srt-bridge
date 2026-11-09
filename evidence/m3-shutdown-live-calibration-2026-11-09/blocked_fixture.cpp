// Finite observation target only; never used by the bridge or a campaign case.
#include <robotweax/srt_bridge/shutdown_trace.hpp>
#include <condition_variable>
#include <csignal>
#include <fstream>
#include <mutex>
#include <thread>
volatile std::sig_atomic_t interrupted=0;
void signal_seen(int){interrupted=1;}
int main(int argc,char** argv){
    if(argc!=3)return 2;
    robotweax::srt_bridge::ShutdownTrace trace(argv[1]);
    std::signal(SIGINT,signal_seen);
    std::mutex mutex;std::condition_variable condition;bool done=false;
    std::thread thread([&]{std::unique_lock lock(mutex);condition.wait(lock,[&]{return done;});});
    trace.stage("fixture_ready");std::ofstream(argv[2])<<getpid()<<'\n';
    while(!interrupted)std::this_thread::sleep_for(std::chrono::milliseconds(1));
    trace.stage("fixture_sigint_observed");
    {std::unique_lock lock(mutex);trace.stage("fixture_blocked_begin");condition.wait_for(lock,std::chrono::seconds(3),[]{return false;});trace.stage("fixture_blocked_end");done=true;}
    condition.notify_all();thread.join();trace.stage("fixture_exit");return 0;
}
