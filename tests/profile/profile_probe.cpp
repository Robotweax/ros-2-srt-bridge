// Installed public C API qualification. Test credentials are generated per process.
#include <srt/srt.h>
#include <arpa/inet.h>
#include <algorithm>
#include <array>
#include <chrono>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <thread>
#include <vector>

namespace {
using Clock = std::chrono::steady_clock;
using namespace std::chrono_literals;
void require(bool ok, const std::string& message) {
    if (!ok) throw std::runtime_error(message);
}
void checked(int result, const char* operation) {
    if (result == SRT_ERROR) throw std::runtime_error(std::string(operation) + ": " + srt_getlasterror_str());
}
template<class T> void set(SRTSOCKET s, SRT_SOCKOPT option, T value) {
    checked(srt_setsockflag(s, option, &value, sizeof(value)), "setsockflag");
}
template<class T> T get(SRTSOCKET s, SRT_SOCKOPT option) {
    T value{}; int size = sizeof(value);
    checked(srt_getsockflag(s, option, &value, &size), "getsockflag");
    require(size == sizeof(value), "option size mismatch");
    return value;
}
struct Runtime {
    Runtime() { checked(srt_startup(), "startup"); }
    ~Runtime() { srt_cleanup(); }
};
struct Socket {
    SRTSOCKET fd = SRT_INVALID_SOCK;
    explicit Socket(SRTSOCKET value) : fd(value) { require(fd != SRT_INVALID_SOCK, "invalid socket"); }
    Socket() : Socket(srt_create_socket()) {}
    Socket(const Socket&) = delete;
    Socket& operator=(const Socket&) = delete;
    ~Socket() { if (fd != SRT_INVALID_SOCK) srt_close(fd); }
    void close() { checked(srt_close(fd), "close"); fd = SRT_INVALID_SOCK; }
};
struct Poll {
    int id = srt_epoll_create();
    Poll() { require(id >= 0, "epoll_create"); }
    Poll(const Poll&) = delete;
    Poll& operator=(const Poll&) = delete;
    ~Poll() { srt_epoll_release(id); }
    int wait(SRTSOCKET s, int events, int timeout) {
        events |= SRT_EPOLL_ERR;
        checked(srt_epoll_add_usock(id, s, &events), "epoll_add");
        SRT_EPOLL_EVENT ready{};
        const int count = srt_epoll_uwait(id, &ready, 1, timeout);
        checked(srt_epoll_remove_usock(id, s), "epoll_remove");
        checked(count, "epoll_wait");
        require(count == 0 || (count == 1 && ready.fd == s), "unexpected epoll descriptor");
        return count == 0 ? 0 : ready.events;
    }
};
std::string random_secret() {
    std::array<unsigned char, 32> bytes{};
    std::ifstream random("/dev/urandom", std::ios::binary);
    random.read(reinterpret_cast<char*>(bytes.data()), bytes.size());
    require(bool(random), "random source unavailable");
    constexpr char hex[] = "0123456789abcdef";
    std::string result;
    for (auto b : bytes) { result += hex[b >> 4]; result += hex[b & 15]; }
    return result;
}
struct Settings {
    SRT_TRANSTYPE profile;
    bool gcm = true;
    bool auth = true;
    bool secret = true;
};
void configure(SRTSOCKET s, const Settings& settings, int mss, const std::string& secret) {
    set(s, SRTO_TRANSTYPE, settings.profile);
    set(s, SRTO_MSS, mss);
    set(s, SRTO_ENFORCEDENCRYPTION, true);
    set(s, SRTO_CRYPTOMODE, std::int32_t(settings.gcm ? 2 : 1));
    set(s, SRTO_PBKEYLEN, 32);
    set(s, SRTO_ROBOTWEAX_SESSIONAUTH, settings.auth);
    if (settings.secret) checked(srt_setsockflag(s, SRTO_PASSPHRASE,
        secret.data(), static_cast<int>(secret.size())), "set secret");
    set(s, SRTO_PAYLOADSIZE, 1024);
    set(s, SRTO_FC, 256);
    set(s, SRTO_SNDBUF, 256 * 1024);
    set(s, SRTO_RCVBUF, 256 * 1024);
    set(s, SRTO_UDP_SNDBUF, 256 * 1024);
    set(s, SRTO_UDP_RCVBUF, 256 * 1024);
    set(s, SRTO_CONNTIMEO, 1000);
    set(s, SRTO_SNDSYN, false);
    set(s, SRTO_RCVSYN, false);
    set(s, SRTO_LINGER, linger{0, 0});
}
void negotiated(SRTSOCKET s, SRT_TRANSTYPE profile) {
    require(get<SRT_TRANSTYPE>(s, SRTO_TRANSTYPE) == profile, "profile downgrade");
    require(get<std::int32_t>(s, SRTO_CRYPTOMODE) == 2, "GCM downgrade");
    require(get<bool>(s, SRTO_ROBOTWEAX_SESSIONAUTH), "sessionauth downgrade");
    require(get<bool>(s, SRTO_ENFORCEDENCRYPTION), "encryption downgrade");
    require(!get<bool>(s, SRTO_TSBPDMODE) && !get<bool>(s, SRTO_TLPKTDROP), "unexpected timing profile");
    require(!get<bool>(s, SRTO_SNDSYN) && !get<bool>(s, SRTO_RCVSYN), "blocking I/O");
    require(get<int>(s, SRTO_PAYLOADSIZE) == 1024, "payload size changed");
    const auto linger_value = get<linger>(s, SRTO_LINGER);
    require(linger_value.l_onoff == 0 && linger_value.l_linger == 0, "unbounded linger");
    if (profile == SRTT_SENSOR) {
        std::array<char, 512> filter{}; int n = filter.size();
        checked(srt_getsockflag(s, SRTO_PACKETFILTER, filter.data(), &n), "get filter");
        require(std::string(filter.data()) == "fec-sensor-v1,cols:4,rows:1,arq:never", "FEC contract changed");
    }
    const auto deadline = Clock::now() + 2s;
    while (get<int>(s, SRTO_SNDKMSTATE) != SRT_KM_S_SECURED ||
           get<int>(s, SRTO_RCVKMSTATE) != SRT_KM_S_SECURED) {
        require(Clock::now() < deadline, "key confirmation not secured before DATA");
        std::this_thread::sleep_for(1ms);
    }
}
void empty_receive(SRTSOCKET s) {
    std::array<char, 4096> buffer{};
    require(srt_recvmsg(s, buffer.data(), buffer.size()) == SRT_ERROR, "unexpected data");
    require(srt_getlasterror(nullptr) == SRT_EASYNCRCV, "empty receive did not report EASYNCRCV");
}
void transfer(Poll& poll, SRTSOCKET sender, SRTSOCKET receiver, int size, bool sensor, int iteration) {
    std::vector<char> payload(size);
    for (int i = 0; i < size; ++i) payload[i] = static_cast<char>((i * 37 + iteration) & 255);
    const auto deadline = Clock::now() + 2s;
    SRT_MSGCTRL control = srt_msgctrl_default;
    control.msgttl = sensor ? 250 : -1;
    control.inorder = 0;
    for (;;) {
        const int sent = srt_sendmsg2(sender, payload.data(), size, &control);
        if (sent != SRT_ERROR) { require(sent == size, "partial message send"); break; }
        require(srt_getlasterror(nullptr) == SRT_EASYNCSND, "unexpected send failure");
        require(Clock::now() < deadline, "send deadline");
        require(!(poll.wait(sender, SRT_EPOLL_OUT, 100) & SRT_EPOLL_ERR), "send epoll error");
    }
    std::array<char, 4096> received{};
    for (;;) {
        const int count = srt_recvmsg(receiver, received.data(), received.size());
        if (count != SRT_ERROR) {
            require(count == size && std::equal(payload.begin(), payload.end(), received.begin()), "payload mismatch");
            break;
        }
        require(srt_getlasterror(nullptr) == SRT_EASYNCRCV, "unexpected receive failure");
        require(Clock::now() < deadline, "receive deadline");
        require(!(poll.wait(receiver, SRT_EPOLL_IN, 100) & SRT_EPOLL_ERR), "receive epoll error");
    }
}
void probe(const std::string& profile_name, const std::string& family, const std::string& scenario, bool reverse) {
    const bool sensor = profile_name == "sensor";
    const auto profile = sensor ? SRTT_SENSOR : SRTT_CONTROL;
    Settings listener_settings{profile}, caller_settings{profile};
    auto& changed = reverse ? listener_settings : caller_settings;
    if (scenario == "wrong-profile") changed.profile = sensor ? SRTT_CONTROL : SRTT_SENSOR;
    else if (scenario == "missing-gcm") changed.gcm = false;
    else if (scenario == "missing-sessionauth") changed.auth = false;
    else if (scenario == "missing-secret") changed.secret = false;
    else require(scenario == "positive" || scenario == "backpressure" || scenario == "wrong-secret", "unknown scenario");
    auto secret = random_secret();
    const auto other_secret = scenario == "wrong-secret" ? random_secret() : secret;
    Runtime runtime;
    Socket listener, caller;
    Poll poll;
    const bool ipv6 = family == "ipv6";
    configure(listener.fd, listener_settings, ipv6 ? 1280 : 1500, secret);
    configure(caller.fd, caller_settings, ipv6 ? 1280 : 1500, other_secret);
    sockaddr_storage address{}; int address_size;
    if (ipv6) {
        auto& a = reinterpret_cast<sockaddr_in6&>(address);
        a.sin6_family = AF_INET6; a.sin6_addr = in6addr_loopback; address_size = sizeof(a);
        set(listener.fd, SRTO_IPV6ONLY, 1);
        set(caller.fd, SRTO_IPV6ONLY, 1);
    } else {
        auto& a = reinterpret_cast<sockaddr_in&>(address);
        a.sin_family = AF_INET; a.sin_addr.s_addr = htonl(INADDR_LOOPBACK); address_size = sizeof(a);
    }
    checked(srt_bind(listener.fd, reinterpret_cast<sockaddr*>(&address), address_size), "bind");
    checked(srt_getsockname(listener.fd, reinterpret_cast<sockaddr*>(&address), &address_size), "getsockname");
    checked(srt_listen(listener.fd, 4), "listen");
    const int connected = srt_connect(caller.fd, reinterpret_cast<sockaddr*>(&address), address_size);
    const bool positive = scenario == "positive" || scenario == "backpressure";
    if (!positive) {
        int events = 0;
        if (connected != SRT_ERROR) {
            events = poll.wait(caller.fd, SRT_EPOLL_OUT, 2500);
            require(events & SRT_EPOLL_ERR, "mismatch did not produce epoll error");
            require(srt_getsockstate(caller.fd) == SRTS_BROKEN, "mismatched caller not broken");
            require(srt_getrejectreason(caller.fd) != 0, "missing rejection reason");
        } else {
            require(scenario == "missing-secret", "unexpected local connect error");
        }
        require(!(poll.wait(listener.fd, SRT_EPOLL_IN, 20) & SRT_EPOLL_IN), "mismatched peer was accepted");
        const auto child = srt_accept(listener.fd, nullptr, nullptr);
        if (child != SRT_INVALID_SOCK) { srt_close(child); throw std::runtime_error("negative case accepted"); }
        require(srt_getlasterror(nullptr) == SRT_EASYNCRCV, "negative accept error");
        std::cout << "rejection_reason=" << srt_getrejectreason(caller.fd) << " events=" << events << '\n';
    } else {
        checked(connected, "connect");
        const int ready = poll.wait(caller.fd, SRT_EPOLL_OUT, 2500);
        require((ready & SRT_EPOLL_OUT) && !(ready & SRT_EPOLL_ERR), "connect readiness failed");
        require(poll.wait(listener.fd, SRT_EPOLL_IN, 2500) & SRT_EPOLL_IN, "accept deadline");
        Socket accepted(srt_accept(listener.fd, nullptr, nullptr));
        negotiated(caller.fd, profile); negotiated(accepted.fd, profile);
        empty_receive(accepted.fd);
        require(poll.wait(accepted.fd, SRT_EPOLL_IN, 10) == 0, "empty epoll did not time out");
        if (sensor) {
            std::array<char, 1025> too_big{};
            require(srt_sendmsg(caller.fd, too_big.data(), too_big.size(), 250, 0) == SRT_ERROR, "oversize sensor accepted");
            require(srt_getlasterror(nullptr) == SRT_EINVOP, "unexpected sensor oversize error");
        } else {
            const char data = 'x';
            require(srt_sendmsg(caller.fd, &data, 1, 250, 0) == SRT_ERROR, "finite CONTROL TTL accepted");
            require(srt_getlasterror(nullptr) == SRT_EINVALMSGAPI, "unexpected control TTL error");
        }
        for (int i = 0; i < 8; ++i) {
            transfer(poll, caller.fd, accepted.fd, sensor ? 1024 : 4096, sensor, i);
            transfer(poll, accepted.fd, caller.fd, sensor ? 1024 : 4096, sensor, i + 8);
        }
        empty_receive(accepted.fd);
        if (scenario == "backpressure") {
            std::vector<char> pending(sensor ? 1024 : 4096, 'q');
            bool full = false;
            for (int i = 0; i < 1024; ++i) {
                const int sent = srt_sendmsg(caller.fd, pending.data(), pending.size(), -1, 0);
                if (sent == SRT_ERROR) {
                    require(srt_getlasterror(nullptr) == SRT_EASYNCSND, "unexpected pressure error");
                    full = true; break;
                }
                require(sent == static_cast<int>(pending.size()), "partial pressure send");
            }
            require(full, "did not reach bounded send buffer");
        }
        std::cout << "mss=" << get<int>(caller.fd, SRTO_MSS)
                  << " srt_sndbuf=" << get<int>(caller.fd, SRTO_SNDBUF)
                  << " srt_rcvbuf=" << get<int>(caller.fd, SRTO_RCVBUF)
                  << " udp_sndbuf=" << get<int>(caller.fd, SRTO_UDP_SNDBUF)
                  << " udp_rcvbuf=" << get<int>(caller.fd, SRTO_UDP_RCVBUF)
                  << " flow_window=" << get<int>(caller.fd, SRTO_FC) << '\n';
        const auto start = Clock::now();
        caller.close(); accepted.close(); listener.close();
        require(Clock::now() - start < 2s, "socket close exceeded budget");
        std::cout << "bytes_per_message=" << (sensor ? 1024 : 4096) << " messages=16 crypto=gcm sessionauth=on close_ms="
                  << std::chrono::duration_cast<std::chrono::milliseconds>(Clock::now()-start).count() << '\n';
    }
}
}
int main(int argc, char** argv) {
    try {
        require(argc == 4 || argc == 5, "usage: profile_probe control|sensor ipv4|ipv6 CASE [reverse]");
        require(std::string(argv[1]) == "control" || std::string(argv[1]) == "sensor", "invalid profile");
        require(std::string(argv[2]) == "ipv4" || std::string(argv[2]) == "ipv6", "invalid address family");
        require(argc != 5 || std::string(argv[4]) == "reverse", "invalid direction");
        probe(argv[1], argv[2], argv[3], argc == 5);
        std::cout << "PASS " << argv[1] << ' ' << argv[2] << ' ' << argv[3] << (argc == 5 ? " reverse" : "") << '\n';
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "FAIL: " << error.what() << '\n'; return 1;
    }
}
