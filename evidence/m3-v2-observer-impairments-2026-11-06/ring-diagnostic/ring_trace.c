#define _GNU_SOURCE
#include <dlfcn.h>
#include <linux/if_packet.h>
#include <sys/socket.h>
#include <stdio.h>
#include <stdint.h>
int setsockopt(int fd,int level,int option,const void* value,socklen_t length){
 int (*real)(int,int,int,const void*,socklen_t)=dlsym(RTLD_NEXT,"setsockopt");
 int result=real(fd,level,option,value,length);
 if(level==SOL_PACKET&&option==PACKET_VERSION&&length==sizeof(int))fprintf(stderr,"M3_RING_VERSION %d rc=%d\n",*(const int*)value,result);
 if(level==SOL_PACKET&&option==PACKET_RX_RING&&length>=sizeof(struct tpacket_req)){
  const struct tpacket_req* r=value;fprintf(stderr,"M3_RING_GEOMETRY block_size=%u block_count=%u frame_size=%u frame_count=%u bytes=%llu rc=%d\n",r->tp_block_size,r->tp_block_nr,r->tp_frame_size,r->tp_frame_nr,(unsigned long long)r->tp_block_size*r->tp_block_nr,result);
 }
 return result;
}
