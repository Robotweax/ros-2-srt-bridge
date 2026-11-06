// Read-only ethtool feature/MTU snapshot. No SET ioctl is implemented.
#include <linux/ethtool.h>
#include <linux/sockios.h>
#include <net/if.h>
#include <sys/ioctl.h>
#include <sys/socket.h>
#include <unistd.h>
#include <cstdint>
#include <cstring>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <vector>
int main(int argc,char** argv){
 try{
  if(argc!=2||std::strlen(argv[1])>=IFNAMSIZ)throw std::runtime_error("usage: netdev_features INTERFACE");
  int fd=socket(AF_INET,SOCK_DGRAM|SOCK_CLOEXEC,0);if(fd<0)throw std::runtime_error("socket failed");
  ifreq req{};std::strcpy(req.ifr_name,argv[1]);
  if(ioctl(fd,SIOCGIFMTU,&req))throw std::runtime_error("MTU read failed");
  int mtu=req.ifr_mtu;
  auto query=[&](void* data){req.ifr_data=static_cast<char*>(data);if(ioctl(fd,SIOCETHTOOL,&req))throw std::runtime_error("ethtool read failed");};
  std::vector<uint64_t> info_mem((sizeof(ethtool_sset_info)+sizeof(uint32_t)+7)/8);auto* info=reinterpret_cast<ethtool_sset_info*>(info_mem.data());info->cmd=ETHTOOL_GSSET_INFO;info->sset_mask=1ULL<<ETH_SS_FEATURES;query(info);
  if(!(info->sset_mask&(1ULL<<ETH_SS_FEATURES))||!info->data[0]||info->data[0]>4096)throw std::runtime_error("feature set unavailable");
  const uint32_t count=info->data[0],blocks=(count+31)/32;
  std::vector<uint64_t> strings_mem((sizeof(ethtool_gstrings)+count*ETH_GSTRING_LEN+7)/8);auto* names=reinterpret_cast<ethtool_gstrings*>(strings_mem.data());names->cmd=ETHTOOL_GSTRINGS;names->string_set=ETH_SS_FEATURES;names->len=count;query(names);if(names->len!=count)throw std::runtime_error("feature names changed");
  std::vector<uint64_t> features_mem((sizeof(ethtool_gfeatures)+blocks*sizeof(ethtool_get_features_block)+7)/8);auto* features=reinterpret_cast<ethtool_gfeatures*>(features_mem.data());features->cmd=ETHTOOL_GFEATURES;features->size=blocks;query(features);if(features->size!=blocks)throw std::runtime_error("feature blocks changed");
  std::cout<<"{\"interface\":"<<std::quoted(argv[1])<<",\"mtu\":"<<mtu<<",\"read_only\":true,\"features\":{";bool first=true;
  for(uint32_t i=0;i<count;++i){const auto& b=features->features[i/32];const uint32_t bit=1U<<(i%32);const char* text=reinterpret_cast<const char*>(names->data+i*ETH_GSTRING_LEN);std::string name(text,strnlen(text,ETH_GSTRING_LEN));if(name.empty())continue;if(!first)std::cout<<',';first=false;
   std::cout<<std::quoted(name)<<":{\"active\":"<<((b.active&bit)?"true":"false")<<",\"available\":"<<((b.available&bit)?"true":"false")<<",\"requested\":"<<((b.requested&bit)?"true":"false")<<",\"fixed\":"<<((b.never_changed&bit)?"true":"false")<<'}';}
  std::cout<<"}}\n";close(fd);return 0;
 }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
}
