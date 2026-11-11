// Passive AF_PACKET socket observer. No tc/XDP hooks or traffic verdicts.
#include <bpf/bpf.h>
#include <bpf/libbpf.h>
#include <linux/bpf.h>
#include <linux/if_packet.h>
#include <net/ethernet.h>
#include <net/if.h>
#include <arpa/inet.h>
#include <sys/socket.h>
#include <sys/prctl.h>
#include <sys/ioctl.h>
#include <unistd.h>
#include <signal.h>
#include <time.h>
#include <array>
#include <cerrno>
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <map>
#include <stdexcept>
#include <string>
#include <vector>

namespace {
volatile sig_atomic_t stopping=0;
void stop(int){stopping=1;}
uint64_t mono(){timespec t{};if(clock_gettime(CLOCK_MONOTONIC,&t))throw std::runtime_error("clock_gettime");return uint64_t(t.tv_sec)*1000000000+t.tv_nsec;}
struct Record {uint64_t ns;uint32_t length,captured,type,ifindex,gso_segs,gso_size,vlan_present,vlan_tci;std::array<uint8_t,128> prefix;};
static_assert(sizeof(Record)==168);
struct Counters {uint64_t seen,submitted,reserve_failed,copy_failed;};
struct Program {
 std::vector<bpf_insn> code;std::map<std::string,size_t> labels;std::vector<std::pair<size_t,std::string>> jumps;
 void op(uint8_t c,uint8_t d=0,uint8_t s=0,int16_t o=0,int32_t i=0){bpf_insn x{};x.code=c;x.dst_reg=d;x.src_reg=s;x.off=o;x.imm=i;code.push_back(x);}
 void imm(int d,int value){op(BPF_ALU64|BPF_MOV|BPF_K,d,0,0,value);}
 void mov(int d,int s){op(BPF_ALU64|BPF_MOV|BPF_X,d,s);}
 void map(int d,int fd){op(BPF_LD|BPF_DW|BPF_IMM,d,BPF_PSEUDO_MAP_FD,0,fd);op(0);}
 void call(int helper){op(BPF_JMP|BPF_CALL,0,0,0,helper);}
 void label(const std::string& name){labels[name]=code.size();}
 void jump(uint8_t condition,int reg,int value,const std::string& name){jumps.emplace_back(code.size(),name);op(BPF_JMP|condition|BPF_K,reg,0,0,value);}
 void count(int offset){imm(0,1);op(BPF_STX|BPF_DW|BPF_XADD,8,0,offset);}
 void finish(){for(const auto& [index,name]:jumps)code[index].off=labels.at(name)-index-1;}
};
Program program(int stats,int ring){
 Program p;p.mov(6,1);p.map(1,stats);p.mov(2,10);p.op(BPF_ALU64|BPF_ADD|BPF_K,2,0,0,-4);p.op(BPF_ST|BPF_W|BPF_MEM,10,0,-4,0);p.call(BPF_FUNC_map_lookup_elem);p.jump(BPF_JEQ,0,0,"exit");p.mov(8,0);p.count(0);
 p.call(BPF_FUNC_ktime_get_ns);p.mov(7,0);p.map(1,ring);p.imm(2,sizeof(Record));p.imm(3,0);p.call(BPF_FUNC_ringbuf_reserve);p.jump(BPF_JEQ,0,0,"reserve_failed");p.mov(9,0);
 for(int offset=0;offset<int(sizeof(Record));offset+=8)p.op(BPF_ST|BPF_DW|BPF_MEM,9,0,offset,0);
 p.op(BPF_STX|BPF_DW|BPF_MEM,9,7,0);p.op(BPF_LDX|BPF_W|BPF_MEM,7,6,offsetof(__sk_buff,len));p.op(BPF_STX|BPF_W|BPF_MEM,9,7,8);p.jump(BPF_JLE,7,128,"bounded");p.imm(7,128);p.label("bounded");p.jump(BPF_JEQ,7,0,"copy_failed");p.op(BPF_STX|BPF_W|BPF_MEM,9,7,12);
 for(const auto& pair:std::array<std::pair<int,int>,6>{{{int(offsetof(__sk_buff,pkt_type)),16},{int(offsetof(__sk_buff,ifindex)),20},{int(offsetof(__sk_buff,gso_segs)),24},{int(offsetof(__sk_buff,gso_size)),28},{int(offsetof(__sk_buff,vlan_present)),32},{int(offsetof(__sk_buff,vlan_tci)),36}}}){p.op(BPF_LDX|BPF_W|BPF_MEM,0,6,pair.first);p.op(BPF_STX|BPF_W|BPF_MEM,9,0,pair.second);}
 p.mov(1,6);p.imm(2,0);p.mov(3,9);p.op(BPF_ALU64|BPF_ADD|BPF_K,3,0,0,40);p.mov(4,7);p.call(BPF_FUNC_skb_load_bytes);p.jump(BPF_JNE,0,0,"copy_failed");p.mov(1,9);p.imm(2,0);p.call(BPF_FUNC_ringbuf_submit);p.count(8);p.jump(BPF_JA,0,0,"exit");
 p.label("copy_failed");p.mov(1,9);p.imm(2,0);p.call(BPF_FUNC_ringbuf_discard);p.count(24);p.jump(BPF_JA,0,0,"exit");p.label("reserve_failed");p.count(16);p.label("exit");p.imm(0,0);p.op(BPF_JMP|BPF_EXIT);p.finish();return p;
}
struct Sink {std::ofstream file;uint64_t records=0;bool failed=false;};
int consume(void* context,void* data,size_t bytes){auto& sink=*static_cast<Sink*>(context);if(sink.records>=((128ULL<<20)-16)/sizeof(Record)||bytes!=sizeof(Record)){sink.failed=true;return -1;}sink.file.write(static_cast<char*>(data),bytes);if(!sink.file){sink.failed=true;return -1;}++sink.records;return 0;}
struct Fd {int value=-1;~Fd(){if(value>=0)close(value);}void close_now(){if(value>=0){close(value);value=-1;}}};
}
int main(int argc,char** argv){
 try {
  if(prctl(PR_SET_NAME,"m3_mono_cap",0,0,0))throw std::runtime_error("process name failed");
  if(argc!=4&&argc!=5)throw std::runtime_error("usage: monotonic_capture INTERFACE OUTPUT READY_JSON [RING_BYTES] (output files must not exist)");
  uint32_t ring_bytes=1<<24;
  if(argc==5){char* rest=nullptr;auto value=std::strtoul(argv[4],&rest,10);if(*rest||value<4096||value>(1<<24)||(value&(value-1)))throw std::runtime_error("invalid ring size");ring_bytes=value;}
  // bpf_ktime_get_ns is the kernel's monotonic clock, not a time namespace offset.
  std::ifstream offsets("/proc/self/timens_offsets");std::string name;long seconds,nanos;int clocks=0;
  while(offsets>>name>>seconds>>nanos){if(seconds||nanos)throw std::runtime_error("nonzero time namespace offset");++clocks;}if(clocks!=2)throw std::runtime_error("missing time namespace proof");
  if(std::ifstream(argv[2]).good()||std::ifstream(argv[3]).good())throw std::runtime_error("output already exists");
  const auto index=if_nametoindex(argv[1]);if(!index)throw std::runtime_error("interface missing");
  Fd stats{bpf_map_create(BPF_MAP_TYPE_ARRAY,"m3_stats",4,sizeof(Counters),1,nullptr)};Fd ring{bpf_map_create(BPF_MAP_TYPE_RINGBUF,"m3_packets",0,0,ring_bytes,nullptr)};
  if(stats.value<0||ring.value<0)throw std::runtime_error("BPF map create: "+std::string(strerror(errno)));
  auto p=program(stats.value,ring.value);std::array<char,131072> verifier{};bpf_prog_load_opts opts{};opts.sz=sizeof(opts);opts.log_buf=verifier.data();opts.log_size=verifier.size();opts.log_level=1;
  Fd prog{bpf_prog_load(BPF_PROG_TYPE_SOCKET_FILTER,"m3_monotonic","GPL",p.code.data(),p.code.size(),&opts)};
  if(prog.value<0){std::cerr<<verifier.data();throw std::runtime_error("BPF program load: "+std::string(strerror(errno)));}
  Sink sink{std::ofstream(argv[2],std::ios::binary)};if(!sink.file)throw std::runtime_error("output open failed");
  // Artifact v2 adds GSO/VLAN metadata; SDK wire/IPC is unchanged.
  const std::array<uint32_t,4> header{0x314d5253,2,sizeof(Record),1};sink.file.write(reinterpret_cast<const char*>(header.data()),sizeof(header));
  ring_buffer* buffer=ring_buffer__new(ring.value,consume,&sink,nullptr);if(!buffer)throw std::runtime_error("ring buffer create failed");
  Fd socket{::socket(AF_PACKET,SOCK_RAW|SOCK_CLOEXEC,htons(ETH_P_ALL))};if(socket.value<0)throw std::runtime_error("AF_PACKET socket failed");
  ifreq device{};std::strncpy(device.ifr_name,argv[1],IFNAMSIZ-1);if(ioctl(socket.value,SIOCGIFMTU,&device))throw std::runtime_error("MTU read failed");const int mtu=device.ifr_mtu;
  sockaddr_ll address{};address.sll_family=AF_PACKET;address.sll_protocol=htons(ETH_P_ALL);address.sll_ifindex=index;
  if(bind(socket.value,reinterpret_cast<sockaddr*>(&address),sizeof(address)))throw std::runtime_error("socket bind failed");
  const auto attach_before=mono();if(setsockopt(socket.value,SOL_SOCKET,SO_ATTACH_BPF,&prog.value,sizeof(prog.value)))throw std::runtime_error("socket attach failed");const auto ready=mono();
  signal(SIGINT,stop);signal(SIGTERM,stop);
  {std::ofstream marker(argv[3]);marker<<"{\"version\":1,\"clock\":\"kernel_monotonic\",\"ifindex\":"<<index<<",\"attach_before_ns\":"<<attach_before<<",\"ready_ns\":"<<ready<<"}\n";if(!marker)throw std::runtime_error("ready write failed");}
  bool poll_failed=false;while(!stopping){int rc=ring_buffer__poll(buffer,100);if(rc<0&&rc!=-EINTR){poll_failed=true;break;}}
  const auto stop_before=mono();socket.close_now();
  // Socket close detaches the sole hook; consume queued records before reading final counters.
  for(int i=0;i<3;++i){if(ring_buffer__poll(buffer,100)<0)poll_failed=true;}
  Counters counters{},later{};uint32_t key=0;if(bpf_map_lookup_elem(stats.value,&key,&counters))throw std::runtime_error("stats read failed");
  if(ring_buffer__poll(buffer,100)<0)poll_failed=true;
  if(bpf_map_lookup_elem(stats.value,&key,&later))throw std::runtime_error("stats reread failed");
  ring_buffer__free(buffer);sink.file.flush();const bool complete=!poll_failed&&!sink.failed&&sink.file.good()&&!std::memcmp(&counters,&later,sizeof(counters))&&counters.seen==counters.submitted+counters.reserve_failed+counters.copy_failed&&counters.submitted==sink.records&&!counters.reserve_failed&&!counters.copy_failed;
  std::cout<<"{\"complete\":"<<(complete?"true":"false")<<",\"records\":"<<sink.records<<",\"seen\":"<<counters.seen<<",\"submitted\":"<<counters.submitted<<",\"reserve_failed\":"<<counters.reserve_failed<<",\"copy_failed\":"<<counters.copy_failed<<",\"ready_ns\":"<<ready<<",\"stop_before_ns\":"<<stop_before<<",\"ifindex\":"<<index<<",\"time_namespace_zero\":true,\"ring_bytes\":"<<ring_bytes<<",\"clock\":\"kernel_monotonic\",\"artifact_version\":2,\"mtu\":"<<mtu<<",\"record_bytes\":168,\"prefix_bytes\":128}\n";
  return complete?0:2;
 }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
}
