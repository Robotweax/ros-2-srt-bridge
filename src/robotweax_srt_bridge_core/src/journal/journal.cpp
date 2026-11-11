#include <robotweax/srt_bridge/journal.hpp>
#include <robotweax/srt_bridge/management.hpp>
#include "storage.hpp"
#include <openssl/evp.h>
#include <sqlite3.h>
#include <algorithm>
#include <array>
#include <cstring>
#include <filesystem>
#include <limits>
#include <stdexcept>
#include <fcntl.h>
#include <sys/file.h>
#include <unistd.h>

namespace robotweax::srt_bridge {
namespace {
constexpr std::uint64_t max_time=std::numeric_limits<std::int64_t>::max();
using Record=std::array<std::byte,512>;
struct DbError:std::runtime_error{int code;explicit DbError(int c):std::runtime_error("journal SQLite operation failed"),code(c){}};
void dbcheck(int code){if(code!=SQLITE_OK&&code!=SQLITE_DONE&&code!=SQLITE_ROW)throw DbError(code);}
bool zero(const Identity& i){return std::all_of(i.begin(),i.end(),[](auto b){return b==std::byte{};});}
void put(Record& b,std::size_t at,unsigned count,std::uint64_t v){for(unsigned n=count;n>0;--n){b[at+n-1]=static_cast<std::byte>(v&255);v>>=8;}}
std::uint64_t read(const Record& b,std::size_t at,unsigned count){std::uint64_t v=0;for(unsigned n=0;n<count;++n)v=(v<<8)|std::to_integer<unsigned>(b[at+n]);return v;}
template<class A> void put_array(Record& b,std::size_t at,const A& a){std::copy(a.begin(),a.end(),b.begin()+at);}
template<class A> A array(const Record& b,std::size_t at){A a{};std::copy_n(b.begin()+at,a.size(),a.begin());return a;}
bool terminal(CommandState s){return s==CommandState::succeeded||s==CommandState::failed||s==CommandState::rejected||s==CommandState::expired||s==CommandState::unknown;}
Record pack(const JournalEntry& e){
    Record b{};b[0]=std::byte{'R'};b[1]=std::byte{'W'};b[2]=std::byte{'J'};b[3]=std::byte{'1'};
    put(b,4,2,1);put(b,6,1,static_cast<unsigned>(e.state));put(b,7,1,static_cast<unsigned>(e.reason));
    put(b,8,4,e.route);put(b,12,4,e.command.budget_ms);put_array(b,16,e.context.source_epoch);put(b,32,8,e.context.source_monotonic_ns);
    put_array(b,40,e.context.session);put_array(b,56,e.owner_epoch);put_array(b,72,e.payload_hash);
    put(b,104,4,e.command.rate_hz);put(b,112,8,e.command.expected_generation);put(b,120,8,e.command.new_generation);
    put(b,128,8,e.admitted_ns);put(b,136,8,e.dispatched_ns);put(b,144,8,e.finished_ns);put(b,152,8,e.context.deadline_ns);
    put(b,160,4,e.result.rate_hz);put(b,164,1,e.result.valid?1:0);put(b,168,8,e.result.generation);put(b,176,8,e.revision);
    return b;
}
struct Statement {
    sqlite3_stmt* s=nullptr;
    Statement(sqlite3* db,const char* sql){dbcheck(sqlite3_prepare_v2(db,sql,-1,&s,nullptr));}
    ~Statement(){sqlite3_finalize(s);}
    Statement(const Statement&)=delete;
    void blob(int index,const void* p,int n){dbcheck(sqlite3_bind_blob(s,index,p,n,SQLITE_TRANSIENT));}
    void number(int index,sqlite3_int64 n){dbcheck(sqlite3_bind_int64(s,index,n));}
    void text(int index,const std::string& text){dbcheck(sqlite3_bind_text(s,index,text.c_str(),text.size(),SQLITE_TRANSIENT));}
    int step(){const int c=sqlite3_step(s);dbcheck(c);return c;}
};
void exec(sqlite3* db,const char* sql){dbcheck(sqlite3_exec(db,sql,nullptr,nullptr,nullptr));}
std::uint64_t scalar(sqlite3* db,const char* sql){Statement s(db,sql);if(s.step()!=SQLITE_ROW)throw DbError(SQLITE_CORRUPT);return sqlite3_column_int64(s.s,0);}
struct Transaction {
    sqlite3* db;bool done=false;
    explicit Transaction(sqlite3* d):db(d){exec(db,"BEGIN IMMEDIATE");}
    ~Transaction(){if(!done)sqlite3_exec(db,"ROLLBACK",nullptr,nullptr,nullptr);}
    void commit(){exec(db,"COMMIT");done=true;}
};
JournalOptions normalize(JournalOptions o){
    if(o.path.empty()||o.path.find('\0')!=std::string::npos||o.path==":memory:"||o.local_peer_id.empty()||o.local_peer_id.size()>64||o.remote_peer_id.empty()||o.remote_peer_id.size()>64||
       o.local_peer_id==o.remote_peer_id||zero(o.process_epoch)||(o.side!=JournalSide::sender&&o.side!=JournalSide::receiver)||
       !o.max_entries||o.max_entries>10000||o.max_bytes<262144||o.max_bytes>67108864||o.wal_bytes<32768||o.wal_bytes>8388608||
       o.wal_bytes>o.max_bytes/3)throw std::invalid_argument("invalid journal configuration");
    std::array<std::byte,512> peer_check{};
    if(!encode_management(Hello{o.local_peer_id,{},{}},peer_check)||!encode_management(Hello{o.remote_peer_id,{},{}},peer_check))throw std::invalid_argument("invalid journal peer identity");
    const auto path=std::filesystem::absolute(o.path).lexically_normal();std::filesystem::create_directories(path.parent_path());
    o.path=path.string();return o;
}
}
struct CommandJournal::Impl {
    JournalOptions options;
    storage::QuotaVfs vfs;
    sqlite3* db=nullptr;
    int lock_fd=-1;
    bool poisoned=false;
    explicit Impl(JournalOptions o):options(normalize(std::move(o))),vfs(options){
        try{
            lock_fd=::open((options.path+".owner").c_str(),O_CREAT|O_RDWR|O_CLOEXEC|O_NOFOLLOW,0600);
            if(lock_fd<0||flock(lock_fd,LOCK_EX|LOCK_NB)!=0)throw std::runtime_error("journal already owned or unavailable");
            dbcheck(sqlite3_open_v2(options.path.c_str(),&db,SQLITE_OPEN_READWRITE|SQLITE_OPEN_CREATE|SQLITE_OPEN_NOMUTEX|SQLITE_OPEN_NOFOLLOW,vfs.name()));
            sqlite3_extended_result_codes(db,1);sqlite3_busy_timeout(db,0);
            exec(db,"PRAGMA trusted_schema=OFF; PRAGMA temp_store=MEMORY; PRAGMA mmap_size=0; PRAGMA cache_spill=OFF; PRAGMA locking_mode=EXCLUSIVE;");
            const auto app=scalar(db,"PRAGMA application_id"),version=scalar(db,"PRAGMA user_version");
            const bool fresh=app==0&&version==0&&scalar(db,"SELECT count(*) FROM sqlite_master")==0;
            if(!fresh&&(app!=0x52574a31||version!=1))throw std::runtime_error("journal schema identity mismatch");
            if(!fresh&&scalar(db,"PRAGMA page_size")!=4096)throw std::runtime_error("journal page size mismatch");
            if(fresh)exec(db,"PRAGMA page_size=4096");
            {Statement locking(db,"PRAGMA locking_mode");if(locking.step()!=SQLITE_ROW||std::strcmp(reinterpret_cast<const char*>(sqlite3_column_text(locking.s,0)),"exclusive")!=0)throw DbError(SQLITE_ERROR);}
            {Statement mode(db,"PRAGMA journal_mode=WAL");if(mode.step()!=SQLITE_ROW||std::strcmp(reinterpret_cast<const char*>(sqlite3_column_text(mode.s,0)),"wal")!=0)throw DbError(SQLITE_ERROR);}
            exec(db,"PRAGMA synchronous=FULL; PRAGMA wal_autocheckpoint=0; PRAGMA journal_size_limit=0;");
            const auto page_limit=(options.max_bytes-options.wal_bytes-32768-16384)/4096;
            exec(db,("PRAGMA max_page_count="+std::to_string(page_limit)).c_str());
            if(scalar(db,"PRAGMA synchronous")!=2||scalar(db,"PRAGMA max_page_count")!=page_limit)throw std::runtime_error("journal durability/size configuration mismatch");
            checkpoint();
            if(fresh){
                Transaction t(db);
                exec(db,"CREATE TABLE identity(local TEXT NOT NULL,remote TEXT NOT NULL,side INTEGER NOT NULL);"
                    "CREATE TABLE entries(id BLOB PRIMARY KEY CHECK(length(id)=16),route INTEGER NOT NULL,state INTEGER NOT NULL,record BLOB NOT NULL CHECK(length(record)=512)) WITHOUT ROWID;");
                Statement s(db,"INSERT INTO identity VALUES(?,?,?)");s.text(1,options.local_peer_id);s.text(2,options.remote_peer_id);s.number(3,static_cast<int>(options.side));s.step();
                exec(db,"PRAGMA application_id=1381452337; PRAGMA user_version=1;");t.commit();
            }
            {Statement s(db,"SELECT local,remote,side FROM identity");if(s.step()!=SQLITE_ROW||
                options.local_peer_id!=reinterpret_cast<const char*>(sqlite3_column_text(s.s,0))||options.remote_peer_id!=reinterpret_cast<const char*>(sqlite3_column_text(s.s,1))||
                static_cast<int>(options.side)!=sqlite3_column_int(s.s,2)||s.step()!=SQLITE_DONE)throw std::runtime_error("journal peer/direction mismatch");}
            // Paginate by immutable primary key; no read statement remains live at checkpoints.
            Identity previous{};bool have=false;
            for(;;){
                std::optional<Identity> next;
                {Statement s(db,have?"SELECT id FROM entries WHERE id>? ORDER BY id LIMIT 1":"SELECT id FROM entries ORDER BY id LIMIT 1");
                    if(have)s.blob(1,previous.data(),previous.size());
                    if(s.step()==SQLITE_ROW){if(sqlite3_column_bytes(s.s,0)!=16)throw DbError(SQLITE_CORRUPT);Identity id;std::memcpy(id.data(),sqlite3_column_blob(s.s,0),16);next=id;}}
                if(!next)break;
                previous=*next;have=true;auto e=load(*next);
                if(!e)throw DbError(SQLITE_CORRUPT);
                if(!terminal(e->state)){
                    if(options.side==JournalSide::receiver){e->reason=CommandReason::context_lost;e->state=e->state==CommandState::dispatching?CommandState::unknown:CommandState::rejected;++e->revision;}
                    else {e->reason=CommandReason::reconcile_required;e->state=CommandState::unknown;}
                    e->result={};mutate(*e);
                }
            }
            checkpoint();
        }catch(...){if(db)sqlite3_close(db);db=nullptr;if(lock_fd>=0)::close(lock_fd);lock_fd=-1;throw;}
    }
    ~Impl(){if(db)sqlite3_close(db);if(lock_fd>=0)::close(lock_fd);}
    void checkpoint(){int log=0,done=0;dbcheck(sqlite3_wal_checkpoint_v2(db,nullptr,SQLITE_CHECKPOINT_TRUNCATE,&log,&done));}
    void hook(JournalPoint point){if(options.test_hook)options.test_hook(point,options.test_context);}
    std::optional<JournalEntry> load(Identity id){
        Statement s(db,"SELECT route,state,record FROM entries WHERE id=?");s.blob(1,id.data(),id.size());if(s.step()==SQLITE_DONE)return {};
        if(sqlite3_column_bytes(s.s,2)!=512)throw DbError(SQLITE_CORRUPT);
        Record b;std::memcpy(b.data(),sqlite3_column_blob(s.s,2),b.size());JournalEntry e;e.request_id=id;
        if(read(b,0,4)!=0x52574a31||read(b,4,2)!=1||read(b,6,1)<1||read(b,6,1)>8||read(b,7,1)>6)throw DbError(SQLITE_CORRUPT);
        e.state=static_cast<CommandState>(read(b,6,1));e.reason=static_cast<CommandReason>(read(b,7,1));e.route=read(b,8,4);e.command.budget_ms=read(b,12,4);
        e.context.source_epoch=array<Identity>(b,16);e.context.source_monotonic_ns=read(b,32,8);e.context.session=array<Identity>(b,40);e.owner_epoch=array<Identity>(b,56);
        e.payload_hash=array<Digest>(b,72);e.command.rate_hz=read(b,104,4);e.command.expected_generation=read(b,112,8);e.command.new_generation=read(b,120,8);
        e.admitted_ns=read(b,128,8);e.dispatched_ns=read(b,136,8);e.finished_ns=read(b,144,8);e.context.deadline_ns=read(b,152,8);
        e.result={static_cast<std::uint32_t>(read(b,160,4)),read(b,168,8),read(b,164,1)!=0};e.revision=read(b,176,8);
        const bool provisional=options.side==JournalSide::sender&&e.state==CommandState::unknown&&e.reason==CommandReason::reconcile_required&&e.revision<=2&&!e.result.valid;
        const bool queued=options.side==JournalSide::sender&&e.state==CommandState::local_queued&&e.reason==CommandReason::none&&e.revision==0&&!e.result.valid;
        const bool locally_expired=options.side==JournalSide::sender&&e.state==CommandState::expired&&e.reason==CommandReason::start_deadline&&e.revision==0&&!e.result.valid;
        if(!provisional&&!queued&&!locally_expired&&!valid_remote_status(e.route,{e.state,e.reason,e.command,e.payload_hash,e.result,e.revision}))throw DbError(SQLITE_CORRUPT);
        if(zero(e.request_id)||zero(e.owner_epoch)||zero(e.context.session)||zero(e.context.source_epoch)||e.admitted_ns>max_time||e.dispatched_ns>max_time||e.finished_ns>max_time||e.context.source_monotonic_ns>max_time||e.context.deadline_ns>max_time)throw DbError(SQLITE_CORRUPT);
        if(!e.route||!valid_command(e.command)||e.payload_hash!=command_hash(e.route,e.command)||pack(e)!=b||
            sqlite3_column_int64(s.s,0)!=e.route||sqlite3_column_int(s.s,1)!=10+static_cast<int>(e.state))throw DbError(SQLITE_CORRUPT);
        return e;
    }
    void update(const JournalEntry& e,bool insert){
        auto b=pack(e);Statement s(db,insert?"INSERT INTO entries(id,route,state,record) VALUES(?,?,?,?)":"UPDATE entries SET route=?,state=?,record=? WHERE id=?");
        if(insert){s.blob(1,e.request_id.data(),16);s.number(2,e.route);s.number(3,10+static_cast<int>(e.state));s.blob(4,b.data(),b.size());}
        else{s.number(1,e.route);s.number(2,10+static_cast<int>(e.state));s.blob(3,b.data(),b.size());s.blob(4,e.request_id.data(),16);}
        s.step();if(sqlite3_changes(db)!=1)throw DbError(SQLITE_CORRUPT);
    }
    void mutate(const JournalEntry& e){checkpoint();Transaction t(db);update(e,false);t.commit();}
    JournalResult failed(int code){poisoned=true;return {(code&255)==SQLITE_CORRUPT?JournalError::corrupt:JournalError::storage};}
};
CommandJournal::CommandJournal(JournalOptions options):impl_(std::make_unique<Impl>(std::move(options))){}
CommandJournal::~CommandJournal()=default;
JournalResult CommandJournal::get(Identity id){if(impl_->poisoned)return {JournalError::storage};try{auto e=impl_->load(id);return e?JournalResult{JournalError::none,*e}:JournalResult{JournalError::not_found};}catch(const DbError& e){return impl_->failed(e.code);}}
JournalResult CommandJournal::admit(Identity id,std::uint32_t route,RateCommand command,CommandContext context,std::uint64_t now){
    auto& p=*impl_;if(p.poisoned)return {JournalError::storage};
    if(zero(id)||!route||!valid_command(command)||zero(context.session)||zero(context.source_epoch)||now>max_time||context.source_monotonic_ns>max_time||context.deadline_ns>max_time)return {JournalError::invalid};
    try{
        const auto hash=command_hash(route,command);
        if(auto e=p.load(id))return e->payload_hash==hash?JournalResult{JournalError::none,*e,false}:JournalResult{JournalError::conflict,*e,false};
        if(entry_count()>=p.options.max_entries||scalar(p.db,"PRAGMA page_count")+8>=scalar(p.db,"PRAGMA max_page_count"))return {JournalError::capacity};
        if(p.options.side==JournalSide::receiver&&scalar(p.db,"SELECT count(*) FROM entries WHERE state IN(12,13)")>=64)return {JournalError::busy};
        JournalEntry e;e.request_id=id;e.owner_epoch=p.options.process_epoch;e.route=route;e.command=command;e.context=context;e.payload_hash=hash;e.admitted_ns=now;
        e.state=p.options.side==JournalSide::sender?CommandState::local_queued:CommandState::accepted;e.revision=p.options.side==JournalSide::sender?0:1;
        if(now>context.deadline_ns){e.state=CommandState::expired;e.reason=CommandReason::start_deadline;e.finished_ns=now;}
        p.checkpoint();Transaction t(p.db);p.update(e,true);p.hook(JournalPoint::admission_before_commit);t.commit();p.hook(JournalPoint::admission_committed);
        return {JournalError::none,e,true};
    }catch(const DbError& e){return p.failed(e.code);}
}
JournalResult CommandJournal::begin_dispatch(Identity id,Identity session,bool qualified,std::uint64_t now){
    auto& p=*impl_;if(p.poisoned)return {JournalError::storage};
    try{
        auto e=p.load(id);if(!e)return {JournalError::not_found};
        if(p.options.side!=JournalSide::receiver||e->state!=CommandState::accepted)return {JournalError::invalid_state,*e};
        if(now>max_time||now<e->admitted_ns)return {JournalError::invalid};
        if(e->owner_epoch!=p.options.process_epoch||e->context.session!=session){e->state=CommandState::rejected;e->reason=CommandReason::context_lost;}
        else if(now>e->context.deadline_ns){e->state=CommandState::expired;e->reason=CommandReason::start_deadline;}
        else{
            if(!qualified)return {JournalError::clock_unqualified,*e};
            Statement active(p.db,"SELECT 1 FROM entries WHERE route=? AND state=13 LIMIT 1");active.number(1,e->route);
            if(active.step()==SQLITE_ROW)return {JournalError::busy,*e};
            e->state=CommandState::dispatching;
        }
        if(e->state==CommandState::dispatching)e->dispatched_ns=now;else e->finished_ns=now;
        ++e->revision;p.mutate(*e);p.hook(JournalPoint::dispatch_committed);return {JournalError::none,*e};
    }catch(const DbError& e){return p.failed(e.code);}
}
JournalResult CommandJournal::decline(Identity id,CommandState state,CommandReason reason,std::uint64_t now){
    auto& p=*impl_;if(p.poisoned)return {JournalError::storage};
    try{
        auto e=p.load(id);if(!e)return {JournalError::not_found};
        if(p.options.side!=JournalSide::receiver||e->state!=CommandState::accepted)return {JournalError::invalid_state,*e};
        if(now<e->admitted_ns||now>max_time||!((state==CommandState::rejected&&reason==CommandReason::context_lost)||(state==CommandState::expired&&reason==CommandReason::start_deadline)))return {JournalError::invalid};
        e->state=state;e->reason=reason;e->finished_ns=now;++e->revision;p.mutate(*e);return {JournalError::none,*e};
    }catch(const DbError& e){return p.failed(e.code);}
}
JournalResult CommandJournal::finish(Identity id,CommandState state,CommandReason reason,RateResult result,std::uint64_t now){
    auto& p=*impl_;if(p.poisoned)return {JournalError::storage};
    try{
        auto e=p.load(id);if(!e)return {JournalError::not_found};
        if(p.options.side!=JournalSide::receiver||e->state!=CommandState::dispatching||
           (state!=CommandState::succeeded&&state!=CommandState::failed&&state!=CommandState::expired&&state!=CommandState::rejected&&state!=CommandState::unknown))return {JournalError::invalid_state,*e};
        if(now<e->dispatched_ns||now>max_time||(state==CommandState::succeeded&&(!result.valid||result.rate_hz!=e->command.rate_hz||result.generation!=e->command.new_generation||reason!=CommandReason::none)))return {JournalError::invalid};
        CommandStatus proposed{state,reason,e->command,e->payload_hash,state==CommandState::succeeded?result:RateResult{},e->revision+1};
        if(!valid_remote_status(e->route,proposed))return {JournalError::invalid};
        e->state=state;e->reason=reason;e->result=proposed.result;e->finished_ns=now;++e->revision;
        p.checkpoint();Transaction t(p.db);p.update(*e,false);p.hook(JournalPoint::result_before_commit);t.commit();p.hook(JournalPoint::result_committed);
        return {JournalError::none,*e};
    }catch(const DbError& e){return p.failed(e.code);}
}
JournalResult CommandJournal::reconcile_sender(Identity id,std::uint32_t route,RateCommand command,CommandContext context,std::uint64_t now){
    auto& p=*impl_;if(p.poisoned)return {JournalError::storage};
    if(p.options.side!=JournalSide::sender||now>max_time||!valid_command(command))return {JournalError::invalid};
    try{
        auto e=p.load(id);if(!e)return {JournalError::not_found};
        if(e->owner_epoch!=p.options.process_epoch)return {JournalError::context_lost};
        if(e->route!=route||e->command!=command||e->payload_hash!=command_hash(route,command)||
           e->context.session!=context.session||e->context.source_epoch!=context.source_epoch||e->context.source_monotonic_ns!=context.source_monotonic_ns||e->context.deadline_ns!=context.deadline_ns)return {JournalError::conflict};
        if(now<e->admitted_ns)return {JournalError::invalid};
        // A delayed local receipt never overwrites an authoritative peer state.
        if(e->state==CommandState::local_queued){
            if(e->revision||e->reason!=CommandReason::none||e->result.valid)return {JournalError::invalid_state};
            e->state=CommandState::unknown;e->reason=CommandReason::reconcile_required;e->result={};p.mutate(*e);
        }
        return {JournalError::none,*e};
    }catch(const DbError& error){return p.failed(error.code);}
}
JournalError CommandJournal::invalidate_session(Identity session,std::uint64_t now){
    auto& p=*impl_;if(p.poisoned)return JournalError::storage;
    try{
        for(;;){std::optional<JournalEntry> candidate;
            {Statement s(p.db,p.options.side==JournalSide::receiver?"SELECT id FROM entries WHERE state=12 ORDER BY id":"SELECT id FROM entries WHERE state IN(11,12,13) ORDER BY id");while(s.step()==SQLITE_ROW){Identity id{};if(sqlite3_column_bytes(s.s,0)!=16)throw DbError(SQLITE_CORRUPT);std::memcpy(id.data(),sqlite3_column_blob(s.s,0),16);auto e=p.load(id);if(e&&e->context.session==session){candidate=e;break;}}}
            if(!candidate)break;
            if(now<candidate->admitted_ns||now>max_time)return JournalError::invalid;
            if(p.options.side==JournalSide::receiver){candidate->state=CommandState::rejected;candidate->reason=CommandReason::context_lost;candidate->finished_ns=now;++candidate->revision;}
            else{candidate->state=CommandState::unknown;candidate->reason=CommandReason::reconcile_required;candidate->result={};}
            p.mutate(*candidate);
        }return JournalError::none;
    }catch(const DbError& e){return p.failed(e.code).error;}
}
JournalError CommandJournal::observe_remote(Identity id,std::uint32_t route,const CommandStatus& status,std::uint64_t now){
    auto& p=*impl_;if(p.poisoned)return JournalError::storage;
    if(now>max_time||!valid_remote_status(route,status))return JournalError::invalid;
    try{
        auto local=p.load(id);if(!local)return JournalError::not_found;
        if(local->owner_epoch==p.options.process_epoch&&now<local->admitted_ns)return JournalError::invalid;
        if(p.options.side!=JournalSide::sender||local->route!=route||local->payload_hash!=status.payload_hash||local->command!=status.command)return JournalError::conflict;
        if(status.revision<local->revision)return JournalError::invalid_state;
        const bool reconciliable=local->state==CommandState::unknown&&local->reason==CommandReason::reconcile_required;
        const bool same=local->state==status.state&&local->reason==status.reason&&local->revision==status.revision&&local->result==status.result;
        if(terminal(local->state)&&!reconciliable)return same?JournalError::none:JournalError::invalid_state;
        if(status.revision==local->revision&&!reconciliable)return same?JournalError::none:JournalError::invalid_state;
        local->state=status.state;local->reason=status.reason;local->result=status.result;local->revision=status.revision;
        if(local->owner_epoch==p.options.process_epoch){
            if(status.state==CommandState::dispatching&&!local->dispatched_ns)local->dispatched_ns=now;
            if(terminal(status.state))local->finished_ns=now;
        }
        p.mutate(*local);return JournalError::none;
    }catch(const DbError& e){return p.failed(e.code).error;}
}
bool CommandJournal::sender_may_transmit(Identity id,Identity session,std::uint64_t now){
    auto r=get(id);return !impl_->poisoned&&impl_->options.side==JournalSide::sender&&r&&r.entry->state==CommandState::local_queued&&
        r.entry->owner_epoch==impl_->options.process_epoch&&r.entry->context.session==session&&now>=r.entry->admitted_ns&&now<=r.entry->context.deadline_ns;
}
std::uint64_t CommandJournal::file_bytes() const{return impl_->vfs.bytes();}
std::uint32_t CommandJournal::entry_count() const{return scalar(impl_->db,"SELECT count(*) FROM entries");}
bool CommandJournal::healthy() const noexcept{return !impl_->poisoned;}
}
