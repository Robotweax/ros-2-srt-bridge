#pragma once
#include <robotweax/srt_bridge/worker.hpp>
#include <algorithm>
#include <stdexcept>
#include <limits>
namespace robotweax::srt_bridge::worker_ipc {
constexpr std::size_t frame_bytes=2048;
constexpr std::uint16_t protocol_version=4;
constexpr std::uint16_t initialize=100,ready=101,stop=102,paused=103;
using Frame=std::array<std::byte,frame_bytes>;
struct Writer {
    Frame bytes{};std::size_t position=20;
    void number(std::uint64_t value,unsigned width){if(position+width>bytes.size())throw std::runtime_error("IPC size");for(unsigned i=0;i<width;++i)bytes[position++]=std::byte(value>>(8*(width-i-1)));}
    template<std::size_t N> void raw(const std::array<std::byte,N>& value){for(auto b:value)number(std::to_integer<unsigned>(b),1);}
    void string(const std::string& value,std::size_t limit){if(value.size()>limit||value.find('\0')!=std::string::npos)throw std::invalid_argument("IPC string");number(value.size(),2);for(unsigned char b:value)number(b,1);}
    Frame finish(std::uint16_t operation,std::uint64_t token){const auto length=position-20;position=0;number(0x52575031,4);number(protocol_version,2);number(operation,2);number(token,8);number(length,4);return bytes;}
};
struct Reader {
    const Frame& bytes;std::size_t position=0,end=frame_bytes;
    std::uint16_t operation=0;std::uint64_t token=0;
    std::uint64_t number(unsigned width){if(position+width>end)throw std::runtime_error("truncated IPC");std::uint64_t value=0;for(unsigned i=0;i<width;++i)value=(value<<8)|std::to_integer<unsigned>(bytes[position++]);return value;}
    explicit Reader(const Frame& frame):bytes(frame){if(number(4)!=0x52575031||number(2)!=protocol_version)throw std::runtime_error("IPC header");operation=number(2);token=number(8);const auto length=number(4);if(length>frame_bytes-20)throw std::runtime_error("IPC length");end=20+length;for(std::size_t i=end;i<bytes.size();++i)if(bytes[i]!=std::byte{})throw std::runtime_error("IPC padding");}
    template<std::size_t N> void raw(std::array<std::byte,N>& value){for(auto& b:value)b=std::byte(number(1));}
    bool boolean(){auto value=number(1);if(value>1)throw std::runtime_error("IPC boolean");return value;}
    std::string string(std::size_t limit){const auto length=number(2);if(length>limit)throw std::runtime_error("IPC string");std::string value;for(std::size_t i=0;i<length;++i){auto b=number(1);if(!b)throw std::runtime_error("IPC NUL");value+=char(b);}return value;}
    void done(){if(position!=end)throw std::runtime_error("IPC trailing fields");}
};
inline void command(Writer& w,const RateCommand& c){w.number(c.rate_hz,4);w.number(c.budget_ms,4);w.number(c.expected_generation,8);w.number(c.new_generation,8);}
inline RateCommand command(Reader& r){RateCommand c;c.rate_hz=r.number(4);c.budget_ms=r.number(4);c.expected_generation=r.number(8);c.new_generation=r.number(8);return c;}
inline void context(Writer& w,const CommandContext& c){w.raw(c.session);w.raw(c.source_epoch);w.number(c.source_monotonic_ns,8);w.number(c.deadline_ns,8);}
inline CommandContext context(Reader& r){CommandContext c;r.raw(c.session);r.raw(c.source_epoch);c.source_monotonic_ns=r.number(8);c.deadline_ns=r.number(8);return c;}
inline void result(Writer& w,const RateResult& c){w.number(c.rate_hz,4);w.number(c.generation,8);w.number(c.valid,1);}
inline RateResult result(Reader& r){RateResult c;c.rate_hz=r.number(4);c.generation=r.number(8);c.valid=r.boolean();return c;}
inline void status(Writer& w,const CommandStatus& c){w.number(unsigned(c.state),1);w.number(unsigned(c.reason),1);command(w,c.command);w.raw(c.payload_hash);result(w,c.result);w.number(c.revision,8);}
inline CommandStatus status(Reader& r){CommandStatus c;c.state=CommandState(r.number(1));c.reason=CommandReason(r.number(1));c.command=command(r);r.raw(c.payload_hash);c.result=result(r);c.revision=r.number(8);return c;}
inline Frame encode(const WorkerRequest& q,std::uint64_t token){Writer w;w.raw(q.request_id);w.raw(q.session);w.number(q.route,4);command(w,q.command);context(w,q.context);status(w,q.remote_status);w.number(unsigned(q.state),1);w.number(unsigned(q.reason),1);result(w,q.result);w.number(q.clock_qualified,1);w.number(q.grant_slot,4);w.number(q.grant_generation,8);return w.finish(unsigned(q.operation),token);}
inline WorkerRequest request(Reader& r){if(r.operation<1||r.operation>11||!r.token)throw std::runtime_error("IPC request operation");WorkerRequest q;q.operation=WorkerOperation(r.operation);r.raw(q.request_id);r.raw(q.session);q.route=r.number(4);q.command=command(r);q.context=context(r);q.remote_status=status(r);q.state=CommandState(r.number(1));q.reason=CommandReason(r.number(1));q.result=result(r);q.clock_qualified=r.boolean();q.grant_slot=r.number(4);q.grant_generation=r.number(8);r.done();return q;}
inline void entry(Writer& w,const JournalEntry& e){w.raw(e.request_id);w.raw(e.owner_epoch);w.number(e.route,4);command(w,e.command);context(w,e.context);w.raw(e.payload_hash);w.number(unsigned(e.state),1);w.number(unsigned(e.reason),1);result(w,e.result);w.number(e.admitted_ns,8);w.number(e.dispatched_ns,8);w.number(e.finished_ns,8);w.number(e.revision,8);}
inline JournalEntry entry(Reader& r){JournalEntry e;r.raw(e.request_id);r.raw(e.owner_epoch);e.route=r.number(4);e.command=command(r);e.context=context(r);r.raw(e.payload_hash);e.state=CommandState(r.number(1));e.reason=CommandReason(r.number(1));e.result=result(r);e.admitted_ns=r.number(8);e.dispatched_ns=r.number(8);e.finished_ns=r.number(8);e.revision=r.number(8);return e;}
inline Frame encode_reply(std::uint16_t op,std::uint64_t token,const JournalResult& result,bool may_transmit=false,RateResult device={},std::uint64_t effects=0){Writer w;w.number(unsigned(result.error),1);w.number(result.inserted,1);w.number(may_transmit,1);w.number(result.entry.has_value(),1);if(result.entry)entry(w,*result.entry);worker_ipc::result(w,device);w.number(effects,8);return w.finish(op,token);}
inline WorkerReply reply(Reader& r){WorkerReply q;q.token=r.token;q.operation=WorkerOperation(r.operation);const auto error=r.number(1);if(error>unsigned(JournalError::corrupt))throw std::runtime_error("IPC journal error");q.journal.error=JournalError(error);q.journal.inserted=r.boolean();q.may_transmit=r.boolean();if(r.boolean())q.journal.entry=entry(r);q.device=result(r);q.effects=r.number(8);r.done();return q;}
inline Frame initialize_frame(const WorkerOptions& o){Writer w;const auto& j=o.journal;w.string(j.path,1024);w.string(j.local_peer_id,64);w.string(j.remote_peer_id,64);w.number(unsigned(j.side),1);w.raw(j.process_epoch);w.number(j.max_entries,4);w.number(j.max_bytes,8);w.number(j.wal_bytes,8);w.number(o.simulated_rate_handler,1);w.number(o.external_rate_handler,1);w.number(o.test_handler_pause,1);w.number(o.test_pause_at?unsigned(*o.test_pause_at)+1:0,1);w.number(o.test_faults.has_value(),1);if(o.test_faults){w.number(std::uint32_t(o.test_faults->writes_before_failure),4);w.number(std::uint32_t(o.test_faults->syncs_before_failure),4);w.number(o.test_faults->full,1);}return w.finish(initialize,0);}
inline WorkerOptions options(Reader& r){if(r.operation!=initialize||r.token)throw std::runtime_error("IPC initialization");WorkerOptions o;auto& j=o.journal;j.path=r.string(1024);j.local_peer_id=r.string(64);j.remote_peer_id=r.string(64);j.side=JournalSide(r.number(1));r.raw(j.process_epoch);j.max_entries=r.number(4);j.max_bytes=r.number(8);j.wal_bytes=r.number(8);o.simulated_rate_handler=r.boolean();o.external_rate_handler=r.boolean();o.test_handler_pause=r.number(1);if(o.test_handler_pause>3)throw std::runtime_error("IPC handler barrier");const auto pause=r.number(1);if(pause>5)throw std::runtime_error("IPC test barrier");if(pause)o.test_pause_at=JournalPoint(pause-1);if(r.boolean()){JournalFaults f;const auto writes=r.number(4),syncs=r.number(4);if((writes>std::numeric_limits<int>::max()&&writes!=UINT32_MAX)||(syncs>std::numeric_limits<int>::max()&&syncs!=UINT32_MAX))throw std::runtime_error("IPC fault count");f.writes_before_failure=writes==UINT32_MAX?-1:int(writes);f.syncs_before_failure=syncs==UINT32_MAX?-1:int(syncs);f.full=r.boolean();o.test_faults=f;}r.done();return o;}
}
