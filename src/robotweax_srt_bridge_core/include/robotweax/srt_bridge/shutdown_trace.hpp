#pragma once
// Default-off, bounded diagnostic output. Never authorizes an endpoint operation.
#include <atomic>
#include <chrono>
#include <cstdio>
#include <cstdint>
#include <fcntl.h>
#include <memory>
#include <stdexcept>
#include <string>
#include <sys/stat.h>
#include <unistd.h>
#ifdef __linux__
#include <sys/syscall.h>
#endif

namespace robotweax::srt_bridge {
class ShutdownTrace {
    int fd_=-1;
    std::atomic<std::uint64_t> attempted_{0},dropped_{0};
public:
    static constexpr std::uint64_t limit=256;
    explicit ShutdownTrace(const std::string& path){
        // Exclusive creation refuses old files/symlinks; no credentials or payloads.
        fd_=open(path.c_str(),O_WRONLY|O_APPEND|O_CREAT|O_EXCL|O_CLOEXEC|O_NOFOLLOW|O_NONBLOCK,0600);
        if(fd_<0)throw std::runtime_error("cannot create shutdown trace");
        struct stat s{};
        if(fstat(fd_,&s)||!S_ISREG(s.st_mode)){close(fd_);fd_=-1;throw std::runtime_error("shutdown trace is not a regular file");}
    }
    ShutdownTrace(const ShutdownTrace&)=delete;
    ShutdownTrace& operator=(const ShutdownTrace&)=delete;
    ~ShutdownTrace(){if(fd_>=0)close(fd_);}
    std::uint64_t attempted()const noexcept{return attempted_.load();}
    std::uint64_t dropped()const noexcept{return dropped_.load();}
    void stage(const char* point,long detail=0)noexcept{
        const auto seq=attempted_.fetch_add(1)+1;
        if(seq>limit){++dropped_;return;}
        const auto ns=std::chrono::duration_cast<std::chrono::nanoseconds>(std::chrono::steady_clock::now().time_since_epoch()).count();
#ifdef __linux__
        const auto tid=static_cast<long>(syscall(SYS_gettid));
#else
        const auto tid=static_cast<long>(getpid()); // Native thread IDs supported on Linux only.
#endif
        char line[384];const int n=std::snprintf(line,sizeof(line),"{\"schema_version\":1,\"sequence\":%llu,\"monotonic_ns\":%llu,\"pid\":%ld,\"tid\":%ld,\"point\":\"%s\",\"detail\":%ld,\"dropped_before\":%llu}\n",
            static_cast<unsigned long long>(seq),static_cast<unsigned long long>(ns),static_cast<long>(getpid()),tid,point,detail,static_cast<unsigned long long>(dropped_.load()));
        if(n<=0||static_cast<std::size_t>(n)>=sizeof(line)||write(fd_,line,static_cast<std::size_t>(n))!=n)++dropped_;
    }
};
inline void shutdown_stage(const std::shared_ptr<ShutdownTrace>& trace,const char* point,long detail=0)noexcept{if(trace)trace->stage(point,detail);}
}
