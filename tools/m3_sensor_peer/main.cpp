// Finite installed-provider SENSOR qualification. Never linked into the bridge.
#include <srt/srt.h>
#include <arpa/inet.h>
#include <array>
#include <algorithm>
#include <chrono>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <thread>
#include <vector>
using namespace std::chrono_literals;
namespace {
using Clock=std::chrono::steady_clock;
void require(bool ok,const char* message){if(!ok)throw std::runtime_error(message);}
void checked(int value,const char* message){if(value==SRT_ERROR)throw std::runtime_error(std::string(message)+": "+srt_getlasterror_str());}
template<class T> void set(SRTSOCKET s,SRT_SOCKOPT key,T value){checked(srt_setsockflag(s,key,&value,sizeof(value)),"set");}
template<class T> T get(SRTSOCKET s,SRT_SOCKOPT key){T value{};int size=sizeof(value);checked(srt_getsockflag(s,key,&value,&size),"get");require(size==sizeof(value),"option size");return value;}
struct Socket{SRTSOCKET fd=srt_create_socket();Socket(){require(fd!=SRT_INVALID_SOCK,"socket");}~Socket(){srt_close(fd);}Socket(const Socket&)=delete;};
void atomic_write(const std::filesystem::path& p,const std::string& value){auto tmp=p;tmp+=".tmp";{std::ofstream out(tmp);out<<value<<'\n';require(bool(out),"write");}std::filesystem::rename(tmp,p);}
std::uint64_t ns(){return std::chrono::duration_cast<std::chrono::nanoseconds>(Clock::now().time_since_epoch()).count();}
void wait_file(const std::filesystem::path& p){const auto end=Clock::now()+12s;while(!std::filesystem::exists(p)){require(Clock::now()<end,"file barrier timeout");std::this_thread::sleep_for(2ms);}}
void configure(SRTSOCKET s,const std::string& key){
 set(s,SRTO_TRANSTYPE,SRTT_SENSOR);set(s,SRTO_MSS,1500);set(s,SRTO_ENFORCEDENCRYPTION,true);
 set(s,SRTO_CRYPTOMODE,std::int32_t(2));set(s,SRTO_PBKEYLEN,32);set(s,SRTO_ROBOTWEAX_SESSIONAUTH,true);
 checked(srt_setsockflag(s,SRTO_PASSPHRASE,key.data(),static_cast<int>(key.size())),"secret");
 set(s,SRTO_PAYLOADSIZE,1024);set(s,SRTO_FC,256);set(s,SRTO_SNDBUF,256*1024);set(s,SRTO_RCVBUF,256*1024);
 set(s,SRTO_UDP_SNDBUF,256*1024);set(s,SRTO_UDP_RCVBUF,256*1024);set(s,SRTO_CONNTIMEO,3000);
 set(s,SRTO_SNDSYN,false);set(s,SRTO_RCVSYN,false);set(s,SRTO_LINGER,linger{0,0});
}
void negotiated(SRTSOCKET s){
 require(get<SRT_TRANSTYPE>(s,SRTO_TRANSTYPE)==SRTT_SENSOR,"profile");
 require(get<int>(s,SRTO_CRYPTOMODE)==2&&get<bool>(s,SRTO_ROBOTWEAX_SESSIONAUTH)&&get<bool>(s,SRTO_ENFORCEDENCRYPTION)&&get<int>(s,SRTO_PBKEYLEN)==32,"security downgrade");
 require(!get<bool>(s,SRTO_TSBPDMODE)&&!get<bool>(s,SRTO_TLPKTDROP),"timing profile");
 std::array<char,512> filter{};int size=filter.size();checked(srt_getsockflag(s,SRTO_PACKETFILTER,filter.data(),&size),"filter");
 require(std::string(filter.data())=="fec-sensor-v1,cols:4,rows:1,arq:never","filter contract");
 const auto end=Clock::now()+4s;
 while(get<int>(s,SRTO_SNDKMSTATE)!=SRT_KM_S_SECURED||get<int>(s,SRTO_RCVKMSTATE)!=SRT_KM_S_SECURED){require(Clock::now()<end,"key confirmation");std::this_thread::sleep_for(1ms);}
}
std::string stats(SRTSOCKET s){SRT_TRACEBSTATS v{};checked(srt_bstats(s,&v,0),"stats");return
 "{\"data_sent\":"+std::to_string(v.pktSentTotal)+",\"retransmitted\":"+std::to_string(v.pktRetransTotal)+
 ",\"filter_extra_sent\":"+std::to_string(v.pktSndFilterExtraTotal)+",\"filter_extra_received\":"+std::to_string(v.pktRcvFilterExtraTotal)+
 ",\"filter_supplied\":"+std::to_string(v.pktRcvFilterSupplyTotal)+",\"filter_loss\":"+std::to_string(v.pktRcvFilterLossTotal)+
 ",\"undecryptable\":"+std::to_string(v.pktRcvUndecryptTotal)+"}";}
std::array<char,128> payload(unsigned id){std::array<char,128> data{};for(unsigned i=0;i<data.size();++i)data[i]=static_cast<char>((id*17+i*29)&255);return data;}
}
int main(int argc,char** argv){try{
 require(argc==5,"mode run-directory peer-address credential-file");checked(srt_startup(),"startup");
 const bool receiver=std::string(argv[1])=="receive";require(receiver||std::string(argv[1])=="send","mode");
 const std::filesystem::path run=argv[2];std::ifstream keyfile(argv[4]);std::string key;std::getline(keyfile,key);require(key.size()>=10,"credential");
 Socket socket;configure(socket.fd,key);sockaddr_in address{};address.sin_family=AF_INET;
 address.sin_port=htons(receiver?10081:39781);address.sin_addr.s_addr=htonl(INADDR_ANY);
 checked(srt_bind(socket.fd,reinterpret_cast<sockaddr*>(&address),sizeof(address)),"bind");
 SRTSOCKET active=socket.fd;const auto deadline=Clock::now()+10s;
 if(receiver){checked(srt_listen(socket.fd,1),"listen");atomic_write(run/"listening","{}");
  while((active=srt_accept(socket.fd,nullptr,nullptr))==SRT_INVALID_SOCK){require(srt_getlasterror(nullptr)==SRT_EASYNCRCV,"accept");require(Clock::now()<deadline,"accept timeout");std::this_thread::sleep_for(1ms);}
 }else{require(inet_pton(AF_INET,argv[3],&address.sin_addr)==1,"peer address");address.sin_port=htons(10081);
  checked(srt_connect(active,reinterpret_cast<sockaddr*>(&address),sizeof(address)),"connect");
  while(srt_getsockstate(active)!=SRTS_CONNECTED){require(srt_getsockstate(active)!=SRTS_BROKEN&&Clock::now()<deadline,"connect timeout");std::this_thread::sleep_for(1ms);}
 }
 negotiated(active);const std::string side=receiver?"receiver":"sender";
 const auto origin=get<std::int32_t>(active,SRTO_ISN);require(origin>=0,"invalid initial sequence");
 atomic_write(run/(side+"-ready.json"),"{\"initial_sequence\":"+std::to_string(origin)+",\"socket_id\":"+std::to_string(active)+",\"ready_ns\":"+std::to_string(ns())+",\"sensor\":true,\"gcm\":true,\"sessionauth\":true,\"key_secured\":true,\"key_bytes\":32,\"payload_limit\":1024,\"fec\":\"fec-sensor-v1,cols:4,rows:1,arq:never\"}");
 wait_file(run/"armed");const auto initial=stats(active);std::string entries="[";
 if(receiver){
  const auto end=Clock::now()+4s;bool first=true;
  while(Clock::now()<end&&!std::filesystem::exists(run/"finish-receiver")){
   std::array<char,1024> data{};SRT_MSGCTRL ctrl=srt_msgctrl_default;
   const int size=srt_recvmsg2(active,data.data(),data.size(),&ctrl);
   if(size==SRT_ERROR){require(srt_getlasterror(nullptr)==SRT_EASYNCRCV,"receive");std::this_thread::sleep_for(1ms);continue;}
   require(size==128,"payload size");int identity=-1;
   for(unsigned i=0;i<16;++i){const auto expected=payload(i);if(std::equal(expected.begin(),expected.end(),data.begin()))identity=static_cast<int>(i);}
   require(identity>=0,"payload integrity");if(!first)entries+=",";first=false;
   entries+="{\"id\":"+std::to_string(identity)+",\"msgno\":"+std::to_string(ctrl.msgno)+",\"received_ns\":"+std::to_string(ns())+"}";
  }
 }else{
  for(unsigned i=0;i<16;++i){const auto data=payload(i);SRT_MSGCTRL ctrl=srt_msgctrl_default;ctrl.msgttl=250;ctrl.inorder=0;
   const auto begin=ns();checked(srt_sendmsg2(active,data.data(),data.size(),&ctrl),"send");const auto end=ns();
   require(ctrl.msgno==static_cast<int>(i+1),"unexpected assigned message identity");if(i)entries+=",";
   entries+="{\"id\":"+std::to_string(i)+",\"msgno\":"+std::to_string(ctrl.msgno)+",\"begin_ns\":"+std::to_string(begin)+",\"end_ns\":"+std::to_string(end)+"}";
   std::this_thread::sleep_for(10ms);
  }
  atomic_write(run/"sent","{}");wait_file(run/"finish-sender");
 }
 entries+="]";require(srt_getsockstate(active)==SRTS_CONNECTED,"connection changed");
 atomic_write(run/(side+"-result.json"),"{\"initial_stats\":"+initial+",\"final_stats\":"+stats(active)+",\"entries\":"+entries+",\"connected\":true,\"end_ns\":"+std::to_string(ns())+"}");
 wait_file(run/"release");
 if(receiver){srt_close(active);}
 srt_cleanup();return 0;
 }catch(const std::exception& e){std::cerr<<"FAIL "<<e.what()<<'\n';return 1;}}
