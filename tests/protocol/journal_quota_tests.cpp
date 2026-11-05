#include "journal/storage.hpp"
#include <filesystem>
#include <iostream>
#include <stdexcept>
#include <unistd.h>
using namespace robotweax::srt_bridge;
namespace {unsigned checks=0;void check(bool b,const char* m){++checks;if(!b)throw std::runtime_error(m);}}
int main(){sqlite3* db=nullptr;std::unique_ptr<storage::QuotaVfs> vfs;try{
    auto directory=std::filesystem::current_path()/("quota-artifacts-"+std::to_string(getpid()));
    for(unsigned n=0;std::filesystem::exists(directory);++n)directory=std::filesystem::current_path()/("quota-artifacts-"+std::to_string(getpid())+"-"+std::to_string(n));
    std::filesystem::create_directories(directory);JournalOptions o;o.path=(directory/"quota.sqlite").string();o.max_bytes=262144;o.wal_bytes=65536;
    vfs=std::make_unique<storage::QuotaVfs>(o);check(sqlite3_open_v2(o.path.c_str(),&db,SQLITE_OPEN_READWRITE|SQLITE_OPEN_CREATE,nullptr)==SQLITE_OK,"raw setup");sqlite3_close(db);db=nullptr;
    check(sqlite3_open_v2(o.path.c_str(),&db,SQLITE_OPEN_READWRITE,vfs->name())==SQLITE_OK,"quota open");
    check(sqlite3_exec(db,"PRAGMA locking_mode=EXCLUSIVE; PRAGMA temp_store=MEMORY; PRAGMA journal_mode=WAL; CREATE TABLE t(data BLOB);",nullptr,nullptr,nullptr)==SQLITE_OK,"quota schema");
    sqlite3_file* file=nullptr;check(sqlite3_file_control(db,"main",SQLITE_FCNTL_FILE_POINTER,&file)==SQLITE_OK&&file,"wrapped file pointer");
    sqlite3_int64 hint=1048576;check(file->pMethods->xFileControl(file,SQLITE_FCNTL_SIZE_HINT,&hint)==SQLITE_FULL,"size hint escaped quota");
    std::array<std::byte,4096> bytes{};check(file->pMethods->xWrite(file,bytes.data(),bytes.size(),1048576)==SQLITE_FULL,"write escaped quota");
    const int result=sqlite3_exec(db,"INSERT INTO t VALUES(zeroblob(200000));",nullptr,nullptr,nullptr);
    check((result&255)==SQLITE_FULL,"oversized transaction did not hit actual VFS quota");
    check(vfs->bytes()<=o.max_bytes,"physical logical-file quota exceeded");
    sqlite3_stmt* count=nullptr;check(sqlite3_prepare_v2(db,"SELECT count(*) FROM t",-1,&count,nullptr)==SQLITE_OK&&sqlite3_step(count)==SQLITE_ROW&&sqlite3_column_int(count,0)==0,"failed transaction committed data");sqlite3_finalize(count);
    check(sqlite3_close(db)==SQLITE_OK,"quota close");db=nullptr;
    std::cout<<"PASS journal quota contract: "<<checks<<" checks, WAL FULL, guarded preallocation/write\n";
}catch(const std::exception& e){if(db)sqlite3_close(db);std::cerr<<"FAIL: "<<e.what()<<'\n';return 1;}}
