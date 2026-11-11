#pragma once
#include <array>
#include <atomic>
#include <thread>
#include <stdexcept>
#include <cstddef>
#include <cstdint>
#include <cerrno>
#include <arpa/inet.h>
#include <poll.h>
#include <sys/socket.h>
#include <unistd.h>
class ControlGate {
    int fd_=-1;unsigned family_;std::uint16_t server_port_,port_=0;
    sockaddr_storage server_{};socklen_t server_length_=0;
    std::atomic<bool> stop_{false};std::thread thread_;
    static std::uint16_t port(const sockaddr_storage& address){return ntohs(address.ss_family==AF_INET?
        reinterpret_cast<const sockaddr_in&>(address).sin_port:reinterpret_cast<const sockaddr_in6&>(address).sin6_port);}
    void run(){
        sockaddr_storage client{};socklen_t client_length=0;std::array<std::byte,65536> bytes{};
        while(!stop_.load()){
            pollfd descriptor{fd_,POLLIN,0};const int ready=::poll(&descriptor,1,5);
            if(ready<0){if(errno==EINTR)continue;failed=true;return;}if(!ready)continue;
            for(unsigned n=0;n<64;++n){sockaddr_storage source{};socklen_t length=sizeof(source);
                const auto count=recvfrom(fd_,bytes.data(),bytes.size(),MSG_DONTWAIT,reinterpret_cast<sockaddr*>(&source),&length);
                if(count<0){if(errno==EAGAIN||errno==EWOULDBLOCK)break;if(errno==EINTR)continue;failed=true;return;}
                const bool from_server=port(source)==server_port_;
                if(from_server){if(!client_length)continue;if(drop_reply.load()){++dropped;continue;}}
                else{client=source;client_length=length;}
                const auto& destination=from_server?client:server_;
                const auto size=from_server?client_length:server_length_;
                if(sendto(fd_,bytes.data(),count,0,reinterpret_cast<const sockaddr*>(&destination),size)!=count){failed=true;return;}
                if(from_server)++forwarded_reply;else ++forwarded_request;
            }
        }
    }
public:
    std::atomic<bool> drop_reply{false},failed{false};
    std::atomic<unsigned> dropped{0},forwarded_reply{0},forwarded_request{0};
    ControlGate(bool ipv6,std::uint16_t server_port):family_(ipv6?AF_INET6:AF_INET),server_port_(server_port){
        fd_=socket(family_,SOCK_DGRAM|SOCK_NONBLOCK|SOCK_CLOEXEC,0);if(fd_<0)throw std::runtime_error("gate socket failed");
        try{
            sockaddr_storage local{};socklen_t length;
            if(ipv6){auto& a=reinterpret_cast<sockaddr_in6&>(local);a.sin6_family=AF_INET6;a.sin6_addr=in6addr_loopback;length=sizeof(a);
                auto& server=reinterpret_cast<sockaddr_in6&>(server_);server=a;server.sin6_port=htons(server_port);}
            else{auto& a=reinterpret_cast<sockaddr_in&>(local);a.sin_family=AF_INET;a.sin_addr.s_addr=htonl(INADDR_LOOPBACK);length=sizeof(a);
                auto& server=reinterpret_cast<sockaddr_in&>(server_);server=a;server.sin_port=htons(server_port);}
            server_length_=length;
            if(bind(fd_,reinterpret_cast<const sockaddr*>(&local),length)||getsockname(fd_,reinterpret_cast<sockaddr*>(&local),&length))throw std::runtime_error("gate bind failed");
            port_=port(local);thread_=std::thread([this]{run();});
        }catch(...){close(fd_);throw;}
    }
    ~ControlGate(){stop_=true;if(thread_.joinable())thread_.join();close(fd_);}
    std::uint16_t listen_port()const{return port_;}
};
