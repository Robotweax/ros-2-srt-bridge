from pathlib import Path
import hashlib,json,re,shutil,subprocess,sys
sys.path.insert(0,'tools');sys.path.insert(0,'.local/v2-observer-study-dev')
from audit_journals import audit
from m3_observer_study import source_inventory,installed_inventory
from m3_accounting import summarize_window
from m3_window_measurement import read_samples,summarize_cgroup
from m3_dds import summarize_competitor
import m3_monotonic_capture as mono
out=Path('evidence/m3-srt-n5-v2-2026-11-06');base=Path('.local/srt-n5-v2/20261106-retention256');dev=Path('.local/srt-n5-v2-dev');plan=json.load(open(base/'plan.json'));study=json.load(open(base/'study.json'));assert study['status']=='failed' and len(study['rows'])==2
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,d):p.write_text(json.dumps(d,indent=2)+'\n')
for n in ('plan.json','study.json'):shutil.copyfile(base/n,out/n)
for n in ('run_full.py','archive_outcome.py','analyze_capture_gap.py','capture-gap.json'):shutil.copyfile(dev/n,out/n)
shutil.copyfile('.local/v2-observer-study-dev/audit_journals.py',out/'audit_journals.py');raw=[];audits=[];commands=[];sensors=[];pcaps=[];isolation={};replayed=0
for item in study['rows']:
 label=item['slot']['label'];run=Path(item['run']);r=json.load(open(run/'run.json'));dest=out/label;dest.mkdir(exist_ok=True);assert r['source_sha256']==plan['source_sha256']
 for n in ('run.json','operator-result.json','robot-capture.log','operator-capture.log','robot-monotonic-capture.log','operator-monotonic-capture.log','robot-monotonic-ready.json','operator-monotonic-ready.json','profile-robot-readback.log','profile-operator-readback.log','before-robot.log','before-operator.log','after-robot.log','after-operator.log'):
  if (run/n).exists():shutil.copyfile(run/n,dest/n)
 net=json.load(open(run/'network.json'));dump(dest/'profile-commands.json',[dict(label=c['label'],argv=c['argv']) for c in net['commands'] if re.fullmatch(r'profile-(robot|operator)-[01]',c['label'])])
 for role in ('robot','operator'):
  q=json.load(open(run/('profile-'+role+'-readback.log')));tbf=next(x['options'] for x in q if x['kind']=='tbf');nem=next(x['options'] for x in q if x['kind']=='netem');assert tbf['rate']==64000 and tbf['burst']==4096 and tbf.get('lat')==448000 and nem['limit']==16 and nem['seed']==item['slot']['seed']+(role=='operator')
 a=audit(run);audits.append(a);results=r['results'];m=r['measurement_window'];assert summarize_window(results['checkpoints']['begin'],results['checkpoints']['end'],results['publication_interval'])==m
 assert a['receiver_successes']==results['device']['effects'];c=r['command_summary'];native=mono.summarize_run(run,net['addresses'],r['endpoint_measurements'],allow_udp_fragments=False,features=r['monotonic_capture_config']['features_before']);dump(dest/'native-independent-reanalysis.json',dict(original_run_status=r['status'],qualification_scope='independent native hook records only; does not rescue failed PCAP or overall case',**native))
 full=json.load(open(run/'competing-traffic.json'));offered=summarize_competitor(full);assert all(r['competitor_check'][k]==v for k,v in offered.items()) and r['competitor_check']['alive_poll_checks']>0
 dump(dest/'competitor-offered.json',dict(setup=full['start']['test_start'],total=full['end']['sum'],intervals=[v['sum'] for v in full['intervals']],raw_sha256=sha(run/'competing-traffic.json'),scope='whole-run offered load/liveness, not matched-window delivery'))
 isolation[label]={}
 for role in ('robot','operator'):
  h=json.load(open(run/(role+'-inspect.log')))[0]['HostConfig'];assert not h['Privileged'] and not h['PortBindings'];isolation[label][role]=dict(cap_add=h['CapAdd'],privileged=False,published_ports=False,clock_proof=r['clock_namespace_proof'][role])
  log=(run/(role+'-capture.log')).read_text();captured=int(re.findall(r'(\d+) packets? captured',log)[-1]);filtered=int(re.findall(r'(\d+) packets? received by filter',log)[-1]);drops=int(re.findall(r'(\d+) packets? dropped by kernel',log)[-1]);pcaps.append(dict(seed=item['slot']['seed'],role=role,run_status=r['status'],captured=captured,filter_received=filtered,file_records=r['captures'][role]['records'],kernel_drops=drops,overall_capture_qualified=r['status']=='passed'))
  projected=[dict(begin_ns=s['begin_ns'],end_ns=s['end_ns'],cgroup=s['cgroup']) for s in read_samples(run/(role+'-endpoint-samples.jsonl'))];(dest/(role+'-cgroup-samples.jsonl')).write_text(''.join(json.dumps(s)+'\n' for s in projected))
  for phase,w in r['endpoint_measurements']['windows'].items():assert summarize_cgroup(projected,*w['monotonic_ns'])==w['container_cgroup'][role];replayed+=1
 commands.append(dict(seed=item['slot']['seed'],overall_status=r['status'],capture_error=r.get('capture_error'),**c,effects=results['device']['effects'],skipped_slots=results['skipped_command_slots'],journal_sender_unknown=sum(e['state']==8 for e in a['roles']['operator']['entries'].values()),sender_only=a['sender_only'],receiver_only=a['receiver_only'],status_divergences=a['status_divergences'],pending_intent=results['unresolved_command'],competitor_check=r['competitor_check']))
 sensors.append(dict(seed=item['slot']['seed'],overall_status=r['status'],measurement=m,diagnostic_observation=results['diagnostic_observation'],pcap_clock_qualified={p:w['wire_clock']['qualified'] for p,w in r['endpoint_measurements']['windows'].items()}))
 for p in run.iterdir():
  if p.suffix in ('.sqlite','.mono','.jsonl') or '.pcap' in p.name or p.name=='competing-traffic.json':raw.append(dict(path=str(p),bytes=p.stat().st_size,sha256=sha(p)))
