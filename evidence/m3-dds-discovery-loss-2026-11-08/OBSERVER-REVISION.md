# Native probe no-loss callback diagnostic

Sourced12feb5 baseline FAILED after45s despite mutual participant/endpoint matching
and425/426 writes; both observers show0 valid/invalid HELLO callbacks. The fault
case is NOT EXECUTED. Captures are complete and show small28-byte HELLO CDR data
at both taps. Native DDS close footers and child shutdown are clean. This result
is a probe/control failure, not evidence for the fragment hypothesis.

Add reader-callback/take-result and type-deserializer counters/last-length to the
standalone fixture only, with no acceptance relaxation. Rebuild the standalone
probe; production binaries untouched. Run a fresh no-loss baseline with those
observers under the same45s callback gate. If it fails, skip fault again. Preserve
all original files and failed/unexecuted outcomes under their original directory.
A new diagnostic directory distinguishes source/binary hashes. Use these counters
to identify the reader/codec boundary before authorizing any fragment injection.
