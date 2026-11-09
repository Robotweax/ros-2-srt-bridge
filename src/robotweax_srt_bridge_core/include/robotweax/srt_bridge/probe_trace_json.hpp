#pragma once
#include <robotweax/srt_bridge/command_trace.hpp>
#include <ostream>
namespace robotweax::srt_bridge {
inline void append_probe_trace_json(std::ostream& out,const CommandTraceEvent& e){
    if(unsigned(e.point)<50||unsigned(e.point)>54)return;
    out<<",\"probe_trace_version\":1,\"probe_t1\":"<<e.probe_t1<<",\"probe_t2\":"<<e.probe_t2<<",\"probe_t3\":"<<e.probe_t3
       <<",\"probe_pending_before\":"<<e.probe_pending_before<<",\"probe_pending_after\":"<<e.probe_pending_after<<",\"probe_end_ns\":"<<e.probe_end_ns
       <<",\"probe_fields_available\":"<<(e.probe_fields_available?"true":"false")<<",\"probe_mapper_submitted\":"<<(e.probe_mapper_submitted?"true":"false")
       <<",\"probe_sdk_bytes\":"<<e.probe_sdk_bytes<<",\"probe_message_bytes\":"<<e.probe_message_bytes
       <<",\"clock_observed\":"<<(e.clock_observed?"true":"false")<<",\"probe_anchor_ns\":"<<e.probe_anchor_ns
       <<",\"offset_lower_ns\":"<<e.offset_lower_ns<<",\"offset_upper_ns\":"<<e.offset_upper_ns;
}
}
