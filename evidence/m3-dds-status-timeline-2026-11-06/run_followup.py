import hashlib,json,subprocess,sys
from pathlib import Path
sys.path.insert(0,'tools')
from m3_observer_study import source_inventory,installed_inventory,extract
from m3_dds_result_timeline import analyze
root=Path.cwd();out=root/'.local/dds-status-followup/20261106-history';out.mkdir(parents=True,exist_ok=False)
def dump(p,d):p.write_text(json.dumps(d,indent=2)+'\n')
def scripts():
 result={}
 for p in Path('ros2/robotweax_srt_bridge_demo/scripts').glob('*.py'):
  q=Path('install/m3-ros/robotweax_srt_bridge_demo/lib/robotweax_srt_bridge_demo')/p.name
  if q.exists():
   assert p.read_bytes()==q.read_bytes();result[str(q)]=hashlib.sha256(q.read_bytes()).hexdigest()
 return result
slots=[dict(label='dds-N2-'+str(seed),group='dds',phase='status_diagnosis',profile='N2',seed=seed,seconds=60,observer=True) for seed in (1701,2903,4211)]
plan=dict(base_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),source_sha256=source_inventory(),installed_sha256=installed_inventory(),installed_scripts=scripts(),slots=slots,scope='three short instrumented development runs; no retries, full-duration acceptance, isolated resource estimate or policy changes',complete_m3_acceptance=False)
dump(out/'plan.json',plan);result=dict(status='running',rows=[])
try:
 for slot in slots:
  assert source_inventory()==plan['source_sha256'] and installed_inventory()==plan['installed_sha256'] and scripts()==plan['installed_scripts']
  with (out/(slot['label']+'.log')).open('w') as log:code=subprocess.call([sys.executable,'tools/run_m3_dds.py','--commands','--profile','N2','--seed',str(slot['seed']),'--seconds','60','--skip-build','--monotonic-capture'],stdout=log,stderr=subprocess.STDOUT)
  paths=[Path(line) for line in (out/(slot['label']+'.log')).read_text().splitlines() if line.startswith(str(root/'.local/')) and (Path(line)/'run.json').exists()]
  assert paths,'missing child manifest';run=paths[-1];report=json.loads((run/'run.json').read_text());row=dict(slot=slot,run=str(run.relative_to(root)),exit_code=code,status=report['status']);result['rows'].append(row);dump(out/'study.json',result)
  assert not code and report['status']=='passed',report.get('error')
  assert report['source_sha256']==plan['source_sha256'] and source_inventory()==plan['source_sha256'] and installed_inventory()==plan['installed_sha256'] and scripts()==plan['installed_scripts']
  row['metrics']=extract(report,slot);dump(out/(slot['label']+'-timeline.json'),analyze(run));dump(out/'study.json',result);print(slot['label'],'passed',run,flush=True)
 result['status']='passed'
except BaseException as error:result.update(status='failed',error=str(error));dump(out/'study.json',result);raise
dump(out/'study.json',result)
