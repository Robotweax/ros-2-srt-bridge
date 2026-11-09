// Passive source TX lifecycle observer; no verdicts, kernel addresses or host tuning.
#include <bpf/bpf.h>
#include <bpf/btf.h>
#include <bpf/libbpf.h>
#include <linux/bpf.h>
#include <linux/btf.h>
#include <arpa/inet.h>
#include <net/if.h>
#include <sys/stat.h>
#include <sys/prctl.h>
#include <unistd.h>
#include <signal.h>
#include <time.h>
#include <array>
#include <cerrno>
#include <cstring>
#include <fstream>
#include <iostream>
#include <map>
#include <stdexcept>
#include <string>
#include <vector>

namespace {
volatile sig_atomic_t stopping=0;
void stop(int){stopping=1;}
void require(bool b,const std::string& s){if(!b)throw std::runtime_error(s);}
uint64_t mono(){timespec t{};require(!clock_gettime(CLOCK_MONOTONIC,&t),"clock");return uint64_t(t.tv_sec)*1000000000+t.tv_nsec;}
struct Fd {int value=-1;explicit Fd(int n=-1):value(n){}Fd(const Fd&)=delete;~Fd(){close_now();}void close_now(){if(value>=0){close(value);value=-1;}}};
struct Types {
 btf* b=nullptr;
 Types(){b=btf__parse("/sys/kernel/btf/vmlinux",nullptr);require(b&&!libbpf_get_error(b),"kernel BTF unavailable");}
 ~Types(){btf__free(b);}
 const btf_type* type(int id){auto*t=btf__type_by_id(b,id);require(t,"BTF type missing");return t;}
 int resolve(int id){for(int i=0;i<32;++i){auto*t=type(id);switch(btf_kind(t)){case BTF_KIND_TYPEDEF:case BTF_KIND_CONST:case BTF_KIND_VOLATILE:case BTF_KIND_RESTRICT:id=t->type;break;default:return id;}}throw std::runtime_error("BTF cycle");}
 int named(const char* n,int kind){int id=btf__find_by_name_kind(b,n,kind);require(id>0,std::string("BTF name missing: ")+n);return id;}
 // Find anonymous aggregates recursively, reject ambiguous/bitfield/unaligned members.
 std::vector<std::pair<int,int>> fields(int id,const std::string& name,int base=0,int depth=0){require(depth<12,"BTF nesting");auto*t=type(resolve(id));std::vector<std::pair<int,int>> out;if(!btf_is_composite(t))return out;auto*m=btf_members(t);for(unsigned i=0;i<btf_vlen(t);++i){std::string n=btf__name_by_offset(b,m[i].name_off);int bit=btf_member_bit_offset(t,i);if(n==name){require(!(bit%8)&&!btf_member_bitfield_size(t,i),"BTF bitfield");out.emplace_back(base+bit/8,m[i].type);}else if(n.empty()){auto more=fields(m[i].type,name,base+bit/8,depth+1);out.insert(out.end(),more.begin(),more.end());}}return out;}
 std::pair<int,int> field(int id,const char* n,int size){auto v=fields(id,n);require(v.size()==1,std::string("ambiguous BTF field ")+n);require(btf__resolve_size(b,v[0].second)==size,std::string("BTF field size ")+n);return v[0];}
 std::string spelling(int id){id=resolve(id);auto*t=type(id);if(btf_is_ptr(t))return spelling(t->type)+"*";if(!id)return "void";return btf__name_by_offset(b,t->name_off);}
 void signature(const char* name,const std::vector<std::string>& expected){int id=named((std::string("btf_trace_")+name).c_str(),BTF_KIND_TYPEDEF);auto*t=type(resolve(id));require(btf_is_ptr(t),"trace typedef pointer");t=type(resolve(t->type));require(btf_is_func_proto(t)&&btf_vlen(t)==expected.size()+1,"trace prototype arity");auto*p=btf_params(t);require(spelling(p[0].type)=="void*","implicit trace data");for(unsigned i=0;i<expected.size();++i)require(spelling(p[i+1].type)==expected[i],std::string("trace arg type: ")+name+" "+std::to_string(i)+" got "+spelling(p[i+1].type));}
};
struct Layout {int dev,head,mac,ifindex,nd_net,net_inum,qhandle,qparent;};
Layout layout(Types& b){int skb=b.named("sk_buff",BTF_KIND_STRUCT),dev=b.named("net_device",BTF_KIND_STRUCT),net=b.named("net",BTF_KIND_STRUCT),q=b.named("Qdisc",BTF_KIND_STRUCT);auto nd=b.field(dev,"nd_net",8);auto ptr=b.field(nd.second,"net",8);auto ns=b.fields(net,"ns");require(ns.size()==1,"net.ns");auto inum=b.field(ns[0].second,"inum",4);return {b.field(skb,"dev",8).first,b.field(skb,"head",8).first,b.field(skb,"mac_header",2).first,b.field(dev,"ifindex",4).first,nd.first+ptr.first,ns[0].first+inum.first,b.field(q,"handle",4).first,b.field(q,"parent",4).first};}
struct Hook {const char* name;int kind,skb_arg;std::vector<std::string> signature;};
const std::array<Hook,6> hooks{{{"net_dev_queue",1,0,{"sk_buff*"}},{"qdisc_enqueue",2,2,{"Qdisc*","netdev_queue*","sk_buff*"}},{"qdisc_dequeue",3,3,{"Qdisc*","netdev_queue*","int","sk_buff*"}},{"net_dev_start_xmit",4,0,{"sk_buff*","net_device*"}},{"kfree_skb",5,0,{"sk_buff*","void*","skb_drop_reason","sock*"}},{"consume_skb",6,0,{"sk_buff*","void*"}}}};
struct Stats {uint64_t created,emitted,reserve_failed,map_failed,read_failed,collision,retired;};
struct Record {uint64_t ns,cookie;uint32_t kind,aux,handle,parent;};
static_assert(sizeof(Record)==32);
struct Program {
 std::vector<bpf_insn> code;std::map<std::string,size_t> labels;std::vector<std::pair<size_t,std::string>> jumps;
 void op(uint8_t c,uint8_t d=0,uint8_t s=0,int16_t o=0,int32_t i=0){bpf_insn x{};x.code=c;x.dst_reg=d;x.src_reg=s;x.off=o;x.imm=i;code.push_back(x);}
 void imm(int d,int v){op(BPF_ALU64|BPF_MOV|BPF_K,d,0,0,v);}void mov(int d,int s){op(BPF_ALU64|BPF_MOV|BPF_X,d,s);}void add(int d,int v){op(BPF_ALU64|BPF_ADD|BPF_K,d,0,0,v);}
 void map(int d,int fd){op(BPF_LD|BPF_DW|BPF_IMM,d,BPF_PSEUDO_MAP_FD,0,fd);op(0);}void call(int h){op(BPF_JMP|BPF_CALL,0,0,0,h);}void label(const std::string&s){labels[s]=code.size();}
 void jump(uint8_t c,int r,int v,const std::string&s){jumps.emplace_back(code.size(),s);op(BPF_JMP|c|BPF_K,r,0,0,v);}void count(int off){imm(0,1);op(BPF_STX|BPF_DW|BPF_ATOMIC,8,0,off,BPF_ADD);}
 void jump32(uint8_t c,int r,int v,const std::string&s){jumps.emplace_back(code.size(),s);op(BPF_JMP32|c|BPF_K,r,0,0,v);}
 void finish(){for(auto [i,n]:jumps){require(labels.count(n),"jump label");require(labels.at(n)<code.size(),"jump out of range");code[i].off=labels.at(n)-i-1;}}
 void stack(int r,int off){mov(r,10);add(r,off);}void read(int dst,int size,int src,int offset){stack(1,dst);imm(2,size);mov(3,src);add(3,offset);call(BPF_FUNC_probe_read_kernel);jump(BPF_JNE,0,0,"read_failed");}
 void lookup(int mapfd){map(1,mapfd);stack(2,-8);call(BPF_FUNC_map_lookup_elem);}
};
// Stack: skb key -8, scratch -24..-16, cookie -32, exact header -96..-55.
Program program(const Hook& h,const Layout& l,int stats,int ring,int tracked,uint32_t netns,uint32_t index,const std::array<uint8_t,42>& header){
 Program p;p.mov(6,1);p.op(BPF_ST|BPF_W|BPF_MEM,10,0,-4,0);p.map(1,stats);p.stack(2,-4);p.call(BPF_FUNC_map_lookup_elem);p.jump(BPF_JEQ,0,0,"exit");p.mov(8,0);
 p.op(BPF_LDX|BPF_DW|BPF_MEM,7,6,h.skb_arg*8);p.jump(BPF_JEQ,7,0,"exit");p.op(BPF_STX|BPF_DW|BPF_MEM,10,7,-8);
 if(h.kind==1){
  p.read(-16,8,7,l.dev);p.op(BPF_LDX|BPF_DW|BPF_MEM,9,10,-16);p.jump(BPF_JEQ,9,0,"exit");p.read(-24,4,9,l.ifindex);p.op(BPF_LDX|BPF_W|BPF_MEM,0,10,-24);p.jump32(BPF_JNE,0,index,"exit");p.read(-24,8,9,l.nd_net);p.op(BPF_LDX|BPF_DW|BPF_MEM,9,10,-24);p.read(-24,4,9,l.net_inum);p.op(BPF_LDX|BPF_W|BPF_MEM,0,10,-24);p.jump32(BPF_JNE,0,netns,"exit");
  p.read(-16,8,7,l.head);p.read(-24,2,7,l.mac);p.op(BPF_LDX|BPF_DW|BPF_MEM,9,10,-16);p.op(BPF_LDX|BPF_H|BPF_MEM,0,10,-24);p.op(BPF_ALU64|BPF_ADD|BPF_X,9,0);p.read(-96,42,9,0);
  for(int off=0;off<40;off+=4){uint32_t word;std::memcpy(&word,header.data()+off,4);p.op(BPF_LDX|BPF_W|BPF_MEM,0,10,-96+off);p.jump32(BPF_JNE,0,word,"exit");}uint16_t tail;std::memcpy(&tail,header.data()+40,2);p.op(BPF_LDX|BPF_H|BPF_MEM,0,10,-56);p.jump32(BPF_JNE,0,tail,"exit");
  p.lookup(tracked);p.jump(BPF_JNE,0,0,"collision");p.imm(0,1);p.op(BPF_STX|BPF_DW|BPF_ATOMIC,8,0,0,BPF_ADD|BPF_FETCH);p.add(0,1);p.op(BPF_STX|BPF_DW|BPF_MEM,10,0,-32);
  p.map(1,tracked);p.stack(2,-8);p.stack(3,-32);p.imm(4,BPF_NOEXIST);p.call(BPF_FUNC_map_update_elem);p.jump(BPF_JNE,0,0,"map_failed");
 }else{p.lookup(tracked);p.jump(BPF_JEQ,0,0,"exit");p.op(BPF_LDX|BPF_DW|BPF_MEM,0,0,0);p.op(BPF_STX|BPF_DW|BPF_MEM,10,0,-32);}
 // Timestamp immediately before record reservation, same VM monotonic clock.
 p.call(BPF_FUNC_ktime_get_ns);p.mov(7,0);p.map(1,ring);p.imm(2,sizeof(Record));p.imm(3,0);p.call(BPF_FUNC_ringbuf_reserve);p.jump(BPF_JEQ,0,0,"reserve_failed");p.mov(9,0);
 for(int off=0;off<int(sizeof(Record));off+=8)p.op(BPF_ST|BPF_DW|BPF_MEM,9,0,off,0);
 p.op(BPF_STX|BPF_DW|BPF_MEM,9,7,0);p.op(BPF_LDX|BPF_DW|BPF_MEM,0,10,-32);p.op(BPF_STX|BPF_DW|BPF_MEM,9,0,8);p.op(BPF_ST|BPF_W|BPF_MEM,9,0,16,h.kind);
 // Reads while ring reservation held must discard on failure.
 if(h.kind==2||h.kind==3){p.op(BPF_LDX|BPF_DW|BPF_MEM,7,6,0);for(auto [src,dst]:std::array<std::pair<int,int>,2>{{{l.qhandle,24},{l.qparent,28}}}){p.mov(1,9);p.add(1,dst);p.imm(2,4);p.mov(3,7);p.add(3,src);p.call(BPF_FUNC_probe_read_kernel);p.jump(BPF_JNE,0,0,"discard_read_failed");}}
 if(h.kind==3||h.kind==5){p.op(BPF_LDX|BPF_DW|BPF_MEM,0,6,16);p.op(BPF_STX|BPF_W|BPF_MEM,9,0,20);}
 p.mov(1,9);p.imm(2,0);p.call(BPF_FUNC_ringbuf_submit);p.count(8);p.jump(BPF_JA,0,0,"retire");
 if(h.kind==2||h.kind==3){p.label("discard_read_failed");p.mov(1,9);p.imm(2,0);p.call(BPF_FUNC_ringbuf_discard);p.count(32);p.jump(BPF_JA,0,0,"retire");}
 p.label("reserve_failed");p.count(16);p.label("retire");if(h.kind>=4){p.map(1,tracked);p.stack(2,-8);p.call(BPF_FUNC_map_delete_elem);p.jump(BPF_JNE,0,0,"map_failed");p.count(48);}p.jump(BPF_JA,0,0,"exit");
 if(h.kind==1){p.label("collision");p.count(40);p.jump(BPF_JA,0,0,"exit");}if(h.kind==1||h.kind>=4){p.label("map_failed");p.count(24);p.jump(BPF_JA,0,0,"exit");}if(h.kind==1){p.label("read_failed");p.count(32);}p.label("exit");p.imm(0,0);p.op(BPF_JMP|BPF_EXIT);p.finish();return p;
}
void unsigned_regression(){
 std::array<char,64> data{};
 for(bool narrow:{false,true}){Program p;p.op(BPF_ALU|BPF_MOV|BPF_K,7,0,0,int32_t(0xf0000001));if(narrow)p.jump32(BPF_JNE,7,int32_t(0xf0000001),"mismatch");else p.jump(BPF_JNE,7,int32_t(0xf0000001),"mismatch");p.imm(0,42);p.op(BPF_JMP|BPF_EXIT);p.label("mismatch");p.imm(0,0);p.op(BPF_JMP|BPF_EXIT);p.finish();Fd fd(bpf_prog_load(BPF_PROG_TYPE_SOCKET_FILTER,"arp_u32_check","GPL",p.code.data(),p.code.size(),nullptr));require(fd.value>=0,"unsigned regression load");bpf_test_run_opts opt{};opt.sz=sizeof(opt);opt.data_in=data.data();opt.data_size_in=data.size();require(!bpf_prog_test_run_opts(fd.value,&opt),"unsigned regression run");require(opt.retval==(narrow?42u:0u),"unexpected comparison semantics");}
 std::cout<<"{\"passed\":true,\"high_bit_u32\":4026531841,\"jmp64_matches\":false,\"jmp32_matches\":true}\n";
}
struct Sink {std::ofstream out;uint64_t records=0;bool failed=false;};
int consume(void* ctx,void* data,size_t size){auto&s=*static_cast<Sink*>(ctx);if(size!=sizeof(Record)||s.records>=1000000){s.failed=true;return -1;}auto&r=*static_cast<Record*>(data);s.out<<"{\"ns\":"<<r.ns<<",\"cookie\":"<<r.cookie<<",\"kind\":"<<r.kind<<",\"aux\":"<<r.aux<<",\"handle\":"<<r.handle<<",\"parent\":"<<r.parent<<"}\n";++s.records;if(!s.out){s.failed=true;return -1;}return 0;}
std::array<uint8_t,6> mac(const char* s){std::array<uint8_t,6> out{};unsigned a[6];int n=0;require(sscanf(s,"%x:%x:%x:%x:%x:%x%n",&a[0],&a[1],&a[2],&a[3],&a[4],&a[5],&n)==6&&s[n]==0,"MAC");for(int i=0;i<6;++i){require(a[i]<256,"MAC byte");out[i]=a[i];}return out;}
}
int main(int argc,char**argv){try{
 require(!prctl(PR_SET_NAME,"m3_arp_trace",0,0,0),"process name");
 require(argc==2||argc==9,"usage: arp_packet_trace --inspect | IFACE SOURCE_IP TARGET_IP SOURCE_MAC TARGET_MAC OUT READY MAX_SECONDS");Types b;auto l=layout(b);for(auto&h:hooks)b.signature(h.name,h.signature);
 if(argc==2){if(std::string(argv[1])=="--selftest"){unsigned_regression();return 0;}require(std::string(argv[1])=="--inspect","inspect argument");std::cout<<"{\"btf_valid\":true,\"offsets\":["<<l.dev<<","<<l.head<<","<<l.mac<<","<<l.ifindex<<","<<l.nd_net<<","<<l.net_inum<<","<<l.qhandle<<","<<l.qparent<<"],\"drop_reasons\":{";int id=b.named("skb_drop_reason",BTF_KIND_ENUM);auto*t=b.type(id);auto*e=btf_enum(t);for(unsigned i=0;i<btf_vlen(t);++i){if(i)std::cout<<",";std::cout<<"\""<<e[i].val<<"\":\""<<btf__name_by_offset(b.b,e[i].name_off)<<"\"";}std::cout<<"}}\n";return 0;}
 require(!std::ifstream(argv[6]).good()&&!std::ifstream(argv[7]).good(),"output already exists");char*end=nullptr;long duration=strtol(argv[8],&end,10);require(!*end&&duration>0&&duration<=600,"duration 1..600");
 std::ifstream offsets("/proc/self/timens_offsets");std::string cname;long secs,nsecs;int clocks=0;while(offsets>>cname>>secs>>nsecs){require(!secs&&!nsecs,"nonzero time namespace");++clocks;}require(clocks==2,"clock proof");
 struct stat st{};require(!stat("/proc/self/ns/net",&st)&&st.st_ino<=UINT32_MAX,"net namespace");uint32_t netns=st.st_ino,index=if_nametoindex(argv[1]);require(index,"interface");
 auto src=mac(argv[4]),dst=mac(argv[5]);std::array<uint8_t,42> header{};std::memcpy(header.data(),dst.data(),6);std::memcpy(header.data()+6,src.data(),6);header[12]=8;header[13]=6;header[15]=1;header[16]=8;header[18]=6;header[19]=4;header[21]=2;std::memcpy(header.data()+22,src.data(),6);std::memcpy(header.data()+32,dst.data(),6);require(inet_pton(AF_INET,argv[2],header.data()+28)==1&&inet_pton(AF_INET,argv[3],header.data()+38)==1,"IPv4");
 Fd stats(bpf_map_create(BPF_MAP_TYPE_ARRAY,"arp_stats",4,sizeof(Stats),1,nullptr)),ring(bpf_map_create(BPF_MAP_TYPE_RINGBUF,"arp_events",0,0,1<<22,nullptr)),tracked(bpf_map_create(BPF_MAP_TYPE_HASH,"arp_lifetimes",8,8,4096,nullptr));require(stats.value>=0&&ring.value>=0&&tracked.value>=0,"map creation");
 Sink sink{std::ofstream(argv[6])};require(sink.out.good(),"output");ring_buffer* buffer=ring_buffer__new(ring.value,consume,&sink,nullptr);require(buffer,"ring buffer");
 // All links owned here; close even on exceptions/partial attachment.
 std::vector<int> links;struct Links {std::vector<int>&v;~Links(){for(int fd:v)close(fd);}} guard{links};
 for(const auto&h:hooks){auto p=program(h,l,stats.value,ring.value,tracked.value,netns,index,header);std::array<char,262144> log{};bpf_prog_load_opts opt{};opt.sz=sizeof(opt);opt.log_buf=log.data();opt.log_size=log.size();opt.log_level=1;Fd prog(bpf_prog_load(BPF_PROG_TYPE_RAW_TRACEPOINT,"arp_lifecycle","GPL",p.code.data(),p.code.size(),&opt));if(prog.value<0){std::cerr<<log.data();throw std::runtime_error(std::string("load ")+h.name+": "+strerror(errno));}int fd=bpf_raw_tracepoint_open(h.name,prog.value);require(fd>=0,std::string("attach ")+h.name+": "+strerror(errno));links.push_back(fd);}
 signal(SIGINT,stop);signal(SIGTERM,stop);auto ready=mono();{std::ofstream out(argv[7]);out<<"{\"version\":2,\"ready_ns\":"<<ready<<",\"netns\":"<<netns<<",\"ifindex\":"<<index<<",\"hooks\":6,\"clock\":\"kernel_monotonic\"}\n";require(out.good(),"ready write");}
 bool poll_failed=false;while(!stopping&&mono()-ready<uint64_t(duration)*1000000000){int rc=ring_buffer__poll(buffer,100);if(rc<0&&rc!=-EINTR){poll_failed=true;break;}}
 bool deadline=!stopping;uint64_t detach_before=mono();for(int fd:links)close(fd);links.clear();for(int i=0;i<4;++i)if(ring_buffer__poll(buffer,100)<0)poll_failed=true;
 uint32_t key=0;Stats a{},later{};require(!bpf_map_lookup_elem(stats.value,&key,&a),"stats");if(ring_buffer__poll(buffer,100)<0)poll_failed=true;require(!bpf_map_lookup_elem(stats.value,&key,&later),"stats reread");ring_buffer__free(buffer);sink.out.flush();uint64_t previous=0,next=0,pending=0;int rc=bpf_map_get_next_key(tracked.value,nullptr,&next);while(!rc){++pending;previous=next;rc=bpf_map_get_next_key(tracked.value,&previous,&next);}require(errno==ENOENT,"map enumeration");
 bool complete=!deadline&&!poll_failed&&!sink.failed&&sink.out.good()&&!memcmp(&a,&later,sizeof(a))&&a.emitted==sink.records&&!a.reserve_failed&&!a.map_failed&&!a.read_failed&&!a.collision&&a.created==a.retired+pending;
 std::cout<<"{\"complete\":"<<(complete?"true":"false")<<",\"deadline\":"<<(deadline?"true":"false")<<",\"created\":"<<a.created<<",\"emitted\":"<<a.emitted<<",\"records\":"<<sink.records<<",\"reserve_failed\":"<<a.reserve_failed<<",\"map_failed\":"<<a.map_failed<<",\"read_failed\":"<<a.read_failed<<",\"collision\":"<<a.collision<<",\"retired\":"<<a.retired<<",\"pending\":"<<pending<<",\"ready_ns\":"<<ready<<",\"detach_before_ns\":"<<detach_before<<",\"detached_hooks\":6,\"time_namespace_zero\":true}\n";return complete?0:2;
 }catch(const std::exception&e){std::cerr<<e.what()<<"\n";return 1;}}
