#pragma once
#include <robotweax/srt_bridge/command_trace.hpp>
#include <ostream>
namespace robotweax::srt_bridge {
// Diagnostic JSON suffix only; never sent on SRT, ROS CDR or worker socket IPC.
inline void append_start_trace_json(std::ostream& out,const CommandTraceEvent& e){
    if(unsigned(e.point)<40||unsigned(e.point)>44)return;
    out<<",\"start_trace_version\":1,\"check_token\":"<<e.check_token<<",\"worker_token\":"<<e.worker_token
        <<",\"grant_slot\":"<<e.grant_slot<<",\"grant_generation\":"<<e.grant_generation<<",\"grant_deadline_ns\":"<<e.grant_deadline_ns
        <<",\"command_deadline_ns\":"<<e.command_deadline_ns
        <<",\"start_granted\":"<<(e.start_granted?"true":"false")<<",\"worker_observation_available\":"<<(e.worker_observation_available?"true":"false")
        <<",\"consume_ns\":"<<e.consume_ns<<",\"consume_deadline_ns\":"<<e.consume_deadline_ns<<",\"consume_result\":"<<e.consume_result
        <<",\"second_gate_ns\":"<<e.second_gate_ns<<",\"second_gate_deadline_ns\":"<<e.second_gate_deadline_ns
        <<",\"second_gate_checked\":"<<(e.second_gate_checked?"true":"false")<<",\"handler_invoked\":"<<(e.handler_invoked?"true":"false")
        <<",\"terminal_state\":"<<e.terminal_state<<",\"terminal_reason\":"<<e.terminal_reason;
}
}
