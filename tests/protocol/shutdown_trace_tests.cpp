#include <robotweax/srt_bridge/shutdown_trace.hpp>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <set>
#include <thread>
#include <vector>
using namespace robotweax::srt_bridge;
void check(bool v){if(!v)throw std::runtime_error("shutdown trace contract");}
int main(){
    char pattern[]="/tmp/bridge-shutdown-unit-XXXXXX";char* name=mkdtemp(pattern);check(name);std::filesystem::path root(name);
    shutdown_stage({},"disabled");check(std::filesystem::is_empty(root));
    const auto file=root/"stages.jsonl";
    {
        auto trace=std::make_shared<ShutdownTrace>(file.string());
        bool rejected=false;try{ShutdownTrace duplicate(file.string());}catch(const std::runtime_error&){rejected=true;}check(rejected);
        std::vector<std::thread> threads;for(unsigned i=0;i<4;++i)threads.emplace_back([trace]{for(unsigned n=0;n<16;++n)shutdown_stage(trace,"unit_stage",7);});
        for(auto& t:threads){t.join();}
        check(trace->attempted()==64&&trace->dropped()==0);
        for(unsigned i=64;i<ShutdownTrace::limit+5;++i)trace->stage("unit_stage");
        check(trace->attempted()==ShutdownTrace::limit+5&&trace->dropped()==5);
    }
    std::ifstream log(file);std::string line;std::set<std::uint64_t> seq;unsigned lines=0;
    while(std::getline(log,line)){++lines;check(line.size()<384&&line.front()=='{'&&line.back()=='}');const auto start=line.find("\"sequence\":")+11;seq.insert(std::stoull(line.substr(start)));check(line.find("\"point\":\"unit_stage\"")!=std::string::npos);}
    check(lines==ShutdownTrace::limit&&seq.size()==lines&&*seq.begin()==1&&*seq.rbegin()==ShutdownTrace::limit);
    {
        const auto path=root/"socket.jsonl";auto trace=std::make_shared<ShutdownTrace>(path.string());int calls=0;
        check(shutdown_socket_close({},17,true,[&]{++calls;return 0;})==0&&calls==1);
        check(trace->attempted()==0);
        check(shutdown_socket_close(trace,17,false,[&]{++calls;return -1;})==-1&&calls==2);
        check(trace->attempted()==0);
        shutdown_stage(trace,"control_fd_disposition",-1); // explicit already-invalid slot
        check(shutdown_socket_close(trace,19,true,[&]{++calls;return 0;})==0);
        check(shutdown_socket_close(trace,20,true,[&]{++calls;return -1;})==-1&&calls==4);
        check(trace->attempted()==7&&trace->dropped()==0);trace.reset();
        std::ifstream socket_log(path);std::string contents((std::istreambuf_iterator<char>(socket_log)),{});
        check(contents.find("\"point\":\"control_fd_disposition\",\"detail\":-1")!=std::string::npos);
        check(contents.find("\"point\":\"socket_close_result\",\"detail\":0")!=std::string::npos);
        check(contents.find("\"point\":\"socket_close_result\",\"detail\":-1")!=std::string::npos);
    }
    std::filesystem::remove_all(root);std::cout<<"PASS default-off, exclusive output, concurrent records and bounded loss accounting\n";
}
