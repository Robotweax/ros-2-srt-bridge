#include <robotweax/srt_bridge/journal.hpp>
#include <filesystem>
#include <iostream>
#include <stdexcept>
#include <sys/wait.h>
#include <poll.h>
#include <signal.h>
#include <fcntl.h>
#include <unistd.h>
using namespace robotweax::srt_bridge;
namespace {
unsigned checks=0;void check(bool b,const char* m){++checks;if(!b)throw std::runtime_error(m);}
Identity id(unsigned n){Identity i{};i[0]=static_cast<std::byte>(n);return i;}
struct Hook {JournalPoint point;int ready;};
void crash_hook(JournalPoint point,void* data){auto* h=static_cast<Hook*>(data);if(point!=h->point)return;const char byte='x';if(::write(h->ready,&byte,1)!=1)_exit(3);for(;;)pause();}
JournalOptions options(const std::filesystem::path& path){JournalOptions o;o.path=path.string();o.local_peer_id="robot";o.remote_peer_id="operator";o.process_epoch=id(1);return o;}
void kill_at(const std::filesystem::path& root,JournalPoint point,bool effect,CommandState expected,bool absent){
    const auto path=root/("phase-"+std::to_string(static_cast<int>(point))+".sqlite");int pipes[2];check(pipe(pipes)==0,"pipe");
    const auto child=fork();check(child>=0,"fork");
    if(child==0){
        ::close(pipes[0]);Hook hook{point,pipes[1]};auto o=options(path);o.test_hook=crash_hook;o.test_context=&hook;
        try{
            CommandJournal j(o);j.admit(id(1),100,{100,5000,0,1},{id(10),id(2),100,5000},100);
            j.begin_dispatch(id(1),id(10),true,200);
            if(effect){const auto marker=path.string()+".effect";const int fd=::open(marker.c_str(),O_CREAT|O_WRONLY|O_TRUNC,0600);
                if(fd<0||::write(fd,"applied-once",12)!=12||fsync(fd)!=0)_exit(4);
                ::close(fd);}
            j.finish(id(1),CommandState::succeeded,CommandReason::none,{100,1,true},300);
        }catch(...){_exit(5);} _exit(6);
    }
    ::close(pipes[1]);pollfd wait{pipes[0],POLLIN,0};const int ready=poll(&wait,1,15000);char byte=0;
    const bool reached=ready>0&&::read(pipes[0],&byte,1)==1&&byte=='x';::close(pipes[0]);
    kill(child,SIGKILL);int status=0;waitpid(child,&status,0);
    check(reached&&WIFSIGNALED(status)&&WTERMSIG(status)==SIGKILL,"worker did not reach crash barrier");
    auto o=options(path);o.process_epoch=id(9);CommandJournal recovered(o);auto record=recovered.get(id(1));
    if(absent)check(record.error==JournalError::not_found,"uncommitted admission survived");
    else{check(record&&record.entry->state==expected,"wrong restart state");
        check(recovered.begin_dispatch(id(1),id(10),true,400).error==JournalError::invalid_state,"restart admitted automatic execution");
        check(recovered.admit(id(1),100,{100,5000,0,1},{id(11),id(2),400,9000},400).entry->state==expected,"duplicate reset recovery state");}
    check(std::filesystem::exists(path.string()+".effect")==effect,"effect boundary changed");
}
}
int main(){try{
    auto root=std::filesystem::current_path()/("journal-crash-artifacts-"+std::to_string(getpid()));for(unsigned suffix=0;std::filesystem::exists(root);++suffix)root=std::filesystem::current_path()/("journal-crash-artifacts-"+std::to_string(getpid())+"-"+std::to_string(suffix));
    std::filesystem::create_directories(root);
    kill_at(root,JournalPoint::admission_before_commit,false,CommandState::unknown,true);
    kill_at(root,JournalPoint::admission_committed,false,CommandState::rejected,false);
    kill_at(root,JournalPoint::dispatch_committed,false,CommandState::unknown,false);
    kill_at(root,JournalPoint::result_before_commit,true,CommandState::unknown,false);
    kill_at(root,JournalPoint::result_committed,true,CommandState::succeeded,false);
    std::cout<<"PASS journal crash contract: "<<checks<<" checks, five SIGKILL boundaries\n";
}catch(const std::exception& e){std::cerr<<"FAIL: "<<e.what()<<'\n';return 1;}}
