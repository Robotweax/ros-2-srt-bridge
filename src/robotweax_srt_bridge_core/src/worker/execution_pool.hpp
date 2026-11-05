#pragma once
#include <robotweax/srt_bridge/execution.hpp>
#include <atomic>
#include <array>
namespace robotweax::srt_bridge::execution_detail {
enum class State : std::uint64_t { free,prepared,granted,running,revoked,finished };
enum class Start { started,expired,revoked,invalid };
class Pool;
struct Record {
    JournalEntry entry;
    std::string local_peer,remote_peer;
    std::shared_ptr<std::atomic<bool>> live;
    std::shared_ptr<Pool> pool;
    std::uint32_t slot=UINT32_MAX;
    std::uint64_t generation=0;
    std::atomic<bool> requested{false},submitted{false};
    ~Record();
};
// Linux shared memfd, fixed 64 slots. Cross-process 64-bit atomics must be
// lock-free on the qualified platform; no emulated/process-private mutexes.
class Pool : public std::enable_shared_from_this<Pool> {
public:
    static std::shared_ptr<Pool> create();
    static std::shared_ptr<Pool> map(int fd);
    ~Pool();
    int fd()const noexcept{return fd_;}
    std::shared_ptr<Record> allocate(const JournalEntry& entry,std::string local,std::string remote,std::shared_ptr<std::atomic<bool>> live);
    bool grant(const Record& record,std::uint64_t deadline)noexcept;
    void revoke(const Record& record)noexcept;
    void revoke_all()noexcept;
    State state(const Record& record)const noexcept;
    std::uint64_t deadline(const Record& record)const noexcept;
    std::uint64_t deadline(std::uint32_t slot,std::uint64_t generation)const noexcept;
    Start consume(std::uint32_t slot,std::uint64_t generation,Identity id,Digest hash,std::uint64_t now)noexcept;
    void complete(std::uint32_t slot,std::uint64_t generation)noexcept;
    void release(const Record& record)noexcept;
private:
    Pool()=default;
    struct Mapping;
    int fd_=-1;
    Mapping* mapping_=nullptr;
};
}
