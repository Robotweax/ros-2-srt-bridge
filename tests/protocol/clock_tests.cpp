#include <robotweax/srt_bridge/clock.hpp>
#include <array>
#include <iostream>
#include <limits>
#include <random>
#include <stdexcept>
using namespace robotweax::srt_bridge;
namespace {
std::size_t assertions = 0;
void check(bool condition, const char* message) {
    ++assertions;
    if (!condition) throw std::runtime_error(message);
}
Identity id(unsigned value) { Identity result{}; result[0] = static_cast<std::byte>(value); return result; }
ClockMapper mapper(ClockConfig config = {0, 0, 5000000000ULL, 50000000}) {
    ClockMapper m(config); check(m.reset(id(1), id(2), 3, 4), "reset"); return m;
}
Probe probe(std::uint64_t t1, std::uint64_t t2, std::uint64_t t3, std::uint64_t t4) {
    return {id(1), id(2), 3, 4, t1, t2, t3, t4};
}
void examples() {
    auto m = mapper();
    check(!m.age_of_remote(0, 0).age_ns, "unknown age substituted");
    check(m.observe(probe(1000, 1120, 1130, 1040)) == ClockError::none, "asymmetric probe");
    check(m.offset_at_probe() == Interval{90, 120}, "offset direction/bounds");
    const auto age = m.age_of_remote(1150, 1080);
    check(age.age_ns == Interval{20, 50}, "age interval direction");
    check(age.within_budget(50) && !age.within_budget(49), "upper-bound gate");
    // Incoming data while a probe is outstanding must not invalidate that probe.
    check(m.age_of_remote(1150, 1090).age_ns.has_value(), "interleaved data");
    check(m.observe(probe(1080, 1200, 1210, 1120)) == ClockError::none, "probe rejected after interleaved data");
    auto reverse = mapper();
    check(reverse.observe(probe(1100, 1020, 1030, 1140)) == ClockError::none, "negative offset probe");
    check(reverse.offset_at_probe() == Interval{-110, -80}, "negative offset bounds");
    check(reverse.age_of_remote(1050, 1180).age_ns == Interval{20, 50}, "reverse age");
    auto old = mapper({0, 0, 100, 1000});
    check(old.observe(probe(1000, 1100, 1100, 1000)) == ClockError::none, "zero RTT");
    check(old.age_of_remote(1100, 1100).age_ns.has_value(), "exact probe-age boundary");
    check(old.check(1101) == ClockError::expired, "idle clock expiry");
    check(old.age_of_remote(1100, 1101).error == ClockError::expired, "probe expiry");
    check(old.observe(probe(1200, 1300, 1300, 1200)) == ClockError::none, "requalify expired model");
    check(old.age_of_remote(5000, 1201).error == ClockError::future_sample, "future sample");
    check(old.age_of_remote(1300, 1201).within_budget(1), "future sample poisoned model");
    auto broad = mapper({0, 0, 5000, 50});
    check(broad.observe(probe(1000, 1100, 1100, 1200)) == ClockError::unqualified, "broad model admitted");
    check(!broad.age_of_remote(1100, 1200).within_budget(1000), "uncertainty gate bypass");
    check(broad.observe(probe(1300, 1400, 1400, 1300)) == ClockError::none, "narrower probe did not qualify");
}
void invalidation() {
    for (int mode = 0; mode < 6; ++mode) {
        auto m = mapper();
        check(m.observe(probe(1000, 1100, 1100, 1000)) == ClockError::none, "initial probe");
        auto next = probe(2000, 2100, 2100, 2000);
        ClockError expected;
        if (mode == 0) { next.local_epoch = id(9); expected = ClockError::epoch_mismatch; }
        else if (mode == 1) { next.remote_domain = 9; expected = ClockError::domain_mismatch; }
        else if (mode == 2) { next.t3 = 2099; expected = ClockError::invalid_probe; }
        else if (mode == 3) { next.t1 = 900; expected = ClockError::clock_regressed; }
        else if (mode == 4) { next.t2 = next.t3 = 9999; expected = ClockError::contradictory; }
        else { next.t4 = std::numeric_limits<std::uint64_t>::max(); expected = ClockError::arithmetic_overflow; }
        check(m.observe(next) == expected, "wrong invalidation reason");
        check(!m.offset_at_probe() && !m.age_of_remote(2100, 2000).age_ns, "invalidated model exposed age");
        check(m.observe(probe(3000, 3100, 3100, 3000)) == expected, "invalidation was not sticky");
        check(m.reset(id(1), id(2), 3, 4), "recovery reset");
        check(m.observe(probe(3000, 3100, 3100, 3000)) == ClockError::none, "reset recovery");
    }
    auto m = mapper();
    check(m.observe(probe(100, 200, 250, 120)) == ClockError::invalid_probe, "negative network time");
    m = mapper(); check(m.observe(probe(1000, 1100, 1100, 1000)) == ClockError::none, "baseline");
    check(m.age_of_remote(1100, 999).error == ClockError::clock_regressed, "local clock step");
    check(!m.reset(id(1), id(1), 0, 0), "same boot identity");
    check(!m.reset({}, id(1), 0, 0), "zero boot identity");
    for (auto c : {ClockConfig{10001, 0, 1, 1}, {0, 1000000001, 1, 1}, {0, 0, 0, 1}, {0, 0, 1, 0}}) {
        bool threw = false;
        try { ClockMapper invalid(c); } catch (const std::invalid_argument&) { threw = true; }
        check(threw, "invalid configuration accepted");
    }
}
void drift_and_error() {
    // Remote time = local time * (1 + ppm/1e6) + fixed offset.
    std::mt19937 random(0x434c4f43);
    for (int ppm : {-200, -1, 0, 1, 200}) {
        for (int iteration = 0; iteration < 1000; ++iteration) {
            const std::int64_t offset = iteration % 2 ? 2000000000 : -2000000000;
            const auto remote_time = [ppm, offset](std::int64_t local) {
                return static_cast<std::uint64_t>(local + (local * ppm) / 1000000 + offset);
            };
            const std::uint64_t t1 = 10000000000ULL;
            const auto outbound = 1 + random() % 10000000;
            const auto inbound = 1 + random() % 10000000;
            const auto processing = random() % 10000;
            auto m = mapper({200, 1000, 5000000000ULL, 50000000});
            const auto p = probe(t1, remote_time(t1 + outbound), remote_time(t1 + outbound + processing),
                                 t1 + outbound + processing + inbound);
            check(m.observe(p) == ClockError::none, "drifting probe failed");
            // Exercise events on either side of the probe anchor.
            const auto local_source = t1 - 500000000 + random() % 1000000000;
            const auto now = t1 + 2000000000;
            const auto a = m.age_of_remote(remote_time(local_source), now);
            check(a.age_ns.has_value(), "drifting model lost qualification");
            const auto actual = static_cast<std::int64_t>(now - local_source);
            check(a.age_ns->lower <= actual && a.age_ns->upper >= actual, "true age outside conservative interval");
            check(!a.within_budget(static_cast<std::uint64_t>(a.age_ns->upper) - 1), "budget gate used midpoint");
            const auto next_start = t1 + 3000000000;
            check(m.observe(probe(next_start, remote_time(next_start + outbound),
                remote_time(next_start + outbound + processing), next_start + outbound + processing + inbound)) == ClockError::none,
                "consistent drifting probe intersection");
            const auto later = m.age_of_remote(remote_time(local_source), t1 + 4000000000);
            const auto later_actual = static_cast<std::int64_t>(t1 + 4000000000 - local_source);
            check(later.age_ns && later.age_ns->lower <= later_actual && later.age_ns->upper >= later_actual,
                "old event outside updated drifting model");
        }
    }
    auto m = mapper({10000, 1000, 60000000000ULL, 1000});
    check(m.observe(probe(100000, 100000, 100000, 100000)) == ClockError::unqualified, "timestamp errors omitted");
    m = mapper({10000, 0, 60000000000ULL, 1000});
    check(m.observe(probe(100000, 100000, 100000, 100000)) == ClockError::none, "precise initial model");
    check(m.age_of_remote(100000, 200000).error == ClockError::unqualified, "drift growth did not disable model");
    m = mapper();
    constexpr auto maximum = static_cast<std::uint64_t>(std::numeric_limits<std::int64_t>::max());
    check(m.observe(probe(0, maximum, maximum, 0)) == ClockError::none, "large offset baseline");
    check(!m.age_of_remote(0, maximum).age_ns, "overflow produced plausible age");
}
void qualification_limits(){
    auto m=mapper({1000,0,5000000000ULL,1000000});check(!m.qualification_deadline(),"unobserved clock issued lease");
    check(m.observe(probe(1000000,1000000,1000000,1000000))==ClockError::none,"lease probe failed");
    check(m.qualification_deadline()==501000000ULL,"drift width lease not conservative");
    check(m.check(501000000)==ClockError::none&&m.check(501000001)==ClockError::unqualified,"drift width boundary incorrect");check(!m.qualification_deadline(),"unqualified model issued lease");
    auto age=mapper({0,0,100,1000});check(age.observe(probe(1000,1000,1000,1000))==ClockError::none&&age.qualification_deadline()==1100,"probe-age lease incorrect");
    constexpr auto top=std::uint64_t(std::numeric_limits<std::int64_t>::max());auto end=mapper();check(end.observe(probe(top-10,top-10,top-10,top-10))==ClockError::none&&end.qualification_deadline()==top,"lease deadline overflow");
}
void integer_boundaries() {
    constexpr auto top = std::numeric_limits<std::int64_t>::max();
    struct Case { std::int64_t anchor, offset, source, receive; };
    for (const auto& c : {Case{0,0,0,0}, {top-10000,-10000,top-11000,top-9000},
        {10000,top-20000,5000,20000}, {top-10000,-(top-20000),top-15000,top-9000}}) {
        auto m = mapper();
        check(m.observe(probe(c.anchor, c.anchor+c.offset, c.anchor+c.offset, c.anchor)) == ClockError::none,
            "integer boundary probe");
        const auto a = m.age_of_remote(c.source+c.offset, c.receive);
        check(a.age_ns == Interval{c.receive-c.source,c.receive-c.source}, "integer boundary age");
    }
}
}
int main() {
    try {
        examples(); invalidation(); drift_and_error(); integer_boundaries(); qualification_limits();
        std::cout << "PASS clock contract: " << assertions << " assertions, 5000 drift scenarios\n";
    } catch (const std::exception& e) { std::cerr << "FAIL: " << e.what() << '\n'; return 1; }
}
