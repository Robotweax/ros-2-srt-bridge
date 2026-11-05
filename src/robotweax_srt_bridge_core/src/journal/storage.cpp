#include "storage.hpp"
#include <atomic>
#include <cerrno>
#include <cstring>
#include <limits>
#include <stdexcept>
#include <sys/stat.h>

namespace robotweax::srt_bridge::storage {
namespace {
struct File {sqlite3_file api{};sqlite3_file* real=nullptr;QuotaVfs* quota=nullptr;int kind=-1;};
File* file(sqlite3_file* f){return reinterpret_cast<File*>(f);}
QuotaVfs* quota(sqlite3_vfs* v){return static_cast<QuotaVfs*>(v->pAppData);}
bool fault(int& counter){if(counter<0)return false;if(counter==0)return true;--counter;return false;}
std::uint64_t size(const std::string& path) {struct stat s{};if(::stat(path.c_str(),&s)==0)return static_cast<std::uint64_t>(s.st_size);if(errno==ENOENT)return 0;throw std::runtime_error("journal file stat failed");}
int close(sqlite3_file* f){return file(f)->real->pMethods->xClose(file(f)->real);}
int read(sqlite3_file* f,void* b,int n,sqlite3_int64 at){return file(f)->real->pMethods->xRead(file(f)->real,b,n,at);}
int write(sqlite3_file* f,const void* b,int n,sqlite3_int64 at){auto* q=file(f);
    if(n<0||at<0||at>std::numeric_limits<sqlite3_int64>::max()-n||!q->quota->allow(q->kind,at+n))return SQLITE_FULL;
    if(q->quota->faults&&fault(q->quota->faults->writes_before_failure))return q->quota->faults->full?SQLITE_FULL:SQLITE_IOERR_WRITE;
    return q->real->pMethods->xWrite(q->real,b,n,at);
}
int truncate(sqlite3_file* f,sqlite3_int64 end){auto* q=file(f);if(!q->quota->allow(q->kind,end))return SQLITE_FULL;return q->real->pMethods->xTruncate(q->real,end);}
int sync(sqlite3_file* f,int flags){auto* q=file(f);if(q->quota->faults&&fault(q->quota->faults->syncs_before_failure))return SQLITE_IOERR_FSYNC;return q->real->pMethods->xSync(q->real,flags);}
int filesize(sqlite3_file* f,sqlite3_int64* n){return file(f)->real->pMethods->xFileSize(file(f)->real,n);}
int lock(sqlite3_file* f,int n){return file(f)->real->pMethods->xLock(file(f)->real,n);}
int unlock(sqlite3_file* f,int n){return file(f)->real->pMethods->xUnlock(file(f)->real,n);}
int reserved(sqlite3_file* f,int* n){return file(f)->real->pMethods->xCheckReservedLock(file(f)->real,n);}
int control(sqlite3_file* f,int n,void* p){auto* q=file(f);
    if(n==SQLITE_FCNTL_SIZE_HINT&&!q->quota->allow(q->kind,*static_cast<sqlite3_int64*>(p)))return SQLITE_FULL;
    if(n==SQLITE_FCNTL_CHUNK_SIZE)return SQLITE_NOTFOUND; // no hidden allocation rounding
    if(n==SQLITE_FCNTL_VFS_POINTER){*static_cast<sqlite3_vfs**>(p)=&q->quota->vfs;return SQLITE_OK;}
    if(n==SQLITE_FCNTL_FILE_POINTER){*static_cast<sqlite3_file**>(p)=f;return SQLITE_OK;}
    return q->real->pMethods->xFileControl(q->real,n,p);
}
int sector(sqlite3_file* f){return file(f)->real->pMethods->xSectorSize(file(f)->real);}
int characteristics(sqlite3_file* f){return file(f)->real->pMethods->xDeviceCharacteristics(file(f)->real);}
int map(sqlite3_file* f,int page,int bytes,int extend,void volatile** out){auto* q=file(f);
    if(page<0||bytes<=0||(static_cast<std::uint64_t>(page)+1)*static_cast<std::uint64_t>(bytes)>32768||
       !q->quota->allow(2,(static_cast<sqlite3_int64>(page)+1)*bytes))return SQLITE_FULL;
    return q->real->pMethods->xShmMap(q->real,page,bytes,extend,out);
}
int shm_lock(sqlite3_file* f,int a,int b,int flags){return file(f)->real->pMethods->xShmLock(file(f)->real,a,b,flags);}
void barrier(sqlite3_file* f){file(f)->real->pMethods->xShmBarrier(file(f)->real);}
int unmap(sqlite3_file* f,int del){return file(f)->real->pMethods->xShmUnmap(file(f)->real,del);}
int fetch(sqlite3_file* f,sqlite3_int64 at,int n,void** p){auto* q=file(f);if(!q->real->pMethods->xFetch){*p=nullptr;return SQLITE_OK;}return q->real->pMethods->xFetch(q->real,at,n,p);}
int unfetch(sqlite3_file* f,sqlite3_int64 at,void* p){auto* q=file(f);return q->real->pMethods->xUnfetch?q->real->pMethods->xUnfetch(q->real,at,p):SQLITE_OK;}
const sqlite3_io_methods methods{3,close,read,write,truncate,sync,filesize,lock,unlock,reserved,control,sector,characteristics,map,shm_lock,barrier,unmap,fetch,unfetch};
int open(sqlite3_vfs* v,const char* name,sqlite3_file* f,int flags,int* out){auto* q=quota(v);auto* wrapped=new(f) File;
    wrapped->quota=q;wrapped->real=reinterpret_cast<sqlite3_file*>(reinterpret_cast<char*>(f)+sizeof(File));
    if(!name)return SQLITE_CANTOPEN;
    for(int i=0;i<4;++i)if(q->paths[i]==name)wrapped->kind=i;
    if(wrapped->kind<0||wrapped->kind==2)return SQLITE_CANTOPEN;
    const int result=q->base->xOpen(q->base,name,wrapped->real,flags|SQLITE_OPEN_NOFOLLOW,out);
    if(result!=SQLITE_OK)return result;
    if(wrapped->real->pMethods->iVersion<3){wrapped->real->pMethods->xClose(wrapped->real);return SQLITE_CANTOPEN;}
    wrapped->api.pMethods=&methods;return SQLITE_OK;
}
int del(sqlite3_vfs* v,const char* name,int syncdir){auto* q=quota(v);return q->base->xDelete(q->base,name,syncdir);}
int access(sqlite3_vfs* v,const char* name,int flags,int* out){auto* q=quota(v);return q->base->xAccess(q->base,name,flags,out);}
int full(sqlite3_vfs* v,const char* name,int n,char* out){auto* q=quota(v);return q->base->xFullPathname(q->base,name,n,out);}
void* dlopen(sqlite3_vfs* v,const char* p){auto* q=quota(v);return q->base->xDlOpen(q->base,p);}
void dlerror(sqlite3_vfs* v,int n,char* out){auto* q=quota(v);q->base->xDlError(q->base,n,out);}
void (*dlsym(sqlite3_vfs* v,void* h,const char* p))(void){auto* q=quota(v);return q->base->xDlSym(q->base,h,p);}
void dlclose(sqlite3_vfs* v,void* h){auto* q=quota(v);q->base->xDlClose(q->base,h);}
int random(sqlite3_vfs* v,int n,char* out){auto* q=quota(v);return q->base->xRandomness(q->base,n,out);}
int sleep(sqlite3_vfs* v,int n){auto* q=quota(v);return q->base->xSleep(q->base,n);}
int time(sqlite3_vfs* v,double* out){auto* q=quota(v);return q->base->xCurrentTime(q->base,out);}
int error(sqlite3_vfs* v,int n,char* out){auto* q=quota(v);return q->base->xGetLastError(q->base,n,out);}
int time64(sqlite3_vfs* v,sqlite3_int64* out){auto* q=quota(v);return q->base->xCurrentTimeInt64(q->base,out);}
int setcall(sqlite3_vfs* v,const char* p,sqlite3_syscall_ptr f){auto* q=quota(v);return q->base->xSetSystemCall?q->base->xSetSystemCall(q->base,p,f):SQLITE_NOTFOUND;}
sqlite3_syscall_ptr getcall(sqlite3_vfs* v,const char* p){auto* q=quota(v);return q->base->xGetSystemCall?q->base->xGetSystemCall(q->base,p):nullptr;}
const char* nextcall(sqlite3_vfs* v,const char* p){auto* q=quota(v);return q->base->xNextSystemCall?q->base->xNextSystemCall(q->base,p):nullptr;}
}
QuotaVfs::QuotaVfs(const JournalOptions& o):base(sqlite3_vfs_find(nullptr)),paths{o.path,o.path+"-wal",o.path+"-shm",o.path+"-journal"},
    maximum(o.max_bytes),wal_maximum(o.wal_bytes),faults(o.test_faults){
    static std::atomic<unsigned> serial{0};name_="rwbridge-quota-"+std::to_string(++serial);
    if(!base||base->iVersion<3)throw std::runtime_error("unsupported SQLite VFS");
    vfs=*base;vfs.iVersion=3;vfs.pNext=nullptr;vfs.szOsFile=sizeof(File)+base->szOsFile;vfs.zName=name_.c_str();vfs.pAppData=this;
    vfs.xOpen=open;vfs.xDelete=del;vfs.xAccess=access;vfs.xFullPathname=full;vfs.xDlOpen=dlopen;vfs.xDlError=dlerror;vfs.xDlSym=dlsym;vfs.xDlClose=dlclose;
    vfs.xRandomness=random;vfs.xSleep=sleep;vfs.xCurrentTime=time;vfs.xGetLastError=error;vfs.xCurrentTimeInt64=time64;
    vfs.xSetSystemCall=setcall;vfs.xGetSystemCall=getcall;vfs.xNextSystemCall=nextcall;
    if(bytes()>maximum||sqlite3_vfs_register(&vfs,0)!=SQLITE_OK)throw std::runtime_error("journal VFS quota/register failed");
}
QuotaVfs::~QuotaVfs(){sqlite3_vfs_unregister(&vfs);}
std::uint64_t QuotaVfs::bytes() const{std::uint64_t sum=0;for(const auto& p:paths)sum+=size(p);return sum;}
bool QuotaVfs::allow(int kind,sqlite3_int64 end) const noexcept{
    if(kind<0||kind>3||end<0)return false;
    try{
        const auto current=size(paths[kind]),total=bytes();const auto target=static_cast<std::uint64_t>(end);
        const auto limit=kind==1?wal_maximum:kind==2?32768:kind==3?16384:maximum-wal_maximum-32768-16384;
        return target<=limit&&total<=maximum&&(target<=current||target-current<=maximum-total);
    }catch(...){return false;}
}
}
