#include "execution_pool.hpp"
#include <limits>
#include <algorithm>
#include <stdexcept>
#include <sys/mman.h>
#include <sys/stat.h>
#include <unistd.h>
#ifdef __linux__
#include <sys/mman.h>
#include <fcntl.h>
#endif
namespace robotweax::srt_bridge::execution_detail {
namespace {
constexpr std::uint64_t magic=0x5257455845433031ULL,mask=7,max_generation=UINT64_MAX>>3;
struct alignas(64) Slot {
    alignas(std::atomic_ref<std::uint64_t>::required_alignment) std::uint64_t word=0;
    std::uint64_t deadline=0;
    Identity id{};Digest hash{};
};
std::uint64_t word(std::uint64_t generation,State state){return (generation<<3)|unsigned(state);}
std::atomic_ref<std::uint64_t> atomic(Slot& slot){return std::atomic_ref(slot.word);}
void revoke_slot(Slot& slot){auto value=atomic(slot).load(std::memory_order_acquire);while((value&mask)==unsigned(State::prepared)||(value&mask)==unsigned(State::granted)){
    if(atomic(slot).compare_exchange_weak(value,(value&~mask)|unsigned(State::revoked),std::memory_order_acq_rel))break;}}
}
struct Pool::Mapping {std::uint64_t magic=execution_detail::magic,version=1;std::array<Slot,64> slots{};};
std::shared_ptr<Pool> Pool::create(){
#ifndef __linux__
    throw std::runtime_error("execution pool requires qualified Linux memfd atomics");
#else
    static_assert(std::atomic_ref<std::uint64_t>::is_always_lock_free);
    auto pool=std::shared_ptr<Pool>(new Pool);
    pool->fd_=memfd_create("robotweax-execution",MFD_CLOEXEC|MFD_ALLOW_SEALING);
    if(pool->fd_<0||ftruncate(pool->fd_,sizeof(Mapping)))throw std::runtime_error("execution memfd allocation failed");
    void* memory=mmap(nullptr,sizeof(Mapping),PROT_READ|PROT_WRITE,MAP_SHARED,pool->fd_,0);
    if(memory==MAP_FAILED)throw std::runtime_error("execution mapping failed");
    pool->mapping_=new(memory) Mapping;
    if(fcntl(pool->fd_,F_ADD_SEALS,F_SEAL_GROW|F_SEAL_SHRINK|F_SEAL_SEAL)<0)throw std::runtime_error("execution sealing failed");
    return pool;
#endif
}
std::shared_ptr<Pool> Pool::map(int fd){
#ifndef __linux__
    (void)fd;throw std::runtime_error("execution mapping unsupported");
#else
    static_assert(std::atomic_ref<std::uint64_t>::is_always_lock_free);
    struct stat st{};constexpr int required=F_SEAL_GROW|F_SEAL_SHRINK|F_SEAL_SEAL;
    const auto seals=fcntl(fd,F_GET_SEALS);
    if(fstat(fd,&st)||st.st_size!=sizeof(Mapping)||seals<0||(seals&required)!=required)throw std::runtime_error("invalid execution descriptor");
    auto pool=std::shared_ptr<Pool>(new Pool);
    void* memory=mmap(nullptr,sizeof(Mapping),PROT_READ|PROT_WRITE,MAP_SHARED,fd,0);
    if(memory==MAP_FAILED)throw std::runtime_error("execution remap failed");
    pool->mapping_=static_cast<Mapping*>(memory);
    if(pool->mapping_->magic!=magic||pool->mapping_->version!=1)throw std::runtime_error("invalid execution mapping header");
    return pool;
#endif
}
Pool::~Pool(){if(mapping_)munmap(mapping_,sizeof(Mapping));if(fd_>=0)close(fd_);}
Record::~Record(){if(pool&&slot!=UINT32_MAX)pool->release(*this);}
std::shared_ptr<Record> Pool::allocate(const JournalEntry& entry,std::string local,std::string remote,std::shared_ptr<std::atomic<bool>> live){
    auto record=std::make_shared<Record>();record->entry=entry;record->local_peer=std::move(local);record->remote_peer=std::move(remote);record->live=std::move(live);record->pool=shared_from_this();
    for(std::size_t i=0;i<mapping_->slots.size();++i){auto& slot=mapping_->slots[i];const auto old=atomic(slot).load(std::memory_order_acquire);
        if((old&mask)!=unsigned(State::free)||(old>>3)==max_generation)continue;
        record->slot=i;record->generation=(old>>3)+1;slot.id=entry.request_id;slot.hash=entry.payload_hash;slot.deadline=entry.context.deadline_ns;
        atomic(slot).store(word(record->generation,State::prepared),std::memory_order_release);return record;
    }
    return {};
}
bool Pool::grant(const Record& record,std::uint64_t deadline)noexcept{
    if(!record.live->load()||record.slot>=64)return false;
    auto& slot=mapping_->slots[record.slot];auto expected=word(record.generation,State::prepared);
    if(atomic(slot).load(std::memory_order_acquire)!=expected)return false;
    slot.deadline=std::min(deadline,record.entry.context.deadline_ns);
    return atomic(slot).compare_exchange_strong(expected,word(record.generation,State::granted),std::memory_order_acq_rel);
}
void Pool::revoke(const Record& record)noexcept{if(record.slot<64){auto& slot=mapping_->slots[record.slot];const auto value=atomic(slot).load(std::memory_order_acquire);if((value>>3)==record.generation)revoke_slot(slot);}}
void Pool::revoke_all()noexcept{for(auto& slot:mapping_->slots)revoke_slot(slot);}
State Pool::state(const Record& record)const noexcept{if(record.slot>=64)return State::revoked;const auto value=atomic(mapping_->slots[record.slot]).load(std::memory_order_acquire);return (value>>3)==record.generation?State(value&mask):State::revoked;}
std::uint64_t Pool::deadline(const Record& record)const noexcept{return deadline(record.slot,record.generation);}
std::uint64_t Pool::deadline(std::uint32_t slot,std::uint64_t generation)const noexcept{
    if(slot>=64)return 0;
    const auto current=atomic(mapping_->slots[slot]).load(std::memory_order_acquire);
    return (current>>3)==generation?mapping_->slots[slot].deadline:0;
}
Start Pool::consume(std::uint32_t i,std::uint64_t generation,Identity id,Digest hash,std::uint64_t now)noexcept{
    if(i>=64||!generation)return Start::invalid;
    auto& slot=mapping_->slots[i];auto expected=word(generation,State::granted);
    const auto current=atomic(slot).load(std::memory_order_acquire);
    if(current!=expected)return (current>>3)==generation&&(current&mask)==unsigned(State::revoked)?Start::revoked:Start::invalid;
    if(slot.id!=id||slot.hash!=hash)return Start::invalid;
    if(now>=slot.deadline)return Start::expired;
    return atomic(slot).compare_exchange_strong(expected,word(generation,State::running),std::memory_order_acq_rel)?Start::started:Start::revoked;
}
void Pool::complete(std::uint32_t i,std::uint64_t generation)noexcept{if(i>=64)return;auto expected=word(generation,State::running);atomic(mapping_->slots[i]).compare_exchange_strong(expected,word(generation,State::finished),std::memory_order_acq_rel);}
void Pool::release(const Record& record)noexcept{
    if(record.slot>=64)return;
    auto& slot=mapping_->slots[record.slot];revoke(record);auto current=atomic(slot).load(std::memory_order_acquire);
    // A process failure may leave RUNNING behind. Never recycle it until the
    // entire failed pool is destroyed; this also prevents ABA with a late child.
    if((current>>3)==record.generation&&(current&mask)!=unsigned(State::running))atomic(slot).store(word(record.generation,State::free),std::memory_order_release);
}
}
