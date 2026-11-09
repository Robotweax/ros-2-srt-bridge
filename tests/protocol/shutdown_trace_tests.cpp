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
    std::filesystem::remove_all(root);std::cout<<"PASS default-off, exclusive output, concurrent records and bounded loss accounting\n";
}
