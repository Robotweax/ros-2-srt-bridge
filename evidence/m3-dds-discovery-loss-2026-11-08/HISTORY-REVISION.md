# Reader-history boundary observer

The observer baseline still FAILED after45s with mutual matches, writes and DATA
at taps, but callback/deserializer/take-error counters all0. No payload was
rejected by the fixture codec because it was never entered. Fragment-cut again
NOT EXECUTED. This rules out attributing that run to the probe's explicit
length/header checks; no unique middleware cause established.

Add native sample-rejected/sample-lost listener records and unread-history count,
without polling/taking samples outside the listener or changing wire/QoS. Run a
fresh baseline under the original matching/callback gate, with fault still skipped
on failure. Preserve both earlier cohorts unchanged. No production code or
backend setting changes. The purpose is to locate the pre-callback/history gate,
not to obtain a favorable run by changing acceptance.
