# Retained N3 two-loss4211 shutdown diagnosis — 2026-11-09

**A shutdown timeout is proven; the exact blocked function/root cause is not
recoverable from these captures.** The first8 strict passes and case9/cohort FAIL
remain unchanged. No tuning, patch, build, retry, process attachment, new fixture,
capture or experiment. All29 remaining campaign cases stay disabled. PR2 draft,
M3 not accepted as complete, M4 untouched.

`analyze.py` reads retained files and matching source only. It verifies all913 raw
hashes and the original complete campaign freeze, parses existing native packet
records and compares all9 same-build operator shutdowns. It does not open/recover
journals, run ROS/Docker/worker code or change a frozen source/tool/binary.
`assessment.json` contains per-case timelines; `input-hashes.json` pins all selected
inputs and source line anchors. Existing gate reports and raw artifacts are not
modified or retrospectively upgraded.

## What happened

| Observation | Evidence and limit |
|---|---|
|Eight clean controls|Operator SIGINT-to-reap167.531..221.600ms; every log has SAMPLE_TRACE_STATUS|
|Failed operator|PID141 alive at initial poll; SIGINT send returned; after existing5s wait, parent force-killed it, returncode-9; signal-to-reap5.011041044s|
|Last metrics|3.165358251s before SIGINT: ready/clock-qualified, fault0, worker_fault0, commands_sent0, all3 pending sensor counters0; not a shutdown-time snapshot|
|Last process sample|102.537375ms before SIGINT; bridge_node and plain robotweax-journ worker present. No post-signal process sample or thread/wchan/stack data|
|Last log event|7,308 consecutive parsed sample events; last event5.478214919s before SIGINT; no final footer or partial last line|
|Native packet evidence|Both retained measurement streams end about943.992..944.018ms before operator SIGINT; no shutdown-window packet observation|
|Resource scope|Last pre-signal cgroup sample: no recorded OOM events/throttling and no configured CPU/memory cap. Cannot exclude post-signal scheduling/I/O effects|
|Robot teardown|Source and bridge both exit0 without forced kill; operator's failure is separate|

The5.478s last-sample gap lies within the clean controls'5.097..5.560s gaps, so
silence after source pause is not itself evidence of a freeze during measurement.
A successful signal-send call does not establish entry into the bridge's signal
handler, return from spin, or entry into its destructor. Parent force-kill evidence
does establish the failed lifecycle gate; no earlier child crash is recorded.

## Matching code and actual operator path

1. The scenario's `stop_children` sends SIGINT to the bridge PID, waits5s,
   then kills and reaps it if necessary. Its flags explicitly record this path.
   The operator worker is a descendant managed by the native supervisor, not a
   separately signalled scenario child.
2. `BridgeNode::main` calls `rclcpp::spin`, resets the node, then calls
   `rclcpp::shutdown`. Its destructor resets timers, requests endpoint stop,
   joins the endpoint, drains enabled diagnostic queues, then prints the sample
   footer. Node member/base destruction happens after that destructor body.
3. Endpoint shutdown requests transport stop, stops/joins the journal worker,
   then joins transport. Coordinator/transport joins have no independent total
   deadline in these wrapper functions. The worker supervisor uses2s kill/4s
   join thresholds, but this does not bound all surrounding joins, lock waits,
   kernel operations or ROS shutdown to4s.
4. Transport shutdown applies session stop, closes sockets/listeners, releases
   epoll, and destroys its **run-local Provider**, which calls `srt_cleanup`.
   Therefore provider cleanup is inside the transport-thread completion path;
   missing the bridge footer does not rule it out. There is no retained marker
   proving the run reached socket close, epoll release or provider cleanup.
5. The **operator uses the plain SDK journal worker**, selected by the callee/
   sender branch. The ROS rate backend/ROS worker belongs to the robot caller
   branch. Applying a ROS-rate-worker shutdown fix to explain this operator
   worker would target the wrong executable. The bridge itself still uses ROS.

The missing footer is an observation boundary, not a stack trace: spin/ROS signal
handling, destructor entry/timer cleanup, endpoint/worker join, transport join/
provider operations and diagnostic drain cannot be distinguished. Later node/
RMW member destruction is less consistent with a missing footer if stdout stayed
healthy, but the record does not prove a uniquely reached stage. No command trace
was enabled, so native endpoint_stopping/transport_stopping points provide no
retained stage evidence. No logs prove a specific lock cycle or worker stop reply.

## Why observation stops

EndpointSampler is called from the scenario's spin loop. Cleanup synchronously
calls `stop_children` and closes the sampler afterward; it does not keep sampling
during that wait. This explains the missing post-signal samples without inferring
that the child stopped consuming CPU or that the sampler itself hung.
The host harness deliberately stops measurement recorders and collects interface
features **before** releasing the scenarios for child cleanup. Consequently packet
traces cannot separate queued ARP/FEC/socket closure traffic during this failure.
Reparsing more pre-signal packets cannot supply that missing time interval.

The same-build two-loss1701 and2903 controls exit normally. Thus two selected
packet losses alone are not a sufficient explanation, and the seed is a case
identifier rather than a proven cause. Missing final trace status also prevents
assuming complete final observer accounting for case9. Its measurement subgates
remain unqualified; there is no9/9, cohort splice or automatic later-stage credit.

## Engineering decision

Do not change the5s lifecycle gate, worker thresholds, queue sizes, source pacing,
clock rules, provider parameters or ROS rate backend based on this record.
No specific corrective patch is justified by an identified root cause yet.
The next discriminating evidence would be shutdown stage boundaries and a blocked
thread/worker stack covering the wait, not another broad seed sweep or packet
study. A narrowly scoped design would distinguish signal/spin return, destructor
entry, worker stop/join, transport close/provider cleanup/join and footer completion;
an independent observer must survive the scenario's synchronous wait. No such
instrumentation or experiment was implemented, scheduled or authorized here.

This requested retained-evidence diagnosis is complete to its observation limit.
Further execution requires a separate explicit scope decision; remaining stages
stay disabled. The cohort remains8 PASS/1 FAIL with all owned resources removed.
