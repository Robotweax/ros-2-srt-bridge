#pragma once
#include <robotweax/srt_bridge/command_trace.hpp>
#include <ostream>
namespace robotweax::srt_bridge {
inline void append_sender_trace_json(std::ostream& out,const CommandTraceEvent& e){
    if(unsigned(e.point)<45||unsigned(e.point)>48)return;
    out<<",\"sender_trace_version\":1,\"command_deadline_ns\":"<<e.command_deadline_ns
       <<",\"clock_previous_deadline_ns\":"<<e.clock_previous_deadline_ns<<",\"probe_anchor_ns\":"<<e.probe_anchor_ns
       <<",\"clock_observed\":"<<(e.clock_observed?"true":"false")
       <<",\"offset_lower_ns\":"<<e.offset_lower_ns<<",\"offset_upper_ns\":"<<e.offset_upper_ns
       <<",\"worker_token\":"<<e.worker_token<<",\"journal_entry_available\":"<<(e.journal_entry_available?"true":"false")
       <<",\"journal_revision\":"<<e.journal_revision<<",\"terminal_state\":"<<e.terminal_state<<",\"terminal_reason\":"<<e.terminal_reason;
}
}
