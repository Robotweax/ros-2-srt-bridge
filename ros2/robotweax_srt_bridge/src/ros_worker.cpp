#include <robotweax_srt_bridge/ros_rate_backend.hpp>
int main(int argc,char** argv){robotweax::ros_bridge::RosRateBackend backend;return robotweax::srt_bridge::run_journal_worker(argc,argv,&backend);}
