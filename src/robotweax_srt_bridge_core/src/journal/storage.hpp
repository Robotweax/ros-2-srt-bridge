#pragma once
#include <robotweax/srt_bridge/journal.hpp>
#include <sqlite3.h>
#include <array>

namespace robotweax::srt_bridge::storage {
class QuotaVfs {
public:
    explicit QuotaVfs(const JournalOptions& options);
    ~QuotaVfs();
    QuotaVfs(const QuotaVfs&)=delete;
    QuotaVfs& operator=(const QuotaVfs&)=delete;
    sqlite3_vfs vfs{};
    sqlite3_vfs* base=nullptr;
    std::array<std::string,4> paths;
    std::uint64_t maximum,wal_maximum;
    JournalFaults* faults;
    std::uint64_t bytes() const;
    bool allow(int kind,sqlite3_int64 end) const noexcept;
    const char* name() const noexcept{return name_.c_str();}
private:
    std::string name_;
};
}
