"""Pre-SIGINT SDK provider visibility at original observer sampling/read budgets."""
import json
from pathlib import Path
import time
from task_assessment import assess_metadata,require
PROVIDER_NAMES={'rwx-shard-0','rwx-shard-1','rwx-readiness'}
def presence(rows,target):
    require(bool(rows),'observer header unavailable')
    require(rows[0]['root']==dict(pid=target['pid'],start_ticks=target['start_ticks']),'SDK visibility root differs')
    require(all(r['kind']=='sample' for r in rows[1:]),'observer finalized before release')
    require(len(rows)>1,'SDK provider samples unavailable')
    tasks=[t for r in rows[1:] for p in r['processes'] for t in p.get('threads',[])]
    footer=dict(kind='status',completed=True,budget_exhausted=False,userspace_stacks_requested=False,samples=len(rows)-1,sample_limit=48,kernel_stack_reads_ok=sum(t['kernel_stack']['status']=='ok' for t in tasks),kernel_stack_reads_unavailable=sum(t['kernel_stack']['status']!='ok' for t in tasks))
    proof=assess_metadata([*rows,footer],dict(pid=target['pid'],start_ticks=target['start_ticks']));matches=[];names=set()
    for row in proof['rows']:
        roots=[p for p in row['processes'] if p['identity']['pid']==target['pid']]
        require(len(roots)==1 and roots[0]['status']=='sampled','SDK root no longer live')
        live=[t for t in roots[0]['tasks'] if t['classification']=='readable_task' and t['nonempty_readable_stack']]
        providers=[t for t in live if t['task_identity']['name'] in PROVIDER_NAMES]
        if any(t['tid']==target['pid'] for t in live) and providers:matches.append(row);names.update(t['task_identity']['name'] for t in providers)
    require(len(matches)>=2,'two SDK provider observations required')
    return dict(samples=len(matches),provider_names=sorted(names),first_begin_ns=matches[0]['begin_ns'],last_end_ns=matches[-1]['end_ns'],scope='readable registered bridge/root and named SDK provider tasks before shutdown release; not performance or exit proof')
def wait_provider_visibility(sidecar,target):
    deadline=time.monotonic()+6
    while time.monotonic()<deadline:
        path=sidecar.out/'active-sdk-observer.jsonl';r=sidecar.command(['docker','cp',sidecar.name+':/out/blocked-target-shutdown-stacks.jsonl',str(path)],check=False)
        if r.returncode==0:
            if path.stat().st_size>8*1024*1024:raise ValueError('SDK observer snapshot byte bound exceeded')
            rows=[json.loads(line) for line in path.read_text().splitlines(keepends=True) if line.endswith('\n')]
            try:
                proof=presence(rows,target);(sidecar.out/'sdk-provider-live-proof.json').write_text(json.dumps(proof,indent=2)+'\n');return proof
            except ValueError as error:
                if str(error) not in ('observer header unavailable','SDK provider samples unavailable','two SDK provider observations required'):raise
        state=json.loads(sidecar.command(['docker','inspect',sidecar.name]).stdout)[0]['State']
        if not state['Running']:raise ValueError('SDK observer exited before provider visibility')
        time.sleep(.05)
    raise ValueError('SDK provider visibility deadline exceeded; no release')
