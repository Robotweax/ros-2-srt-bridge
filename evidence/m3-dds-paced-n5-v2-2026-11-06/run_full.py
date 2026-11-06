import hashlib,json,subprocess,sys
from datetime import datetime,timezone
from pathlib import Path
sys.path.insert(0,'tools')
from m3_observer_study import source_inventory,installed_inventory,extract
from m3_dds_result_timeline import analyze
from m3_capture import pcap_configuration
root=Path.cwd();out=root/'.local/dds-n5-v2/20261106-retention256';out.mkdir(parents=True,exist_ok=False)
def dump(p,d):p.write_text(json.dumps(d,indent=2)+'\n')
def full_inventory():
 result=installed_inventory();p=Path('build/m3-dds-profile-probe/dds_profile_probe');result[str(p)]=hashlib.sha256(p.read_bytes()).hexdigest();return result
def scripts():
 result={}
 for p in Path('ros2/robotweax_srt_bridge_demo/scripts').glob('*.py'):
  q=Path('install/m3-ros/robotweax_srt_bridge_demo/lib/robotweax_srt_bridge_demo')/p.name
  if q.exists():
   assert p.read_bytes()==q.read_bytes();result[str(q)]=hashlib.sha256(q.read_bytes()).hexdigest()
 return result
slots=[dict(label='dds-N5-'+str(seed),group='dds',phase='long_paced',profile='N5',seed=seed,seconds=300,observer=True) for seed in (1701,2903,4211)]
plan=dict(created_utc=datetime.now(timezone.utc).isoformat(),base_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),source_sha256=source_inventory(),installed_sha256=full_inventory(),installed_scripts=scripts(),slots=slots,expected_capture=pcap_configuration(),dds_profile='paced-sensors',profile_xml_sha256=source_inventory()['containers/dds-paced-sensors.xml'],scope='three 300-second explicit paced-DDS N5 repetitions, sequential fresh owned labs; no retries or policy changes; seeds label repetitions without stochastic delay/loss; not a default-DDS discovery fix, transport-cost comparison or complete M3 acceptance',complete_m3_acceptance=False)
dump(out/'plan.json',plan);result=dict(status='running',rows=[]);dump(out/'study.json',result)
try:
 for slot in slots:
  assert source_inventory()==plan['source_sha256'] and full_inventory()==plan['installed_sha256'] and scripts()==plan['installed_scripts']
  with (out/(slot['label']+'.log')).open('w') as log:code=subprocess.call([sys.executable,'tools/run_m3_dds.py','--commands','--dds-profile','paced-sensors','--profile','N5','--seed',str(slot['seed']),'--seconds','300','--skip-build','--monotonic-capture'],stdout=log,stderr=subprocess.STDOUT)
  paths=[Path(line) for line in (out/(slot['label']+'.log')).read_text().splitlines() if line.startswith(str(root/'.local/')) and (Path(line)/'run.json').exists()]
  assert paths,'missing child manifest';run=paths[-1];report=json.loads((run/'run.json').read_text());row=dict(slot=slot,run=str(run.relative_to(root)),exit_code=code,status=report['status']);result['rows'].append(row);dump(out/'study.json',result)
  assert not code and report['status']=='passed',report.get('error')
  assert report['source_sha256']==plan['source_sha256'] and source_inventory()==plan['source_sha256'] and full_inventory()==plan['installed_sha256'] and scripts()==plan['installed_scripts']
  assert report['profile_probe']['verified'] and report['profile_probe_binary_sha256']==plan['installed_sha256']['build/m3-dds-profile-probe/dds_profile_probe']
  assert report['dds_transport_xml_sha256']==plan['profile_xml_sha256']
  assert report['competitor_check']['alive_poll_checks']>0 and report['competitor_check']['target_bitrate']==128000
  row['metrics']=extract(report,slot);dump(out/(slot['label']+'-timeline.json'),analyze(run));dump(out/'study.json',result);print(slot['label'],'passed',run,flush=True)
 result['status']='passed'
except BaseException as error:result.update(status='failed',error=str(error));dump(out/'study.json',result);raise
dump(out/'study.json',result)
