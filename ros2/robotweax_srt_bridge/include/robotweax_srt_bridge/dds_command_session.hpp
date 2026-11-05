#pragma once
#include <robotweax/srt_bridge/session.hpp>
#include <openssl/evp.h>
#include <algorithm>
#include <array>
#include <stdexcept>
namespace robotweax::ros_bridge {
namespace core=robotweax::srt_bridge;
inline core::Digest digest(std::span<const std::byte> bytes){core::Digest out{};unsigned size=0;if(EVP_Digest(bytes.data(),bytes.size(),reinterpret_cast<unsigned char*>(out.data()),&size,EVP_sha256(),nullptr)!=1||size!=out.size())throw std::runtime_error("DDS digest failed");return out;}
// Caller serializes these methods with the start-claim mutex. No journal or
// handler operation may hold that mutex. Epochs are transport leases, distinct
// from the durable journal's process owner epoch. Never trusts remote wall time.
class DdsCommandSession {
    bool sender_;
    core::Identity process_,link_,peer_process_{},peer_link_{},session_{};
    core::Digest clock_;
    std::array<core::Identity,64> retired_{};std::size_t retired_count_=0;
    std::uint64_t last_hello_=0,received_sequence_=0;
    bool acked_=false,failed_=false;
    void derive(){std::array<std::byte,32> input{};const auto& first=sender_?link_:peer_link_;const auto& second=sender_?peer_link_:link_;std::copy(first.begin(),first.end(),input.begin());std::copy(second.begin(),second.end(),input.begin()+16);const auto hash=digest(input);std::copy_n(hash.begin(),16,session_.begin());}
public:
    static constexpr std::uint64_t lease_ns=1500000000ULL;
    DdsCommandSession(bool sender,core::Identity process,core::Identity link,core::Digest clock):sender_(sender),process_(process),link_(link),clock_(clock){if(process==core::Identity{}||link==core::Identity{}||clock==core::Digest{})throw std::invalid_argument("DDS session identities required");}
    // Expiry changes our link nonce before any new start claim. Old reliable
    // traffic cannot revive the old session, even when both processes survive.
    void tick(std::uint64_t now,core::Identity replacement){if(last_hello_&&now>=last_hello_&&now-last_hello_>=lease_ns){if(replacement==core::Identity{}||replacement==link_){failed_=true;return;}link_=replacement;session_={};if(peer_link_!=core::Identity{})derive();acked_=false;last_hello_=0;}}
    bool hello(core::Identity process,core::Identity link,core::Identity target,core::Identity session,core::Digest clock,std::uint64_t sequence,std::uint64_t sent,std::uint64_t now){
        if(failed_||clock!=clock_||process==core::Identity{}||link==core::Identity{}||!sequence||!sent||sent>now||now-sent>=lease_ns||(target!=core::Identity{}&&target!=link_))return false;
        if(link!=peer_link_){
            if(std::find(retired_.begin(),retired_.begin()+retired_count_,link)!=retired_.begin()+retired_count_)return false;
            if(peer_link_!=core::Identity{}){if(retired_count_==retired_.size()){failed_=true;return false;}retired_[retired_count_++]=peer_link_;}
            peer_link_=link;peer_process_=process;received_sequence_=0;acked_=false;derive();
        }else if(process!=peer_process_)return false;
        if((target==link_&&session!=session_)||sequence<=received_sequence_)return false;
        received_sequence_=sequence;last_hello_=sent;
        if(target==link_&&session==session_)acked_=true;
        return true;
    }
    bool fresh(core::Identity session,std::uint64_t now)const{return !failed_&&acked_&&session!=core::Identity{}&&session==session_&&last_hello_&&now>=last_hello_&&now-last_hello_<lease_ns;}
    bool frame(core::Identity process,core::Identity link,core::Identity target,core::Identity session,core::Digest clock,std::uint64_t sequence,std::uint64_t sent,std::uint64_t now){
        if(!fresh(session,now)||process!=peer_process_||link!=peer_link_||target!=link_||clock!=clock_||!sequence||sequence<=received_sequence_||!sent||sent>now||now-sent>=lease_ns)return false;
        received_sequence_=sequence;return true;
    }
    core::Identity session()const{return session_;}core::Identity link()const{return link_;}core::Identity peer_link()const{return peer_link_;}core::Identity peer_process()const{return peer_process_;}core::Identity process()const{return process_;}core::Digest clock()const{return clock_;}bool failed()const{return failed_;}
};
}
