#include <bpf/btf.h>
#include <bpf/bpf.h>
#include <linux/btf.h>
#include <linux/bpf.h>
#include <iostream>
#include <cstring>
#include <unistd.h>
int main(){auto*b=btf__parse("/sys/kernel/btf/vmlinux",nullptr);if(!b)return 1;
for(const char*n:{"btf_trace_net_dev_queue","btf_trace_net_dev_start_xmit","btf_trace_net_dev_xmit","btf_trace_qdisc_enqueue","btf_trace_qdisc_dequeue","btf_trace_kfree_skb","btf_trace_consume_skb"}){int id=btf__find_by_name(b,n);std::cout<<n<<" id="<<id; if(id>0){auto*t=btf__type_by_id(b,id);while(btf_kind(t)!=BTF_KIND_FUNC_PROTO&&t->type)t=btf__type_by_id(b,t->type);auto*p=btf_params(t);for(unsigned i=0;i<btf_vlen(t);++i)std::cout<<" "<<btf__name_by_offset(b,p[i].name_off)<<":"<<p[i].type;}std::cout<<"\n";}
bpf_insn ins[2]{};ins[0].code=BPF_ALU64|BPF_MOV|BPF_K;ins[0].dst_reg=0;ins[1].code=BPF_JMP|BPF_EXIT;
int p=bpf_prog_load(BPF_PROG_TYPE_RAW_TRACEPOINT,"m3_capability","GPL",ins,2,nullptr);std::cout<<"program="<<p<<" errno="<<strerror(errno)<<"\n";if(p<0)return 2;for(const char*n:{"net_dev_queue","net_dev_start_xmit","net_dev_xmit","qdisc_enqueue","qdisc_dequeue","kfree_skb","consume_skb"}){int fd=bpf_raw_tracepoint_open(n,p);std::cout<<n<<" attached="<<(fd>=0)<<" errno="<<(fd<0?strerror(errno):"none")<<"\n";if(fd>=0)close(fd);}close(p);btf__free(b);}
