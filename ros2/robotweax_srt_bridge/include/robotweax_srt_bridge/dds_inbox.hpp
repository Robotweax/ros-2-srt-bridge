#pragma once
#include <array>
#include <mutex>
#include <utility>
namespace robotweax::ros_bridge {
// Fixed task storage. Local service admission can return BUSY on contention.
// Received Reliable frames serialize the short copy instead: a contended mutex
// is not a full queue and must not silently lose an already-delivered COMMAND.
// No journal, handler or transport operation runs while this mutex is held.
template<class T,std::size_t Capacity=64> class DdsInbox {
    std::mutex mutex_;std::array<T,Capacity> slots_{};std::size_t head_=0,count_=0;
    bool append(T value){if(count_==Capacity)return false;slots_[(head_+count_++)%Capacity]=std::move(value);return true;}
public:
    bool try_push(T value){std::unique_lock lock(mutex_,std::try_to_lock);return lock.owns_lock()&&append(std::move(value));}
    bool receive(T value){std::lock_guard lock(mutex_);return append(std::move(value));}
    bool pop(T& value){std::lock_guard lock(mutex_);if(!count_)return false;value=std::move(slots_[head_]);slots_[head_]={};head_=(head_+1)%Capacity;--count_;return true;}
};
}