assert source_inventory()==plan['source_sha256'] and installed_inventory()==plan['installed_sha256']
assert all(sha(Path(p))==h for p,h in plan['installed_scripts'].items())
verification=dict(source_files_each=len(plan['source_sha256']),source_manifests=2,frozen_base_commit=plan['base_commit'],all_sources_match_frozen=True,selected_installed_sha256=installed_inventory(),installed_scripts=plan['installed_scripts'],cgroup_windows_replayed_exactly=replayed,failed_case_native_reanalysis_is_not_overall_acceptance=True)
for n,d in [('source-verification.json',verification),('raw-artifacts.json',raw),('journal-audits.json',audits),('command-outcomes.json',commands),('sensor-populations.json',sensors),('pcap-populations.json',pcaps),('isolation.json',isolation)]:dump(out/n,d)
(out/'RESULTS.md').write_text('''# SRT N5 frozen-plan outcome: failed

The plan executed seed 1701 (passed) and seed 2903 (failed), then stopped.
Seed 4211 was not executed. No case is replaced and no capture gate is relaxed.

| Seed | Overall verdict | Attempts | Confirmed successes/effects | Unresolved driver intent | Sender journal UNKNOWN | Skipped slots | Max terminal observation (ms) |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
'''+ '\n'.join(f"| {c['seed']} | {c['overall_status']} | {c['attempts']} | {c['effects']} | {c['unresolved']} | {c['journal_sender_unknown']} | {c['skipped_slots']} | {c['terminal_observation_latency_ms']['maximum']:.3f} |" for c in commands)+'''

The failed run completed its application source window and six counter balances,
but PCAP lost 2672 robot / 2637 operator kernel records. Written files match
reported captured counts; the zero-drop gate correctly rejects the case. Native
recorders report no reserve/copy loss and independently cover both phases. This
cannot rescue the failed overall capture qualification.

Multiset analysis uniquely identifies every missing PCAP record in the native
IPv4 UDP population, exactly matching the kernel-drop counts. Three late-window
clusters are retained in capture-gap.json. The largest missing clusters span
about 2.7 and 3.1 seconds. Endpoint-sampler gaps do not establish a global pause;
no scheduler/storage or unique root cause is attributed. Existing full-snapshot
TPACKET_V2 fixed-slot capacity remains finite; no buffer/dispatch/tuning change
or hidden retry is made in response to this failure.

Intent 105 remains pending in the driver and UNKNOWN/reconcile-required, revision
0, invalid result in the sender journal. The receiver has no record for that ID;
104 common successful records agree and the final observed device generation/
effects are 104. Missing/NOT_FOUND is not nonexecution, so no expiry, success or
safe replay is invented. The sender's context-change reconciliation safeguard
retains uncertainty even though transport readiness later returns.

Competitor offered-load and liveness gates pass for both executions. Their
process observation and final UDP summaries do not prove matched-window delivery.
All source summaries and eight cgroup endpoint/phase windows replay exactly,
including the failed case's application/counter data; this does not change its
failed recorder verdict. All 161 sources/installed hashes and Python bytes match
the SRT frozen plan after the SRT-only competitor-gate commit. No compiled
bridge/SDK/wire/IPC or command policy changes occur. The separate expected
competitor-stop fault is development coverage, not a positive case.

Paced DDS N5 has a separate completed three-repetition cohort. Default DDS N5
startup, full SRT N5 acceptance, remaining age/clock/model/security alignment,
deterministic N3 and N4 command-phase barriers remain open. Raw packets/prefixes,
journals/clocks remain local with hashes; no full inspect/env dumps are published.
''');print('archived failed SRT plan with both application outcomes and independent native analysis')
