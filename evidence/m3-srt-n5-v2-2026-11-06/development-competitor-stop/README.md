# Expected negative competitor-stop test

This is deliberately interrupted development coverage, separate from the frozen
three-repetition positive N5 cohort. A real measurement-start marker precedes
SIGINT to the sole iperf client in the owned robot container. The runner returns
failed with the competitor-exited error, despite valid offered load up to the
stop. This proves that an early-ended competitor cannot leave an uncontended
remainder accepted as N5. Early abort lacks endpoint_measurements, so capture
window analysis also fails; no complete workload, capture-window or closed-
journal acceptance is claimed. Raw artifacts remain local with hashes.
